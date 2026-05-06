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
        self.default_energy_window_hours = 24.0

    def sync_from_microservice(self) -> SimulationState:
        """Load latest values from scraper service while in automatic mode."""

        if self.state.mode != DataSourceMode.AUTOMATIC:
            return self.state

        self.state.residual_hydro_mw = 0.0
        self.state.residual_thermal_mw = 0.0
        self.state.residual_renewable_mw = 0.0
        self.state.manual_baseline_source = ""
        self.state.manual_residual_reason = ""

        production = self.cenace_client.get_latest_production()
        curve = self.cenace_client.get_hourly_demand()
        self.latest_hourly_curve = list(curve)

        demand_latest: dict = {}
        get_latest_demand = getattr(self.cenace_client, "get_latest_demand", None)
        if callable(get_latest_demand):
            try:
                demand_latest = get_latest_demand() or {}
            except CENACEClientError:
                # Demand endpoint can fail independently; fallback to hourly curve.
                demand_latest = {}

        get_latest_plants = getattr(self.cenace_client, "get_latest_plants", None)
        if callable(get_latest_plants):
            try:
                self.latest_plants = get_latest_plants()
            except CENACEClientError:
                # Plants endpoint can fail independently; keep sync alive with last good snapshot
                pass

        latest_point = self._select_latest_effective_point(curve)

        # Official report layer from CENACE summary endpoint (energy snapshot, MWh).
        self.state.official_total_mwh = float(production.get("total_mwh", 0.0) or 0.0)
        self.state.official_hydro_mwh = float(production.get("hydro_mwh", 0.0) or 0.0)
        self.state.official_thermal_mwh = float(production.get("thermal_mwh", 0.0) or 0.0)
        self.state.official_renewable_mwh = float(production.get("renewable_mwh", 0.0) or 0.0)
        self.state.official_import_mwh = float(production.get("import_mwh", 0.0) or 0.0)
        self.state.official_export_mwh = float(production.get("export_mwh", 0.0) or 0.0)

        hourly_has_supply = (
            float(latest_point.get("hydro_mw", 0.0) or 0.0) > 0.0
            or float(latest_point.get("thermal_mw", 0.0) or 0.0) > 0.0
            or float(latest_point.get("renewable_mw", 0.0) or 0.0) > 0.0
            or float(latest_point.get("total_production_mw", 0.0) or 0.0) > 0.0
        )

        if hourly_has_supply:
            # Operational layer uses instantaneous power from hourly curve (MW).
            self.state.hydro_mw = float(latest_point.get("hydro_mw", 0.0) or 0.0)
            self.state.thermal_mw = float(latest_point.get("thermal_mw", 0.0) or 0.0)
            self.state.renewable_mw = float(latest_point.get("renewable_mw", 0.0) or 0.0)
            self.state.import_mw = float(latest_point.get("import_mw", 0.0) or 0.0)
            self.state.export_mw = float(latest_point.get("export_mw", 0.0) or 0.0)
            self.state.supply_source = "hourly_curve"
            self.state.operational_window_hours = 1.0
        else:
            # Fallback converts official energy snapshot into MW-equivalent average.
            eq_hours = self.default_energy_window_hours
            self.state.hydro_mw = self.state.official_hydro_mwh / eq_hours
            self.state.thermal_mw = self.state.official_thermal_mwh / eq_hours
            self.state.renewable_mw = self.state.official_renewable_mwh / eq_hours
            self.state.import_mw = self.state.official_import_mwh / eq_hours
            self.state.export_mw = self.state.official_export_mwh / eq_hours
            self.state.supply_source = "production_summary_mwh_equivalent"
            self.state.operational_window_hours = eq_hours

        # Source of truth for demand in AUTOMATIC mode: demand latest endpoint.
        demand_total = float(demand_latest.get("demand_total_mw", 0.0) or 0.0)
        if demand_total > 0.0:
            self.state.demand_mw = demand_total
            self.state.demand_source = "demand_latest"
        else:
            # Fallback to latest hourly point when demand/latest unavailable.
            self.state.demand_mw = float(latest_point.get("demand_mw", 0.0) or 0.0)
            if self.state.demand_mw <= 0.0:
                # Last-resort fallback keeps app operational even with partial microservice data.
                self.state.demand_mw = self.state.official_total_mwh / self.default_energy_window_hours
                self.state.demand_source = "production_summary_mwh_equivalent"
                self.state.operational_window_hours = self.default_energy_window_hours
            else:
                self.state.demand_source = "hourly_curve"

        self.state.source_timestamp = CENACEClient.parse_iso_datetime(production.get("timestamp"))
        self.state.metrics = self._calculate_metrics()
        return self.state

    @staticmethod
    def _select_latest_effective_point(curve: list[dict]) -> dict:
        """Return the latest non-empty hourly point, or last raw point as fallback."""

        if not curve:
            return {}

        for point in reversed(curve):
            demand = float(point.get("demand_mw", 0.0) or 0.0)
            total = float(point.get("total_production_mw", 0.0) or 0.0)
            if demand > 0.0 or total > 0.0:
                return point

        return curve[-1]

    def switch_mode(self, mode: DataSourceMode) -> SimulationState:
        """Switch execution mode."""

        if mode == self.state.mode:
            return self.state

        self.state.mode = mode
        if mode == DataSourceMode.AUTOMATIC:
            self.sync_from_microservice()
        else:
            self.state.residual_hydro_mw = 0.0
            self.state.residual_thermal_mw = 0.0
            self.state.residual_renewable_mw = 0.0
            self.state.demand_source = "manual_edit"
            self.state.supply_source = "manual_catalog"
            self.state.manual_baseline_source = ""
            self.state.manual_residual_reason = ""
            self.state.operational_window_hours = 1.0
        return self.state

    def set_manual_residual_by_type(
        self,
        residual_by_type_mw: dict[str, float] | None,
        baseline_source: str = "",
        residual_reason: str = "catalog_gap",
    ) -> SimulationState:
        """Store continuity residual applied on MANUAL entry without altering catalog capacities."""

        residuals = residual_by_type_mw or {}
        self.state.residual_hydro_mw = max(0.0, float(residuals.get("HYDRO", 0.0) or 0.0))
        self.state.residual_thermal_mw = max(0.0, float(residuals.get("THERMAL", 0.0) or 0.0))
        self.state.residual_renewable_mw = max(0.0, float(residuals.get("RENEWABLE", 0.0) or 0.0))
        residual_total = (
            self.state.residual_hydro_mw
            + self.state.residual_thermal_mw
            + self.state.residual_renewable_mw
        )
        self.state.manual_baseline_source = str(baseline_source or "")
        self.state.manual_residual_reason = str(residual_reason if residual_total > 0.0 else "")
        self.state.supply_source = "manual_catalog_plus_residual" if residual_total > 0.0 else "manual_catalog"
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
        import_mw: float | None = None,
        export_mw: float | None = None,
    ) -> SimulationState:
        """Recalculate generation split and KPIs from edited central catalog in manual mode."""

        if self.state.mode != DataSourceMode.MANUAL:
            return self.state

        if global_drought_factor is not None:
            self.state.global_drought_factor = max(0.0, min(1.0, float(global_drought_factor)))

        if import_mw is not None:
            self.state.import_mw = max(0.0, float(import_mw))
        if export_mw is not None:
            self.state.export_mw = max(0.0, float(export_mw))

        generation_by_type = aggregate_generation_by_type(
            centrales=centrales,
            global_drought_factor=self.state.global_drought_factor,
        )
        self.state.hydro_mw = generation_by_type.get("HYDRO", 0.0) + self.state.residual_hydro_mw
        self.state.thermal_mw = generation_by_type.get("THERMAL", 0.0) + self.state.residual_thermal_mw
        self.state.renewable_mw = (
            generation_by_type.get("WIND", 0.0) + generation_by_type.get("SOLAR", 0.0) + self.state.residual_renewable_mw
        )
        self.state.last_manual_edit = datetime.now()
        self.state.metrics = self._calculate_metrics()
        return self.state

    def apply_manual_interconnection(
        self,
        import_mw: float,
        export_mw: float,
    ) -> SimulationState:
        """Update interconnection values (import/export) and recalculate KPIs in manual mode."""

        if self.state.mode != DataSourceMode.MANUAL:
            return self.state

        self.state.import_mw = max(0.0, float(import_mw))
        self.state.export_mw = max(0.0, float(export_mw))
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
