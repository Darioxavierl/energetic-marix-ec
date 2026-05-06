"""Helpers to build chart payloads and maintain chart history buffers."""

from __future__ import annotations

from datetime import datetime

from src.domain.models.simulation_state import DataSourceMode, SimulationState


def append_history_point(history: list[dict], point: dict, max_points: int) -> list[dict]:
    """Append point and clamp history to max points."""

    history.append(point)
    if max_points > 0 and len(history) > max_points:
        del history[: len(history) - max_points]
    return history


def build_history_point(state: SimulationState) -> dict:
    """Build a compact history sample from current simulation state."""

    timestamp = datetime.now().isoformat(timespec="seconds")
    return {
        "timestamp": timestamp,
        "demand_mw": float(state.demand_mw),
        "supply_mw": float(state.metrics.total_supply_mw),
        "hydro_mw": float(state.hydro_mw),
        "thermal_mw": float(state.thermal_mw),
        "renewable_mw": float(state.renewable_mw),
    }


def build_history_point_with_origin(state: SimulationState, origin: str | None) -> dict:
    """Build history point and attach source event origin."""

    point = build_history_point(state)
    point["event"] = str(origin or "state_updated")
    return point


def extract_recent_events(history: list[dict], limit: int = 8) -> list[dict]:
    """Extract recent non-sync events from history."""

    events: list[dict] = []
    for item in history:
        event = str(item.get("event", "")).strip()
        if not event or event == "sync":
            continue
        events.append({"timestamp": str(item.get("timestamp", "")), "event": event})
    if limit > 0 and len(events) > limit:
        return events[-limit:]
    return events


def build_charts_payload(
    state: SimulationState,
    history: list[dict],
    hourly_curve: list[dict] | None,
) -> dict:
    """Build dashboard payload consumed by chart web widget."""

    mode = state.mode.value
    use_hourly_curve = mode == DataSourceMode.AUTOMATIC.value and bool(hourly_curve)

    timeline_source = "hourly_curve" if use_hourly_curve else "session_history"
    timeline = []
    if use_hourly_curve:
        for item in hourly_curve or []:
            timeline.append(
                {
                    "timestamp": str(item.get("hour", item.get("timestamp", ""))),
                    "demand_mw": float(item.get("demand_mw", 0.0) or 0.0),
                    "supply_mw": float(
                        item.get("total_production_mw", item.get("total_mw", 0.0)) or 0.0
                    ),
                    "hydro_mw": float(item.get("hydro_mw", 0.0) or 0.0),
                    "thermal_mw": float(item.get("thermal_mw", 0.0) or 0.0),
                    "renewable_mw": float(item.get("renewable_mw", 0.0) or 0.0),
                }
            )
    else:
        timeline = list(history)

    recent_events = extract_recent_events(history)

    return {
        "mode": mode,
        "risk_level": str(state.metrics.risk_level),
        "reserve_margin_pct": float(state.metrics.reserve_margin_pct),
        "demand_mw": float(state.demand_mw),
        "supply_mw": float(state.metrics.total_supply_mw),
        "balance_mw": float(state.metrics.balance_mw),
        "demand_source": str(state.demand_source),
        "supply_source": str(state.supply_source),
        "operational_window_hours": float(state.operational_window_hours),
        "units_note": "Operativo en MW; reporte oficial CENACE en MWh",
        "import_mw": float(state.import_mw),
        "export_mw": float(state.export_mw),
        "official_summary": {
            "total_mwh": float(state.official_total_mwh),
            "hydro_mwh": float(state.official_hydro_mwh),
            "thermal_mwh": float(state.official_thermal_mwh),
            "renewable_mwh": float(state.official_renewable_mwh),
            "import_mwh": float(state.official_import_mwh),
            "export_mwh": float(state.official_export_mwh),
        },
        "generation_by_type": {
            "HYDRO": float(state.hydro_mw),
            "THERMAL": float(state.thermal_mw),
            "RENEWABLE": float(state.renewable_mw),
        },
        "timeline_source": timeline_source,
        "timeline": timeline,
        "recent_events": recent_events,
    }
