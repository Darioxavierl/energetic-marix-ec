"""Tests for charts payload generation and history buffer behavior."""

from src.domain.models.simulation_state import DataSourceMode, SimulationMetrics, SimulationState
from src.ui.charts_data_mapper import (
    append_history_point,
    build_charts_payload,
    build_history_point,
    build_history_point_with_origin,
)


def test_append_history_point_clamps_to_max_points():
    history = []
    append_history_point(history, {"timestamp": "1"}, max_points=2)
    append_history_point(history, {"timestamp": "2"}, max_points=2)
    append_history_point(history, {"timestamp": "3"}, max_points=2)

    assert len(history) == 2
    assert history[0]["timestamp"] == "2"
    assert history[1]["timestamp"] == "3"


def test_build_history_point_uses_state_values():
    state = SimulationState(
        mode=DataSourceMode.MANUAL,
        demand_mw=3000.0,
        hydro_mw=1000.0,
        thermal_mw=1200.0,
        renewable_mw=500.0,
        metrics=SimulationMetrics(total_supply_mw=2700.0),
    )

    point = build_history_point(state)
    assert point["demand_mw"] == 3000.0
    assert point["supply_mw"] == 2700.0
    assert point["hydro_mw"] == 1000.0


def test_build_history_point_with_origin_attaches_event():
    state = SimulationState(mode=DataSourceMode.MANUAL)
    point = build_history_point_with_origin(state, "manual_adjust")
    assert point["event"] == "manual_adjust"


def test_build_payload_uses_hourly_curve_in_automatic_mode():
    state = SimulationState(
        mode=DataSourceMode.AUTOMATIC,
        demand_mw=2800.0,
        hydro_mw=1800.0,
        thermal_mw=700.0,
        renewable_mw=400.0,
        import_mw=10.0,
        export_mw=5.0,
        metrics=SimulationMetrics(total_supply_mw=2905.0, balance_mw=105.0, reserve_margin_pct=3.75, risk_level="CRITICAL"),
    )
    hourly_curve = [
        {
            "hour": "10:00",
            "demand_mw": 2800.0,
            "total_mw": 2900.0,
            "hydro_mw": 1700.0,
            "thermal_mw": 800.0,
            "renewable_mw": 400.0,
        }
    ]

    payload = build_charts_payload(state=state, history=[{"timestamp": "local", "demand_mw": 1}], hourly_curve=hourly_curve)
    assert payload["timeline_source"] == "hourly_curve"
    assert payload["timeline"][0]["timestamp"] == "10:00"
    assert payload["timeline"][0]["supply_mw"] == 2900.0


def test_build_payload_uses_session_history_in_manual_mode():
    state = SimulationState(
        mode=DataSourceMode.MANUAL,
        demand_mw=2800.0,
        hydro_mw=1500.0,
        thermal_mw=900.0,
        renewable_mw=300.0,
        metrics=SimulationMetrics(total_supply_mw=2700.0, balance_mw=-100.0, reserve_margin_pct=-3.57, risk_level="FAILURE"),
    )
    history = [
        {
            "timestamp": "t1",
            "demand_mw": 100.0,
            "supply_mw": 90.0,
            "hydro_mw": 30.0,
            "thermal_mw": 40.0,
            "renewable_mw": 20.0,
            "event": "manual_adjust",
        }
    ]

    payload = build_charts_payload(state=state, history=history, hourly_curve=[{"hour": "11:00", "demand_mw": 200.0}])
    assert payload["timeline_source"] == "session_history"
    assert payload["timeline"][0]["timestamp"] == "t1"
    assert payload["generation_by_type"]["HYDRO"] == 1500.0
    assert payload["recent_events"][0]["event"] == "manual_adjust"
