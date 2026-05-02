"""Aggregate central-level operational state into type-level generation values."""

from config.settings import (
    HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT,
)
from src.domain.simulation.hydro_physics import compute_hydro_effective_generation_mw


def aggregate_generation_by_plant(
    centrales: list[dict],
    global_drought_factor: float = 0.0,
) -> dict[str, float]:
    """Compute generated MW by central id from current operational fields."""

    generation_by_plant_id: dict[str, float] = {}
    for central in centrales:
        central_id = str(central.get("id", ""))
        plant_type = str(central.get("type", "")).upper()
        status = str(central.get("status", "ONLINE")).upper()
        available = float(central.get("available_capacity_mw", 0.0) or 0.0)

        if not central_id:
            continue

        if plant_type == "HYDRO":
            reservoir = float(
                central.get("reservoir_level_pct", HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT)
                or HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
            )
            generation_by_plant_id[central_id] = compute_hydro_effective_generation_mw(
                available_capacity_mw=available,
                status=status,
                reservoir_level_pct=reservoir,
                global_drought_factor=global_drought_factor,
            )
            continue

        generation_by_plant_id[central_id] = max(0.0, available) if status == "ONLINE" else 0.0

    return generation_by_plant_id


def aggregate_generation_by_type(
    centrales: list[dict],
    global_drought_factor: float = 0.0,
) -> dict[str, float]:
    """Compute aggregated generation by technology type from central states."""

    totals = {
        "HYDRO": 0.0,
        "THERMAL": 0.0,
        "WIND": 0.0,
        "SOLAR": 0.0,
    }

    generation_by_plant_id = aggregate_generation_by_plant(
        centrales=centrales,
        global_drought_factor=global_drought_factor,
    )
    for central in centrales:
        central_id = str(central.get("id", ""))
        plant_type = str(central.get("type", "")).upper()
        if plant_type not in totals:
            continue
        totals[plant_type] += max(0.0, generation_by_plant_id.get(central_id, 0.0))

    return totals
