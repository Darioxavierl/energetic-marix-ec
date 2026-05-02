"""Tests for generation allocation helpers."""

from src.domain.simulation.generation_allocator import (
    calculate_utilization_by_type,
    split_renewable_generation,
)


def test_split_renewable_generation_by_capacity_share():
    split = split_renewable_generation(
        renewable_mw=300.0,
        wind_capacity_mw=100.0,
        solar_capacity_mw=50.0,
    )

    assert round(split["WIND"], 2) == 200.0
    assert round(split["SOLAR"], 2) == 100.0


def test_split_renewable_generation_handles_zero_capacity():
    split = split_renewable_generation(
        renewable_mw=150.0,
        wind_capacity_mw=0.0,
        solar_capacity_mw=0.0,
    )

    assert split == {"WIND": 0.0, "SOLAR": 0.0}


def test_calculate_utilization_by_type_is_clamped():
    utilization = calculate_utilization_by_type(
        generation_by_type_mw={"HYDRO": 110.0, "THERMAL": 10.0},
        installed_by_type_mw={"HYDRO": 100.0, "THERMAL": 50.0, "WIND": 0.0},
    )

    assert utilization["HYDRO"] == 1.0
    assert utilization["THERMAL"] == 0.2
    assert utilization["WIND"] == 0.0
