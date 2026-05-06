"""Tests for scenario manager persistence operations."""

import json
from pathlib import Path

from src.application.scenario_manager import ScenarioManager
from src.domain.models.simulation_state import DataSourceMode, SimulationState


def test_save_and_load_scenario(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    state = SimulationState(
        mode=DataSourceMode.MANUAL,
        demand_mw=3000.0,
        hydro_mw=2100.0,
        residual_hydro_mw=150.0,
        manual_baseline_source="snapshot live",
    )

    manager.save("escenario prueba", state)
    loaded = manager.load("escenario_prueba")

    assert loaded.mode == DataSourceMode.MANUAL
    assert loaded.demand_mw == 3000.0
    assert loaded.hydro_mw == 2100.0
    assert loaded.residual_hydro_mw == 150.0
    assert loaded.manual_baseline_source == "snapshot live"


def test_duplicate_and_delete_scenario(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    manager.save("base", SimulationState(demand_mw=2500.0))

    manager.duplicate("base", "base_copy")
    names = manager.list_scenarios()
    assert "base" in names
    assert "base_copy" in names

    manager.delete("base_copy")
    assert "base_copy" not in manager.list_scenarios()


def test_save_and_load_bundle_with_centrales(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    state = SimulationState(mode=DataSourceMode.MANUAL, demand_mw=2800.0, hydro_mw=900.0)
    centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "status": "ONLINE",
            "available_capacity_mw": 1000.0,
            "reservoir_level_pct": 70.0,
        }
    ]

    manager.save("bundle_case", state, centrales=centrales)
    bundle = manager.load_bundle("bundle_case")

    assert bundle["schema_version"] == 2
    assert bundle["state"].mode == DataSourceMode.MANUAL
    assert isinstance(bundle["centrales"], list)
    assert bundle["centrales"][0]["id"] == "h1"
    assert bundle["centrales"][0]["reservoir_level_pct"] == 70.0


def test_load_bundle_backward_compatible_without_centrales(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    legacy_path = tmp_path / "legacy.json"
    legacy_payload = {
        "name": "legacy",
        "saved_at": "2026-05-02T00:00:00",
        "state": {
            "mode": "MANUAL",
            "demand_mw": 2500.0,
            "hydro_mw": 1000.0,
            "thermal_mw": 800.0,
            "renewable_mw": 300.0,
            "import_mw": 50.0,
            "export_mw": 10.0,
            "source_timestamp": None,
            "last_manual_edit": None,
            "metrics": {
                "total_supply_mw": 2140.0,
                "balance_mw": -360.0,
                "reserve_margin_pct": -14.4,
                "risk_level": "FAILURE",
            },
        },
    }
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    bundle = manager.load_bundle("legacy")
    assert bundle["schema_version"] == 1
    assert bundle["centrales"] is None
    assert bundle["state"].mode == DataSourceMode.MANUAL
    assert bundle["state"].demand_mw == 2500.0


def test_create_drought_preset_scales_hydro_fields(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    base_state = SimulationState(mode=DataSourceMode.MANUAL, global_drought_factor=0.0)
    base_centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "status": "ONLINE",
            "reservoir_level_pct": 80.0,
            "available_capacity_mw": 500.0,
        },
        {
            "id": "t1",
            "type": "THERMAL",
            "status": "ONLINE",
            "available_capacity_mw": 400.0,
        },
    ]

    manager.create_drought_preset("media", "preset_media", base_state, base_centrales)
    bundle = manager.load_bundle("preset_media")

    assert round(bundle["state"].global_drought_factor, 2) == 0.45
    hydro = [c for c in bundle["centrales"] if c.get("id") == "h1"][0]
    assert round(float(hydro["reservoir_level_pct"]), 2) == 60.0
    assert "inflow_index" not in hydro


def test_create_drought_preset_invalid_name_raises(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    with_raises = False
    try:
        manager.create_drought_preset(
            "desconocida",
            "preset_invalid",
            SimulationState(),
            [],
        )
    except ValueError:
        with_raises = True

    assert with_raises is True
