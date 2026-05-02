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
    hourly = controller.get_latest_hourly_curve_snapshot()
    assert isinstance(hourly, list)
    assert len(hourly) == 1


def test_manual_adjustment_requires_manual_mode():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()

    original_demand = controller.state.demand_mw
    controller.apply_manual_demand_delta(10.0)
    assert controller.state.demand_mw == original_demand

    controller.switch_mode(DataSourceMode.MANUAL)
    controller.apply_manual_demand_delta(10.0)
    assert controller.state.demand_mw > original_demand


def test_manual_central_catalog_recomputes_kpis():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()
    controller.switch_mode(DataSourceMode.MANUAL)

    centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "status": "ONLINE",
            "available_capacity_mw": 1000.0,
            "reservoir_level_pct": 100.0,
        },
        {
            "id": "t1",
            "type": "THERMAL",
            "status": "ONLINE",
            "available_capacity_mw": 600.0,
        },
    ]
    state = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)

    assert state.hydro_mw == 1000.0
    assert state.thermal_mw == 600.0
    assert state.metrics.total_supply_mw == 1605.0
    assert state.metrics.risk_level in {"CRITICAL", "FAILURE"}

    centrales[0]["status"] = "OFFLINE"
    state_after_offline = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)

    assert state_after_offline.hydro_mw == 0.0
    assert state_after_offline.metrics.total_supply_mw == 605.0


def test_switch_back_to_automatic_restores_external_data():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()

    controller.switch_mode(DataSourceMode.MANUAL)
    centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "status": "ONLINE",
            "available_capacity_mw": 400.0,
            "reservoir_level_pct": 50.0,
        }
    ]
    manual_state = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.5)
    assert manual_state.hydro_mw < 1800.0

    automatic_state = controller.switch_mode(DataSourceMode.AUTOMATIC)
    assert automatic_state.mode == DataSourceMode.AUTOMATIC
    assert automatic_state.hydro_mw == 1800.0
    assert automatic_state.demand_mw == 2800.0
