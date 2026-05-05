"""Tests for manual catalog baseline initialization from live snapshots."""

from datetime import datetime, timedelta

from src.application.manual_catalog_baseline import (
    build_manual_catalog_from_automatic_state_with_diagnostics,
    build_manual_catalog_from_live,
    build_manual_catalog_from_live_with_diagnostics,
    has_usable_live_snapshot,
    is_snapshot_timestamp_fresh,
    neutralize_hydro_reservoir_for_entry,
    normalize_hydro_contract,
)
from src.domain.models.simulation_state import SimulationMetrics, SimulationState


def test_has_usable_live_snapshot_requires_positive_generation():
    assert not has_usable_live_snapshot([])
    assert not has_usable_live_snapshot([{"mwh": 0.0}, {"mwh": None}])
    assert has_usable_live_snapshot([{"mwh": 0.1}])


def test_is_snapshot_timestamp_fresh_respects_max_age():
    now = datetime(2026, 5, 3, 12, 0, 0)
    fresh = now - timedelta(minutes=10)
    stale = now - timedelta(minutes=45)

    assert is_snapshot_timestamp_fresh(fresh, max_age_minutes=30.0, now=now) is True
    assert is_snapshot_timestamp_fresh(stale, max_age_minutes=30.0, now=now) is False
    assert is_snapshot_timestamp_fresh(None, max_age_minutes=30.0, now=now) is False


def test_neutralize_hydro_reservoir_for_entry_sets_target_only_for_hydro():
    centrales = [
        {
            "id": "h1",
            "type": "HYDRO",
            "reservoir_level_pct": 70.0,
        },
        {
            "id": "t1",
            "type": "THERMAL",
            "available_capacity_mw": 100.0,
        },
    ]

    diagnostics = neutralize_hydro_reservoir_for_entry(centrales, target_reservoir_pct=100.0)

    assert centrales[0]["reservoir_level_pct"] == 100.0
    assert "reservoir_level_pct" not in centrales[1]
    assert diagnostics["hydro_entry_neutralized"] is True
    assert diagnostics["hydro_entry_reservoir_changes"] == 1


def test_build_manual_catalog_from_live_sets_online_for_positive_mapped_generation():
    base = [
        {
            "id": "coca_codo_1",
            "name": "Coca Codo Sinclair",
            "type": "HYDRO",
            "installed_capacity_mw": 1500.0,
            "available_capacity_mw": 1500.0,
            "status": "ONLINE",
        },
        {
            "id": "thermal_a",
            "name": "Termo A",
            "type": "THERMAL",
            "installed_capacity_mw": 100.0,
            "available_capacity_mw": 100.0,
            "status": "MAINTENANCE",
        },
    ]
    live = [
        {"plant_name": "Coca Codo", "plant_type": "HYDRO", "mwh": 1200.0},
        {"plant_name": "Termo A", "plant_type": "THERMAL", "mwh": 50.0},
    ]

    result = build_manual_catalog_from_live(base, live)
    by_id = {str(item["id"]): item for item in result}

    assert by_id["coca_codo_1"]["status"] == "ONLINE"
    assert by_id["coca_codo_1"]["available_capacity_mw"] == 1200.0
    assert by_id["thermal_a"]["status"] == "ONLINE"
    assert by_id["thermal_a"]["available_capacity_mw"] == 50.0


def test_build_manual_catalog_from_live_preserves_status_when_no_generation_match():
    base = [
        {
            "id": "thermal_b",
            "name": "Termo B",
            "type": "THERMAL",
            "installed_capacity_mw": 200.0,
            "available_capacity_mw": 180.0,
            "status": "MAINTENANCE",
        }
    ]

    result = build_manual_catalog_from_live(base, live_plants=[])

    assert result[0]["status"] == "MAINTENANCE"
    assert result[0]["available_capacity_mw"] == 180.0


def test_normalize_hydro_contract_removes_legacy_hydro_fields():
    base = [
        {
            "id": "h1",
            "type": "HYDRO",
            "reservoir_level_pct": 70.0,
            "inflow_index": 1.2,
            "drought_factor": 0.3,
        }
    ]

    result = normalize_hydro_contract(base)

    assert "inflow_index" not in result[0]
    assert "drought_factor" not in result[0]
    assert result[0]["reservoir_level_pct"] == 70.0


def test_build_manual_catalog_from_live_with_diagnostics_maps_renewable_to_wind_solar_pool():
    base = [
        {
            "id": "w1",
            "name": "Villonaco",
            "type": "WIND",
            "installed_capacity_mw": 100.0,
            "available_capacity_mw": 80.0,
            "status": "ONLINE",
        },
        {
            "id": "s1",
            "name": "Solar Sur",
            "type": "SOLAR",
            "installed_capacity_mw": 100.0,
            "available_capacity_mw": 60.0,
            "status": "ONLINE",
        },
    ]
    live = [
        {"plant_name": "Renovable", "plant_type": "RENEWABLE", "mwh": 75.0},
    ]

    baseline, diagnostics = build_manual_catalog_from_live_with_diagnostics(base, live)

    assert diagnostics["live_by_type_mw"]["RENEWABLE"] == 75.0
    assert diagnostics["unmatched_pool_by_type"] == {}
    by_id = {str(item["id"]): item for item in baseline}
    assert by_id["w1"]["available_capacity_mw"] > 0.0
    assert by_id["s1"]["available_capacity_mw"] > 0.0


def test_build_manual_catalog_from_automatic_state_reports_unallocated_thermal_capacity_gap():
    base = [
        {
            "id": "t1",
            "name": "Termo Uno",
            "type": "THERMAL",
            "installed_capacity_mw": 100.0,
            "available_capacity_mw": 100.0,
            "status": "ONLINE",
        }
    ]
    state = SimulationState(
        hydro_mw=0.0,
        thermal_mw=500.0,
        renewable_mw=0.0,
        metrics=SimulationMetrics(total_supply_mw=500.0),
    )

    baseline, diagnostics = build_manual_catalog_from_automatic_state_with_diagnostics(base, state)

    assert baseline[0]["available_capacity_mw"] == 100.0
    assert diagnostics["target_by_type_mw"]["THERMAL"] == 500.0
    assert diagnostics["mapped_by_type_mw"]["THERMAL"] == 100.0
    assert diagnostics["unallocated_by_type_mw"]["THERMAL"] == 400.0
