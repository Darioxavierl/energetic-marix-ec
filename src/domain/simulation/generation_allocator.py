"""Helpers to allocate generation and utilization across technology types."""


def split_renewable_generation(
    renewable_mw: float,
    wind_capacity_mw: float,
    solar_capacity_mw: float,
) -> dict[str, float]:
    """Split renewable generation proportionally to installed capacities."""

    total_capacity = max(0.0, wind_capacity_mw) + max(0.0, solar_capacity_mw)
    if renewable_mw <= 0.0 or total_capacity <= 0.0:
        return {"WIND": 0.0, "SOLAR": 0.0}

    wind_share = max(0.0, wind_capacity_mw) / total_capacity
    wind_mw = renewable_mw * wind_share
    solar_mw = max(0.0, renewable_mw - wind_mw)
    return {"WIND": wind_mw, "SOLAR": solar_mw}


def calculate_utilization_by_type(
    generation_by_type_mw: dict[str, float],
    installed_by_type_mw: dict[str, float],
) -> dict[str, float]:
    """Calculate normalized utilization (0 to 1) for each technology type."""

    utilization: dict[str, float] = {}
    for plant_type, installed in installed_by_type_mw.items():
        generated = max(0.0, generation_by_type_mw.get(plant_type, 0.0))
        if installed <= 0.0:
            utilization[plant_type] = 0.0
            continue
        utilization[plant_type] = min(1.0, generated / installed)
    return utilization