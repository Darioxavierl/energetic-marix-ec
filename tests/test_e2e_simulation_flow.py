"""Minimal E2E flow: automatic -> manual -> save -> restore scenario."""

from src.application.scenario_manager import ScenarioManager
from src.application.simulation_controller import SimulationController
from src.domain.models.simulation_state import DataSourceMode


class DummyClient:
    def get_latest_production(self):
        return {"timestamp": "2026-05-02T10:00:00", "total_mwh": 3200.0}

    def get_hourly_demand(self):
        return [
            {
                "demand_mw": 3000.0,
                "hydro_mw": 1800.0,
                "thermal_mw": 800.0,
                "renewable_mw": 350.0,
                "import_mw": 80.0,
                "export_mw": 10.0,
            }
        ]


def test_e2e_automatic_manual_save_restore(tmp_path):
    controller = SimulationController(cenace_client=DummyClient())
    manager = ScenarioManager(tmp_path)

    state = controller.sync_from_microservice()
    assert state.mode == DataSourceMode.AUTOMATIC

    controller.switch_mode(DataSourceMode.MANUAL)
    manual_state = controller.apply_manual_demand_delta(10.0)
    edited_demand = manual_state.demand_mw
    assert edited_demand > 3000.0

    manager.save("flow_case", controller.get_state_snapshot())

    controller.apply_manual_demand_delta(10.0)
    assert controller.state.demand_mw > edited_demand

    restored = manager.load("flow_case")
    controller.set_state(restored)
    assert controller.state.demand_mw == edited_demand
    assert controller.state.mode == DataSourceMode.MANUAL
