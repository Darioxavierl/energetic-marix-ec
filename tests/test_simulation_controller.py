"""Tests for simulation controller orchestration."""

from src.application.simulation_controller import SimulationController
from src.domain.models.simulation_state import DataSourceMode


class DummyClient:
    def get_latest_production(self):
        return {
            "timestamp": "2026-01-15T10:00:00",
            "total_mwh": 3000.0,
            "hydro_mwh": 1800.0,
            "thermal_mwh": 700.0,
            "renewable_mwh": 400.0,
            "import_mwh": 10.0,
            "export_mwh": 5.0,
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

    def get_latest_demand(self):
        return {
            "timestamp": "2026-01-15T10:00:00",
            "demand_total_mw": 2800.0,
            "demand_cnel_mw": 1900.0,
            "demand_empresas_mw": 900.0,
        }


def test_sync_from_microservice_in_automatic_mode():
    controller = SimulationController(cenace_client=DummyClient())
    state = controller.sync_from_microservice()

    assert state.mode == DataSourceMode.AUTOMATIC
    assert state.demand_mw == 2800.0
    assert state.demand_source == "demand_latest"
    assert state.supply_source == "hourly_curve"
    assert state.metrics.total_supply_mw == 2905.0
    assert state.metrics.balance_mw == 105.0
    assert state.official_total_mwh == 3000.0
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


class DummyClientTrailingZeros(DummyClient):
    def get_hourly_demand(self):
        return [
            {
                "demand_mw": 3000.0,
                "total_production_mw": 3012.0,
                "hydro_mw": 1900.0,
                "thermal_mw": 800.0,
                "renewable_mw": 312.0,
                "import_mw": 0.0,
                "export_mw": 0.0,
            },
            {
                "demand_mw": 0.0,
                "total_production_mw": 0.0,
                "hydro_mw": 0.0,
                "thermal_mw": 0.0,
                "renewable_mw": 0.0,
                "import_mw": 0.0,
                "export_mw": 0.0,
            },
        ]


class DummyClientAllZeros(DummyClient):
    def get_hourly_demand(self):
        return [
            {
                "demand_mw": 0.0,
                "total_production_mw": 0.0,
                "hydro_mw": 0.0,
                "thermal_mw": 0.0,
                "renewable_mw": 0.0,
                "import_mw": 0.0,
                "export_mw": 0.0,
            }
        ]


def test_sync_uses_last_non_zero_hourly_point_when_tail_is_zero():
    controller = SimulationController(cenace_client=DummyClientTrailingZeros())
    state = controller.sync_from_microservice()

    # Supply source-of-truth is effective hourly curve in MW.
    assert state.hydro_mw == 1900.0
    assert state.thermal_mw == 800.0
    assert state.renewable_mw == 312.0
    # Demand source-of-truth is demand/latest.
    assert state.demand_mw == 2800.0


def test_sync_falls_back_to_production_when_hourly_curve_is_all_zero():
    controller = SimulationController(cenace_client=DummyClientAllZeros())
    state = controller.sync_from_microservice()

    assert state.demand_mw == 2800.0
    assert round(state.hydro_mw, 2) == round(1800.0 / 24.0, 2)
    assert round(state.thermal_mw, 2) == round(700.0 / 24.0, 2)
    assert round(state.renewable_mw, 2) == round(400.0 / 24.0, 2)
    assert state.supply_source == "production_summary_mwh_equivalent"


class DummyClientProductionVsCurve(DummyClient):
    def get_latest_production(self):
        return {
            "timestamp": "2026-01-15T10:00:00",
            "total_mwh": 90000.0,
            "hydro_mwh": 74000.0,
            "thermal_mwh": 15000.0,
            "renewable_mwh": 700.0,
            "import_mwh": 80.0,
            "export_mwh": 120.0,
        }

    def get_hourly_demand(self):
        return [
            {
                "demand_mw": 4200.0,
                "total_production_mw": 4300.0,
                "hydro_mw": 3000.0,
                "thermal_mw": 1000.0,
                "renewable_mw": 300.0,
                "import_mw": 0.0,
                "export_mw": 0.0,
            }
        ]

    def get_latest_demand(self):
        return {
            "timestamp": "2026-01-15T10:00:00",
            "demand_total_mw": 4300.0,
            "demand_cnel_mw": 2900.0,
            "demand_empresas_mw": 1400.0,
        }


def test_sync_prioritizes_production_summary_and_demand_latest_over_hourly_curve_components():
    controller = SimulationController(cenace_client=DummyClientProductionVsCurve())
    state = controller.sync_from_microservice()

    assert state.hydro_mw == 3000.0
    assert state.thermal_mw == 1000.0
    assert state.renewable_mw == 300.0
    assert state.import_mw == 0.0
    assert state.export_mw == 0.0
    assert state.official_hydro_mwh == 74000.0
    assert state.official_thermal_mwh == 15000.0
    assert state.demand_mw == 4300.0


def test_apply_manual_central_catalog_preserves_import_export():
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
        }
    ]
    state = controller.apply_manual_central_catalog(
        centrales,
        global_drought_factor=0.0,
        import_mw=150.0,
        export_mw=20.0,
    )

    assert state.import_mw == 150.0
    assert state.export_mw == 20.0
    assert state.metrics.total_supply_mw == 1000.0 + 150.0 - 20.0


def test_apply_manual_central_catalog_adds_residual_continuity_without_exceeding_catalog_capacity():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()
    controller.switch_mode(DataSourceMode.MANUAL)
    controller.set_manual_residual_by_type(
        {"HYDRO": 0.0, "THERMAL": 400.0, "RENEWABLE": 0.0},
        baseline_source="snapshot live",
        residual_reason="catalog_gap",
    )

    centrales = [
        {
            "id": "t1",
            "type": "THERMAL",
            "status": "ONLINE",
            "available_capacity_mw": 100.0,
            "installed_capacity_mw": 100.0,
        }
    ]
    state = controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)

    assert state.thermal_mw == 500.0
    assert state.residual_thermal_mw == 400.0
    assert state.supply_source == "manual_catalog_plus_residual"
    assert state.manual_baseline_source == "snapshot live"


def test_sync_from_microservice_resets_manual_residual_fields():
    controller = SimulationController(cenace_client=DummyClient())
    controller.switch_mode(DataSourceMode.MANUAL)
    controller.set_manual_residual_by_type(
        {"HYDRO": 10.0, "THERMAL": 20.0, "RENEWABLE": 30.0},
        baseline_source="snapshot live",
        residual_reason="catalog_gap",
    )

    controller.switch_mode(DataSourceMode.AUTOMATIC)
    state = controller.state

    assert state.residual_hydro_mw == 0.0
    assert state.residual_thermal_mw == 0.0
    assert state.residual_renewable_mw == 0.0
    assert state.manual_baseline_source == ""


def test_apply_manual_interconnection_updates_kpis():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()
    controller.switch_mode(DataSourceMode.MANUAL)

    centrales = [
        {
            "id": "t1",
            "type": "THERMAL",
            "status": "ONLINE",
            "available_capacity_mw": 500.0,
        }
    ]
    controller.apply_manual_central_catalog(centrales, global_drought_factor=0.0)

    state = controller.apply_manual_interconnection(import_mw=200.0, export_mw=50.0)

    assert state.import_mw == 200.0
    assert state.export_mw == 50.0
    # thermal(500) + import(200) - export(50) = 650
    assert state.metrics.total_supply_mw == 500.0 + 200.0 - 50.0


def test_apply_manual_interconnection_blocked_outside_manual():
    controller = SimulationController(cenace_client=DummyClient())
    controller.sync_from_microservice()

    original_import = controller.state.import_mw
    controller.apply_manual_interconnection(import_mw=999.0, export_mw=0.0)

    assert controller.state.import_mw == original_import
