"""Risk classification rules for grid stability."""

from config.settings import (
    RISK_THRESHOLD_ALERT_PCT,
    RISK_THRESHOLD_CRITICAL_PCT,
    RISK_THRESHOLD_SAFE_PCT,
)


class RiskAssessor:
    """Classifies operational risk from reserve margin."""

    @staticmethod
    def classify_by_reserve_margin(reserve_margin_pct: float) -> str:
        """Return textual level from reserve thresholds."""

        if reserve_margin_pct >= RISK_THRESHOLD_SAFE_PCT:
            return "SAFE"
        if reserve_margin_pct >= RISK_THRESHOLD_ALERT_PCT:
            return "ALERT"
        if reserve_margin_pct >= RISK_THRESHOLD_CRITICAL_PCT:
            return "CRITICAL"
        return "FAILURE"
