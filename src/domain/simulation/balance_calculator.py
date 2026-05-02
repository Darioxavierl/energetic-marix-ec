"""Core balance equations for the simulator."""


class BalanceCalculator:
    """Pure calculation service with no side effects."""

    @staticmethod
    def calculate_total_supply(
        hydro_mw: float,
        thermal_mw: float,
        renewable_mw: float,
        import_mw: float = 0.0,
        export_mw: float = 0.0,
    ) -> float:
        """Compute net available power for the system."""

        return hydro_mw + thermal_mw + renewable_mw + import_mw - export_mw

    @staticmethod
    def calculate_balance(total_supply_mw: float, demand_mw: float) -> float:
        """Positive means surplus; negative means deficit."""

        return total_supply_mw - demand_mw

    @staticmethod
    def calculate_reserve_margin(total_supply_mw: float, demand_mw: float) -> float:
        """Compute reserve margin percentage over demand."""

        if demand_mw <= 0:
            return 0.0
        return ((total_supply_mw - demand_mw) / demand_mw) * 100.0
