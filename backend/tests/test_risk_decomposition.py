"""
Unit tests for risk decomposition engine.
"""
import pytest
from datetime import date
from app.services.risk_service import compute_risk_decomposition, fit_rolling_regression
from app.database.connection import SessionLocal


def test_decomposition_reconciles():
    """Alpha + market + sector + residual should equal ETF return."""
    db = SessionLocal()
    result = compute_risk_decomposition("SMH", date(2025, 1, 27), db)
    db.close()

    assert "error" not in result, f"Got error: {result.get('error')}"
    assert result["reconciliation_error_bps"] < 1.0, "Decomposition should reconcile almost exactly"


def test_spy_has_no_sector_factor():
    """SPY is the market itself, should have no sector beta."""
    db = SessionLocal()
    result = compute_risk_decomposition("SPY", date(2025, 1, 27), db)
    db.close()

    assert "error" not in result
    assert result["regression"]["beta_sector"] is None


def test_smh_has_sector_factor():
    """SMH should use QQQ as sector proxy."""
    db = SessionLocal()
    result = compute_risk_decomposition("SMH", date(2025, 1, 27), db)
    db.close()

    assert "error" not in result
    assert result["sector_ticker"] == "QQQ"
    assert result["regression"]["beta_sector"] is not None


def test_regression_uses_no_lookahead():
    """Regression window_end should be strictly before target_date."""
    db = SessionLocal()
    target = date(2025, 1, 27)
    reg = fit_rolling_regression("SMH", target, db)
    db.close()

    assert "error" not in reg
    window_end = date.fromisoformat(reg["window_end"])
    assert window_end < target, "No look-ahead bias: window must end before target date"


def test_minimum_observations_enforced():
    """Regression should fail gracefully with too few observations."""
    db = SessionLocal()
    # Very early date, before 40 trading days of history exist
    result = fit_rolling_regression("SMH", date(2022, 1, 20), db)
    db.close()

    # Should either work with fewer obs (Feb 2022+) or return error
    assert "error" in result or result.get("observations_used", 0) >= 40


if __name__ == "__main__":
    db = SessionLocal()
    result = compute_risk_decomposition("SMH", date(2025, 1, 27), db)
    db.close()
    print(f"\nSMH Risk Decomposition (2025-01-27):")
    print(f"ETF return:        {result['etf_return_pct']:.2f}%")
    print(f"Market return:     {result['market_return_pct']:.2f}%")
    print(f"Sector return:     {result['sector_return_pct']:.2f}%")
    print(f"\nRegression:")
    print(f"  Alpha:           {result['regression']['alpha']:.6f}")
    print(f"  Beta (market):   {result['regression']['beta_market']:.4f}")
    print(f"  Beta (sector):   {result['regression']['beta_sector']:.4f}")
    print(f"  R-squared:       {result['regression']['r_squared']:.4f}")
    print(f"\nDecomposition:")
    print(f"  Market contrib:  {result['decomposition']['market_contribution_pct']:.2f}%")
    print(f"  Sector contrib:  {result['decomposition']['sector_contribution_pct']:.2f}%")
    print(f"  Company-specific:{result['decomposition']['company_specific_pct']:.2f}%")
    print(f"\nReconciliation error: {result['reconciliation_error_bps']:.4f} bps")
    print(f"Interpretation: {result['interpretation']}")
