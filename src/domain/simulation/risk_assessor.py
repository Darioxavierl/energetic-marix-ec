"""Risk classification rules for grid stability."""


class RiskAssessor:
    """Classifies operational risk from reserve margin."""

    @staticmethod
    def classify_by_reserve_margin(reserve_margin_pct: float) -> str:
        """Return textual level from reserve thresholds."""

        if reserve_margin_pct >= 20.0:
            return "SAFE"
        if reserve_margin_pct >= 10.0:
            return "ALERT"
        if reserve_margin_pct >= 0.0:
            return "CRITICAL"
        return "FAILURE"
