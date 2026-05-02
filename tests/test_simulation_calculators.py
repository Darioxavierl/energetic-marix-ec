"""Tests for core simulation calculators."""

from src.domain.simulation.balance_calculator import BalanceCalculator
from src.domain.simulation.risk_assessor import RiskAssessor


def test_balance_calculator_full_flow():
    total_supply = BalanceCalculator.calculate_total_supply(
        hydro_mw=2000.0,
        thermal_mw=800.0,
        renewable_mw=300.0,
        import_mw=50.0,
        export_mw=20.0,
    )
    balance = BalanceCalculator.calculate_balance(total_supply, demand_mw=2900.0)
    reserve = BalanceCalculator.calculate_reserve_margin(total_supply, demand_mw=2900.0)

    assert total_supply == 3130.0
    assert balance == 230.0
    assert reserve > 7.0


def test_risk_assessor_thresholds():
    assert RiskAssessor.classify_by_reserve_margin(25.0) == "SAFE"
    assert RiskAssessor.classify_by_reserve_margin(12.0) == "ALERT"
    assert RiskAssessor.classify_by_reserve_margin(1.0) == "CRITICAL"
    assert RiskAssessor.classify_by_reserve_margin(-3.0) == "FAILURE"
