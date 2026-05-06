"""Build manual central catalog baseline from live microservice snapshots."""

from __future__ import annotations

import copy
from datetime import datetime
from collections import defaultdict

from config.settings import HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
from config.settings import MANUAL_LIVE_ENERGY_WINDOW_HOURS
from src.application.plant_generation_mapper import map_live_generation_to_centrales_with_diagnostics
from src.domain.models.simulation_state import SimulationState
from src.domain.simulation.generation_aggregator import aggregate_generation_by_type


def normalize_hydro_contract(centrales: list[dict]) -> list[dict]:
    """Normalize hydro fields to current contract (reservoir only)."""

    normalized = copy.deepcopy(centrales)
    for central in normalized:
        if str(central.get("type", "")).upper() != "HYDRO":
            continue
        reservoir = float(
            central.get("reservoir_level_pct", HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT)
            or HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
        )
        central["reservoir_level_pct"] = max(0.0, min(100.0, reservoir))
        central.pop("inflow_index", None)
        central.pop("drought_factor", None)
    return normalized


def has_usable_live_snapshot(live_plants: list[dict]) -> bool:
    """Return True when live snapshot carries positive generation values."""

    return any(float(item.get("mwh", 0.0) or 0.0) > 0.0 for item in live_plants)


def is_snapshot_timestamp_fresh(
    source_timestamp: datetime | None,
    max_age_minutes: float,
    now: datetime | None = None,
) -> bool:
    """Return True if source timestamp exists and is not older than max age."""

    if source_timestamp is None:
        return False
    if max_age_minutes <= 0.0:
        return True

    reference = now or datetime.now()
    age_seconds = (reference - source_timestamp).total_seconds()
    if age_seconds < 0.0:
        # Small clock skews should not invalidate an otherwise fresh snapshot.
        return True
    return age_seconds <= (max_age_minutes * 60.0)


def neutralize_hydro_reservoir_for_entry(
    centrales: list[dict],
    target_reservoir_pct: float = 100.0,
) -> dict:
    """Set hydro reservoir to a neutral value to avoid instant entry penalty."""

    clamped_target = max(0.0, min(100.0, float(target_reservoir_pct)))
    changed = 0

    for central in centrales:
        if str(central.get("type", "")).upper() != "HYDRO":
            continue

        previous = float(
            central.get("reservoir_level_pct", HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT)
            or HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
        )
        central["reservoir_level_pct"] = clamped_target
        if abs(previous - clamped_target) > 1e-6:
            changed += 1

    return {
        "hydro_entry_neutralized": True,
        "hydro_entry_target_reservoir_pct": clamped_target,
        "hydro_entry_reservoir_changes": changed,
    }


def build_manual_catalog_from_live(base_centrales: list[dict], live_plants: list[dict]) -> list[dict]:
    """Project live generation to central catalog for manual mode initialization."""

    baseline, _ = build_manual_catalog_from_live_with_diagnostics(base_centrales, live_plants)
    return baseline


def build_manual_catalog_from_automatic_state(base_centrales: list[dict], automatic_state: SimulationState) -> list[dict]:
    """Project automatic aggregate state into local central catalog."""

    baseline, _ = build_manual_catalog_from_automatic_state_with_diagnostics(base_centrales, automatic_state)
    return baseline


def build_manual_catalog_from_automatic_state_with_diagnostics(
    base_centrales: list[dict],
    automatic_state: SimulationState,
) -> tuple[list[dict], dict]:
    """Build manual baseline from aggregate automatic values and expose allocation diagnostics."""

    baseline = normalize_hydro_contract(base_centrales)
    if not baseline:
        return baseline, {
            "source_state": {},
            "target_by_type_mw": {},
            "mapped_by_type_mw": {},
            "unallocated_by_type_mw": {},
            "status_changes": [],
        }

    by_type_ids: dict[str, list[dict]] = {"HYDRO": [], "THERMAL": [], "WIND": [], "SOLAR": []}
    installed_by_type: dict[str, float] = {"HYDRO": 0.0, "THERMAL": 0.0, "WIND": 0.0, "SOLAR": 0.0}
    for central in baseline:
        plant_type = str(central.get("type", "")).upper()
        if plant_type not in by_type_ids:
            continue
        by_type_ids[plant_type].append(central)
        installed_by_type[plant_type] += max(0.0, float(central.get("installed_capacity_mw", 0.0) or 0.0))

    renewable_total = max(0.0, float(automatic_state.renewable_mw))
    renewable_capacity = installed_by_type["WIND"] + installed_by_type["SOLAR"]
    if renewable_capacity > 0.0:
        renewable_wind = renewable_total * (installed_by_type["WIND"] / renewable_capacity)
        renewable_solar = renewable_total * (installed_by_type["SOLAR"] / renewable_capacity)
    else:
        renewable_wind = 0.0
        renewable_solar = 0.0

    target_by_type = {
        "HYDRO": max(0.0, float(automatic_state.hydro_mw)),
        "THERMAL": max(0.0, float(automatic_state.thermal_mw)),
        "WIND": max(0.0, float(renewable_wind)),
        "SOLAR": max(0.0, float(renewable_solar)),
    }

    mapped_by_type: dict[str, float] = defaultdict(float)
    unallocated_by_type: dict[str, float] = defaultdict(float)
    status_changes: list[dict] = []

    for plant_type, centrales in by_type_ids.items():
        target = target_by_type.get(plant_type, 0.0)
        if not centrales:
            unallocated_by_type[plant_type] += target
            continue

        total_installed = sum(max(0.0, float(c.get("installed_capacity_mw", 0.0) or 0.0)) for c in centrales)
        if total_installed <= 0.0:
            unallocated_by_type[plant_type] += target
            continue

        assigned_sum = 0.0
        for central in centrales:
            installed = max(0.0, float(central.get("installed_capacity_mw", 0.0) or 0.0))
            available_base = max(0.0, float(central.get("available_capacity_mw", installed) or installed))
            previous_status = str(central.get("status", "ONLINE")).upper()
            allocation = target * (installed / total_installed) if total_installed > 0.0 else 0.0
            assigned = min(installed, max(0.0, allocation))
            assigned_sum += assigned

            if assigned > 0.0:
                central["available_capacity_mw"] = assigned
                central["status"] = "ONLINE"
                if previous_status != "ONLINE":
                    status_changes.append({"id": str(central.get("id", "")), "before": previous_status, "after": "ONLINE"})
            else:
                central["available_capacity_mw"] = min(installed, available_base) if installed > 0.0 else available_base

        mapped_by_type[plant_type] += assigned_sum
        if target > assigned_sum:
            unallocated_by_type[plant_type] += (target - assigned_sum)

    diagnostics = {
        "source_state": {
            "hydro_mw": float(automatic_state.hydro_mw),
            "thermal_mw": float(automatic_state.thermal_mw),
            "renewable_mw": float(automatic_state.renewable_mw),
            "supply_mw": float(automatic_state.metrics.total_supply_mw),
        },
        "target_by_type_mw": {k: float(v) for k, v in target_by_type.items()},
        "mapped_by_type_mw": {k: float(v) for k, v in mapped_by_type.items()},
        "unallocated_by_type_mw": {k: float(v) for k, v in unallocated_by_type.items() if float(v) > 0.0},
        "status_changes": status_changes,
    }
    return baseline, diagnostics


def build_manual_catalog_from_live_with_diagnostics(
    base_centrales: list[dict],
    live_plants: list[dict],
) -> tuple[list[dict], dict]:
    """Project live generation to central catalog and return transition diagnostics."""

    baseline = normalize_hydro_contract(base_centrales)
    if not baseline:
        return baseline, {
            "live_by_type_mw": {},
            "mapped_by_type_mw": {},
            "unmatched_pool_by_type": {},
            "status_changes": [],
            "direct_matches": 0,
            "distributed_matches": 0,
        }

    generation_by_id, mapper_diagnostics = map_live_generation_to_centrales_with_diagnostics(
        baseline,
        live_plants,
        energy_window_hours=MANUAL_LIVE_ENERGY_WINDOW_HOURS,
    )
    status_changes: list[dict] = []
    mapped_by_type_mw: dict[str, float] = defaultdict(float)
    live_by_type_mw: dict[str, float] = defaultdict(float)
    live_by_type_mwh: dict[str, float] = defaultdict(float)
    safe_window_hours = max(1e-6, float(MANUAL_LIVE_ENERGY_WINDOW_HOURS))

    for live in live_plants:
        live_type = str(live.get("plant_type", "")).upper()
        live_mwh = max(0.0, float(live.get("mwh", 0.0) or 0.0))
        if live_mwh > 0.0:
            live_by_type_mwh[live_type] += live_mwh
            live_by_type_mw[live_type] += (live_mwh / safe_window_hours)

    for central in baseline:
        cid = str(central.get("id", ""))
        plant_type = str(central.get("type", "")).upper()
        installed = max(0.0, float(central.get("installed_capacity_mw", 0.0) or 0.0))
        available_base = max(0.0, float(central.get("available_capacity_mw", installed) or installed))
        estimated = max(0.0, float(generation_by_id.get(cid, 0.0) or 0.0))
        previous_status = str(central.get("status", "ONLINE")).upper()

        if estimated > 0.0:
            central["available_capacity_mw"] = min(installed, estimated) if installed > 0.0 else estimated
            central["status"] = "ONLINE"
            if previous_status != "ONLINE":
                status_changes.append({"id": cid, "before": previous_status, "after": "ONLINE"})
            mapped_by_type_mw[plant_type] += float(central["available_capacity_mw"])
            continue

        central["available_capacity_mw"] = min(installed, available_base) if installed > 0.0 else available_base
        mapped_by_type_mw[plant_type] += float(central["available_capacity_mw"])

    diagnostics = {
        "energy_window_hours": safe_window_hours,
        "live_by_type_mwh": {k: float(v) for k, v in live_by_type_mwh.items()},
        "live_by_type_mw": {k: float(v) for k, v in live_by_type_mw.items()},
        "mapped_by_type_mw": {k: float(v) for k, v in mapped_by_type_mw.items()},
        "unmatched_pool_by_type": dict(mapper_diagnostics.get("unmatched_pool_by_type", {})),
        "unmatched_pool_by_type_energy_mwh": dict(
            mapper_diagnostics.get("unmatched_pool_by_type_energy_mwh", {})
        ),
        "status_changes": status_changes,
        "direct_matches": int(mapper_diagnostics.get("direct_matches", 0)),
        "distributed_matches": int(mapper_diagnostics.get("distributed_matches", 0)),
    }
    return baseline, diagnostics


def calculate_manual_residual_by_type(
    automatic_state: SimulationState,
    centrales: list[dict],
    global_drought_factor: float = 0.0,
) -> dict:
    """Calculate positive continuity residual needed after mapping catalog into MANUAL."""

    generation_by_type = aggregate_generation_by_type(
        centrales=centrales,
        global_drought_factor=float(global_drought_factor),
    )
    catalog_by_type_mw = {
        "HYDRO": float(generation_by_type.get("HYDRO", 0.0) or 0.0),
        "THERMAL": float(generation_by_type.get("THERMAL", 0.0) or 0.0),
        "RENEWABLE": float(generation_by_type.get("WIND", 0.0) or 0.0)
        + float(generation_by_type.get("SOLAR", 0.0) or 0.0),
    }
    automatic_by_type_mw = {
        "HYDRO": max(0.0, float(automatic_state.hydro_mw or 0.0)),
        "THERMAL": max(0.0, float(automatic_state.thermal_mw or 0.0)),
        "RENEWABLE": max(0.0, float(automatic_state.renewable_mw or 0.0)),
    }
    residual_by_type_mw = {
        plant_type: max(0.0, automatic_by_type_mw.get(plant_type, 0.0) - catalog_by_type_mw.get(plant_type, 0.0))
        for plant_type in ("HYDRO", "THERMAL", "RENEWABLE")
    }
    return {
        "automatic_by_type_mw": automatic_by_type_mw,
        "catalog_by_type_mw": catalog_by_type_mw,
        "residual_by_type_mw": residual_by_type_mw,
        "residual_total_mw": float(sum(residual_by_type_mw.values())),
    }
