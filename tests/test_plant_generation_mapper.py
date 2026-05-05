"""Tests for mapping live plant payloads to static centrales."""

from src.application.plant_generation_mapper import (
    calculate_plant_utilization,
    map_live_generation_to_centrales,
)


def test_map_live_generation_prefers_name_match():
    centrales = [
        {"id": "coca_codo_1", "name": "Coca Codo Sinclair", "type": "HYDRO", "installed_capacity_mw": 1500},
        {"id": "mazar_1", "name": "Mazar", "type": "HYDRO", "installed_capacity_mw": 160},
    ]
    live_plants = [
        {"plant_name": "Coca Codo", "plant_type": "HYDRO", "mwh": 1000},
        {"plant_name": "Mazar", "plant_type": "HYDRO", "mwh": 300},
    ]

    mapped = map_live_generation_to_centrales(centrales, live_plants)

    assert mapped["coca_codo_1"] == 1000
    assert mapped["mazar_1"] == 300


def test_map_live_generation_distributes_unmatched_pool_by_capacity():
    centrales = [
        {"id": "thermal_a", "name": "Termo A", "type": "THERMAL", "installed_capacity_mw": 100},
        {"id": "thermal_b", "name": "Termo B", "type": "THERMAL", "installed_capacity_mw": 300},
    ]
    live_plants = [
        {"plant_name": "Térmica", "plant_type": "THERMAL", "mwh": 400},
    ]

    mapped = map_live_generation_to_centrales(centrales, live_plants)

    assert round(mapped["thermal_a"], 1) == 100.0
    assert round(mapped["thermal_b"], 1) == 300.0


def test_calculate_plant_utilization_clamps_to_one():
    utilization = calculate_plant_utilization(
        generation_by_id_mw={"a": 150, "b": 10},
        installed_by_id_mw={"a": 100, "b": 50, "c": 0},
    )

    assert utilization["a"] == 1.0
    assert utilization["b"] == 0.2
    assert utilization["c"] == 0.0


def test_map_live_generation_distributes_generic_renewable_to_wind_and_solar():
    centrales = [
        {"id": "w1", "name": "Villonaco", "type": "WIND", "installed_capacity_mw": 100},
        {"id": "s1", "name": "Solar Sur", "type": "SOLAR", "installed_capacity_mw": 300},
    ]
    live_plants = [
        {"plant_name": "Renovable", "plant_type": "RENEWABLE", "mwh": 400},
    ]

    mapped = map_live_generation_to_centrales(centrales, live_plants)

    assert round(mapped["w1"], 1) == 100.0
    assert round(mapped["s1"], 1) == 300.0
