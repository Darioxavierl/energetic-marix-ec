"""Tests for simulation controller orchestration."""

from src.application.simulation_controller import SimulationController
from src.domain.models.simulation_state import DataSourceMode


class DummyClient:
    def get_latest_production(self):
        return {
            "timestamp": "2026-01-15T10:00:00",
            "total_mwh": 3000.0,
        }

    def get_hourly_demand(self):
        return [
            {
                "demand_mw": 2800.0,
                "hydro_mw": 1800.0,
                "thermal_mw": 700.0,
                "renewable_mw": 400.0,
                "import_mw": 10.0,
                "export_mw": 5.0,
            }
        ]


def test_sync_from_microservice_in_automatic_mode():
    controller = SimulationController(cenace_client=DummyClient())
    state = controller.sync_from_microservice()

    assert state.mode == DataSourceMode.AUTOMATIC
    assert state.demand_mw == 2800.0
    assert state.metrics.total_supply_mw == 2905.0
    assert state.metrics.balance_mw == 105.0


def test_manual_adjustment_requires_manual_mode():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()

    original_demand = controller.state.demand_mw
    controller.apply_manual_demand_delta(10.0)
    assert controller.state.demand_mw == original_demand

    controller.switch_mode(DataSourceMode.MANUAL)
    controller.apply_manual_demand_delta(10.0)
    assert controller.state.demand_mw > original_demand
