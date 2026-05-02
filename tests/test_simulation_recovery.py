"""Tests for controller recovery behavior under client failures."""

from src.application.simulation_controller import SimulationController
from src.infrastructure.api.cenace_client import CENACEClientError


class FlakyClient:
    def __init__(self):
        self.fail_once = True

    def get_latest_production(self):
        if self.fail_once:
            self.fail_once = False
            raise CENACEClientError("temporary outage")
        return {"timestamp": "2026-05-02T10:00:00", "total_mwh": 3000.0}

    def get_hourly_demand(self):
        if self.fail_once:
            raise CENACEClientError("temporary outage")
        return [
            {
                "demand_mw": 2800.0,
                "hydro_mw": 1700.0,
                "thermal_mw": 700.0,
                "renewable_mw": 350.0,
                "import_mw": 80.0,
                "export_mw": 0.0,
            }
        ]


def test_safe_sync_recovers_after_transient_failure(monkeypatch):
    controller = SimulationController(cenace_client=FlakyClient())

    # First call fails; controller should not crash
    state, error = controller.safe_sync()
    assert error is not None

    # Patch methods to success for second call
    monkeypatch.setattr(controller.cenace_client, "get_latest_production", lambda: {"timestamp": "2026-05-02T10:00:00", "total_mwh": 3000.0})
    monkeypatch.setattr(controller.cenace_client, "get_hourly_demand", lambda: [{"demand_mw": 2800.0, "hydro_mw": 1700.0, "thermal_mw": 700.0, "renewable_mw": 350.0, "import_mw": 80.0, "export_mw": 0.0}])

    state, error = controller.safe_sync()
    assert error is None
    assert state.demand_mw == 2800.0
