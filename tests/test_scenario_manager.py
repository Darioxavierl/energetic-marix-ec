"""Tests for scenario manager persistence operations."""

from pathlib import Path

from src.application.scenario_manager import ScenarioManager
from src.domain.models.simulation_state import DataSourceMode, SimulationState


def test_save_and_load_scenario(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    state = SimulationState(mode=DataSourceMode.MANUAL, demand_mw=3000.0, hydro_mw=2100.0)

    manager.save("escenario prueba", state)
    loaded = manager.load("escenario_prueba")

    assert loaded.mode == DataSourceMode.MANUAL
    assert loaded.demand_mw == 3000.0
    assert loaded.hydro_mw == 2100.0


def test_duplicate_and_delete_scenario(tmp_path: Path):
    manager = ScenarioManager(tmp_path)
    manager.save("base", SimulationState(demand_mw=2500.0))

    manager.duplicate("base", "base_copy")
    names = manager.list_scenarios()
    assert "base" in names
    assert "base_copy" in names

    manager.delete("base_copy")
    assert "base_copy" not in manager.list_scenarios()
