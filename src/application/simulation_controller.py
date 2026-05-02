"""Application service to orchestrate simulation state updates."""

from __future__ import annotations

import copy
from datetime import datetime

from src.domain.models.simulation_state import DataSourceMode, SimulationMetrics, SimulationState
from src.domain.simulation.balance_calculator import BalanceCalculator
from src.domain.simulation.generation_aggregator import aggregate_generation_by_type
from src.domain.simulation.risk_assessor import RiskAssessor
from src.infrastructure.api.cenace_client import CENACEClient, CENACEClientError


class SimulationController:
    """Coordinates data retrieval, mode transitions and KPI calculations."""

    def __init__(self, cenace_client: CENACEClient):
        self.cenace_client = cenace_client
        self.state = SimulationState()
        self.latest_plants: list[dict] = []
        self.latest_hourly_curve: list[dict] = []

    def sync_from_microservice(self) -> SimulationState:
        """Load latest values from scraper service while in automatic mode."""

        if self.state.mode != DataSourceMode.AUTOMATIC:
            return self.state

        production = self.cenace_client.get_latest_production()
        curve = self.cenace_client.get_hourly_demand()
        self.latest_hourly_curve = list(curve)
        get_latest_plants = getattr(self.cenace_client, "get_latest_plants", None)
        if callable(get_latest_plants):
            try:
                self.latest_plants = get_latest_plants()
            except CENACEClientError:
                # Plants endpoint can fail independently; keep sync alive with last good snapshot
                pass
        latest_point = curve[-1] if curve else {}

        self.state.hydro_mw = float(latest_point.get("hydro_mw", 0.0))
        self.state.thermal_mw = float(latest_point.get("thermal_mw", 0.0))
        self.state.renewable_mw = float(latest_point.get("renewable_mw", 0.0))
        self.state.import_mw = float(latest_point.get("import_mw", 0.0))
        self.state.export_mw = float(latest_point.get("export_mw", 0.0))
        self.state.demand_mw = float(latest_point.get("demand_mw", 0.0))

        if self.state.demand_mw <= 0.0:
            # Fallback to production total when no demand curve is available yet
            self.state.demand_mw = float(production.get("total_mwh", 0.0))

        self.state.source_timestamp = CENACEClient.parse_iso_datetime(production.get("timestamp"))
        self.state.metrics = self._calculate_metrics()
        return self.state

    def switch_mode(self, mode: DataSourceMode) -> SimulationState:
        """Switch execution mode."""

        if mode == self.state.mode:
            return self.state

        self.state.mode = mode
        if mode == DataSourceMode.AUTOMATIC:
            self.sync_from_microservice()
        return self.state

    def apply_manual_demand_delta(self, delta_percent: float) -> SimulationState:
        """Adjust demand in manual mode and recalculate KPIs."""

        if self.state.mode != DataSourceMode.MANUAL:
            return self.state

        factor = 1.0 + (delta_percent / 100.0)
        self.state.demand_mw = max(0.0, self.state.demand_mw * factor)
        self.state.last_manual_edit = datetime.now()
        self.state.metrics = self._calculate_metrics()
        return self.state

    def apply_manual_central_catalog(
        self,
        centrales: list[dict],
        global_drought_factor: float | None = None,
    ) -> SimulationState:
        """Recalculate generation split and KPIs from edited central catalog in manual mode."""

        if self.state.mode != DataSourceMode.MANUAL:
            return self.state

        if global_drought_factor is not None:
            self.state.global_drought_factor = max(0.0, min(1.0, float(global_drought_factor)))

        generation_by_type = aggregate_generation_by_type(
            centrales=centrales,
            global_drought_factor=self.state.global_drought_factor,
        )
        self.state.hydro_mw = generation_by_type.get("HYDRO", 0.0)
        self.state.thermal_mw = generation_by_type.get("THERMAL", 0.0)
        self.state.renewable_mw = generation_by_type.get("WIND", 0.0) + generation_by_type.get("SOLAR", 0.0)
        self.state.last_manual_edit = datetime.now()
        self.state.metrics = self._calculate_metrics()
        return self.state

    def _calculate_metrics(self) -> SimulationMetrics:
        """Calculate core KPIs from current state values."""

        total_supply = BalanceCalculator.calculate_total_supply(
            hydro_mw=self.state.hydro_mw,
            thermal_mw=self.state.thermal_mw,
            renewable_mw=self.state.renewable_mw,
            import_mw=self.state.import_mw,
            export_mw=self.state.export_mw,
        )
        balance = BalanceCalculator.calculate_balance(total_supply, self.state.demand_mw)
        reserve = BalanceCalculator.calculate_reserve_margin(total_supply, self.state.demand_mw)
        risk = RiskAssessor.classify_by_reserve_margin(reserve)
        return SimulationMetrics(
            total_supply_mw=total_supply,
            balance_mw=balance,
            reserve_margin_pct=reserve,
            risk_level=risk,
        )

    def safe_sync(self) -> tuple[SimulationState, str | None]:
        """Sync wrapper that keeps app responsive on service errors."""

        try:
            return self.sync_from_microservice(), None
        except CENACEClientError as exc:
            return self.state, str(exc)

    def get_latest_plants_snapshot(self) -> list[dict]:
        """Return last successful plants payload from microservice."""

        return list(self.latest_plants)

    def get_latest_hourly_curve_snapshot(self) -> list[dict]:
        """Return last successful hourly demand curve payload from microservice."""

        return list(self.latest_hourly_curve)

    def set_state(self, state: SimulationState) -> SimulationState:
        """Replace current simulation state from an external snapshot."""

        self.state = copy.deepcopy(state)
        return self.state

    def get_state_snapshot(self) -> SimulationState:
        """Return a detached copy of current state."""

        return copy.deepcopy(self.state)
