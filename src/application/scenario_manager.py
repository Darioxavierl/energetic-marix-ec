"""Application-level scenario management with local persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.domain.models.simulation_state import SimulationState


class ScenarioManager:
    """Creates, stores, loads and deletes named simulation scenarios."""

    def __init__(self, scenarios_dir: Path):
        self.scenarios_dir = scenarios_dir
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

    def list_scenarios(self) -> list[str]:
        """Return sorted scenario names discovered on disk."""

        names = [file.stem for file in self.scenarios_dir.glob("*.json")]
        names.sort()
        return names

    def save(self, name: str, state: SimulationState) -> Path:
        """Persist scenario state to JSON file."""

        safe_name = self._sanitize_name(name)
        target = self.scenarios_dir / f"{safe_name}.json"
        payload = {
            "name": safe_name,
            "saved_at": datetime.now().isoformat(),
            "state": state.as_dict(),
        }
        target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return target

    def load(self, name: str) -> SimulationState:
        """Load scenario state from disk by name."""

        safe_name = self._sanitize_name(name)
        source = self.scenarios_dir / f"{safe_name}.json"
        if not source.exists():
            raise FileNotFoundError(f"Escenario no existe: {safe_name}")

        payload = json.loads(source.read_text(encoding="utf-8"))
        return SimulationState.from_dict(payload.get("state", {}))

    def duplicate(self, source_name: str, target_name: str) -> Path:
        """Duplicate a scenario under a different name."""

        state = self.load(source_name)
        return self.save(target_name, state)

    def delete(self, name: str) -> None:
        """Delete scenario file if present."""

        safe_name = self._sanitize_name(name)
        target = self.scenarios_dir / f"{safe_name}.json"
        if target.exists():
            target.unlink()

    @staticmethod
    def _sanitize_name(value: str) -> str:
        """Normalize a scenario name into a safe filename token."""

        base = value.strip().replace(" ", "_")
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        filtered = "".join(ch for ch in base if ch in allowed)
        return filtered or "scenario"
