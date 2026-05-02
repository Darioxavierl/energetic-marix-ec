"""Domain models for simulator state and KPIs."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DataSourceMode(str, Enum):
    """Execution mode for data sourcing and edit permissions."""

    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"


@dataclass
class SimulationMetrics:
    """Calculated KPI values for the current state."""

    total_supply_mw: float = 0.0
    balance_mw: float = 0.0
    reserve_margin_pct: float = 0.0
    risk_level: str = "UNKNOWN"


@dataclass
class SimulationState:
    """Current working state shown in the simulator."""

    mode: DataSourceMode = DataSourceMode.AUTOMATIC
    demand_mw: float = 0.0
    hydro_mw: float = 0.0
    thermal_mw: float = 0.0
    renewable_mw: float = 0.0
    import_mw: float = 0.0
    export_mw: float = 0.0
    source_timestamp: datetime | None = None
    last_manual_edit: datetime | None = None
    metrics: SimulationMetrics = field(default_factory=SimulationMetrics)

    def as_dict(self) -> dict:
        """Serialize state into a plain dictionary for debugging/logging."""

        return {
            "mode": self.mode.value,
            "demand_mw": self.demand_mw,
            "hydro_mw": self.hydro_mw,
            "thermal_mw": self.thermal_mw,
            "renewable_mw": self.renewable_mw,
            "import_mw": self.import_mw,
            "export_mw": self.export_mw,
            "source_timestamp": self.source_timestamp.isoformat() if self.source_timestamp else None,
            "last_manual_edit": self.last_manual_edit.isoformat() if self.last_manual_edit else None,
            "metrics": {
                "total_supply_mw": self.metrics.total_supply_mw,
                "balance_mw": self.metrics.balance_mw,
                "reserve_margin_pct": self.metrics.reserve_margin_pct,
                "risk_level": self.metrics.risk_level,
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SimulationState":
        """Build simulation state from persisted dictionary payload."""

        mode_raw = payload.get("mode", DataSourceMode.AUTOMATIC.value)
        mode = DataSourceMode(mode_raw)

        source_raw = payload.get("source_timestamp")
        source_timestamp = datetime.fromisoformat(source_raw) if source_raw else None

        manual_raw = payload.get("last_manual_edit")
        last_manual_edit = datetime.fromisoformat(manual_raw) if manual_raw else None

        metrics_payload = payload.get("metrics", {})
        metrics = SimulationMetrics(
            total_supply_mw=float(metrics_payload.get("total_supply_mw", 0.0)),
            balance_mw=float(metrics_payload.get("balance_mw", 0.0)),
            reserve_margin_pct=float(metrics_payload.get("reserve_margin_pct", 0.0)),
            risk_level=str(metrics_payload.get("risk_level", "UNKNOWN")),
        )

        return cls(
            mode=mode,
            demand_mw=float(payload.get("demand_mw", 0.0)),
            hydro_mw=float(payload.get("hydro_mw", 0.0)),
            thermal_mw=float(payload.get("thermal_mw", 0.0)),
            renewable_mw=float(payload.get("renewable_mw", 0.0)),
            import_mw=float(payload.get("import_mw", 0.0)),
            export_mw=float(payload.get("export_mw", 0.0)),
            source_timestamp=source_timestamp,
            last_manual_edit=last_manual_edit,
            metrics=metrics,
        )
