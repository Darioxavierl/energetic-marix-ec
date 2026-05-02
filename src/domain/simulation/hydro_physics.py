"""Simplified hydro-physical model for reservoir and drought effects."""


def clamp(value: float, low: float, high: float) -> float:
    """Clamp value in a numeric range."""

    return max(low, min(high, value))


def compute_hydro_availability_factor(
    reservoir_level_pct: float,
    global_drought_factor: float,
) -> float:
    """Compute hydraulic availability factor in [0, 1]."""

    reservoir_component = clamp(reservoir_level_pct / 100.0, 0.0, 1.0)
    global_drought_component = 1.0 - clamp(global_drought_factor, 0.0, 1.0)

    factor = reservoir_component * global_drought_component
    return clamp(factor, 0.0, 1.0)


def compute_hydro_effective_generation_mw(
    available_capacity_mw: float,
    status: str,
    reservoir_level_pct: float,
    global_drought_factor: float,
) -> float:
    """Return effective hydro generation constrained by hydraulic availability."""

    if status != "ONLINE":
        return 0.0

    base = max(0.0, available_capacity_mw)
    factor = compute_hydro_availability_factor(
        reservoir_level_pct=reservoir_level_pct,
        global_drought_factor=global_drought_factor,
    )
    return base * factor
