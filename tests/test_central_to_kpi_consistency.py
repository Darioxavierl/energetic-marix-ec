"""Regression tests for central-edit to KPI coherence in manual mode."""

from src.application.simulation_controller import SimulationController
from src.domain.models.simulation_state import DataSourceMode


class DummyClient:
    def get_latest_production(self):
        return {"timestamp": "2026-01-15T10:00:00", "total_mwh": 3000.0}

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



def test_turning_hydro_offline_reduces_kpi_supply_and_hydro_mw():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()
    controller.switch_mode(DataSourceMode.MANUAL)

    centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "status": "ONLINE",
            "available_capacity_mw": 500.0,
            "reservoir_level_pct": 100.0,
        },
        {"id": "t1", "type": "THERMAL", "status": "ONLINE", "available_capacity_mw": 1000.0},
    ]

    before = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)
    supply_before = before.metrics.total_supply_mw
    hydro_before = before.hydro_mw

    centrales[0]["status"] = "OFFLINE"
    after = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)

    assert after.hydro_mw < hydro_before
    assert after.metrics.total_supply_mw < supply_before
