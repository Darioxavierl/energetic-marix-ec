"""Application-level scenario management with local persistence."""

from __future__ import annotations

import json
import copy
from datetime import datetime
from pathlib import Path

from config.settings import HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
from src.domain.models.simulation_state import SimulationState


class ScenarioManager:
    """Creates, stores, loads and deletes named simulation scenarios."""

    DROUGHT_PRESETS: dict[str, dict[str, float]] = {
        "leve": {"global_drought": 0.2, "reservoir_scale": 0.9},
        "media": {"global_drought": 0.45, "reservoir_scale": 0.75},
        "severa": {"global_drought": 0.7, "reservoir_scale": 0.6},
    }

    def __init__(self, scenarios_dir: Path):
        self.scenarios_dir = scenarios_dir
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

    def list_scenarios(self) -> list[str]:
        """Return sorted scenario names discovered on disk."""

        names = [file.stem for file in self.scenarios_dir.glob("*.json")]
        names.sort()
        return names

    def save(self, name: str, state: SimulationState, centrales: list[dict] | None = None) -> Path:
        """Persist scenario state to JSON file."""

        safe_name = self._sanitize_name(name)
        target = self.scenarios_dir / f"{safe_name}.json"
        payload = {
            "schema_version": 2,
            "name": safe_name,
            "saved_at": datetime.now().isoformat(),
            "state": state.as_dict(),
            "centrales": self._normalize_centrales_contract(centrales),
        }
        target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return target

    def load(self, name: str) -> SimulationState:
        """Load scenario state from disk by name."""

        bundle = self.load_bundle(name)
        return bundle["state"]

    def load_bundle(self, name: str) -> dict:
        """Load scenario state and optional centrales payload from disk by name."""

        safe_name = self._sanitize_name(name)
        source = self.scenarios_dir / f"{safe_name}.json"
        if not source.exists():
            raise FileNotFoundError(f"Escenario no existe: {safe_name}")

        payload = json.loads(source.read_text(encoding="utf-8"))
        raw_centrales = payload.get("centrales", None)
        centrales = self._normalize_centrales_contract(raw_centrales)
        return {
            "schema_version": int(payload.get("schema_version", 1) or 1),
            "state": SimulationState.from_dict(payload.get("state", {})),
            "centrales": centrales,
        }

    def duplicate(self, source_name: str, target_name: str) -> Path:
        """Duplicate a scenario under a different name."""

        bundle = self.load_bundle(source_name)
        return self.save(target_name, bundle["state"], centrales=bundle.get("centrales"))

    def create_drought_preset(
        self,
        preset_name: str,
        target_name: str,
        base_state: SimulationState,
        base_centrales: list[dict],
    ) -> Path:
        """Create a drought preset scenario derived from a base state and catalog."""

        preset_key = preset_name.strip().lower()
        config = self.DROUGHT_PRESETS.get(preset_key)
        if not config:
            valid = ", ".join(sorted(self.DROUGHT_PRESETS.keys()))
            raise ValueError(f"Preset de sequia no valido: {preset_name}. Opciones: {valid}")

        state = copy.deepcopy(base_state)
        state.global_drought_factor = float(config["global_drought"])

        centrales = copy.deepcopy(base_centrales)
        for central in centrales:
            if str(central.get("type", "")).upper() != "HYDRO":
                continue
            reservoir = float(
                central.get("reservoir_level_pct", HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT)
                or HYDRO_DEFAULT_RESERVOIR_LEVEL_PCT
            )
            central["reservoir_level_pct"] = max(0.0, min(100.0, reservoir * float(config["reservoir_scale"])))

        return self.save(target_name, state, centrales=centrales)

    @staticmethod
    def _normalize_centrales_contract(raw_centrales: list[dict] | None) -> list[dict] | None:
        """Normalize centrales payload to current scenario contract while keeping compatibility."""

        if raw_centrales is None:
            return None
        if not isinstance(raw_centrales, list):
            return None

        normalized = copy.deepcopy(raw_centrales)
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
