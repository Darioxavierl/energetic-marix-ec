"""Tests for simplified hydro-physical model behavior."""

from src.domain.simulation.hydro_physics import (
    compute_hydro_availability_factor,
    compute_hydro_effective_generation_mw,
)


def test_hydro_generation_drops_with_drought():
    base = compute_hydro_effective_generation_mw(
        available_capacity_mw=100.0,
        status="ONLINE",
        reservoir_level_pct=90.0,
        global_drought_factor=0.0,
    )
    with_drought = compute_hydro_effective_generation_mw(
        available_capacity_mw=100.0,
        status="ONLINE",
        reservoir_level_pct=90.0,
        global_drought_factor=0.4,
    )

    assert with_drought < base


def test_hydro_generation_drops_with_lower_reservoir():
    high_state = compute_hydro_effective_generation_mw(
        available_capacity_mw=100.0,
        status="ONLINE",
        reservoir_level_pct=95.0,
        global_drought_factor=0.0,
    )
    low_state = compute_hydro_effective_generation_mw(
        available_capacity_mw=100.0,
        status="ONLINE",
        reservoir_level_pct=30.0,
        global_drought_factor=0.0,
    )

    assert low_state < high_state


def test_offline_hydro_generation_is_zero():
    assert (
        compute_hydro_effective_generation_mw(
            available_capacity_mw=200.0,
            status="OFFLINE",
            reservoir_level_pct=100.0,
            global_drought_factor=0.0,
        )
        == 0.0
    )


def test_availability_factor_is_bounded():
    factor = compute_hydro_availability_factor(
        reservoir_level_pct=150.0,
        global_drought_factor=-1.0,
    )

    assert 0.0 <= factor <= 1.0
