"""
Unit tests for attribution engine.
Tests the core financial math — no AI, no mocks for the math itself.
"""
import pytest
from datetime import date
from app.services.attribution_service import compute_attribution
from app.database.connection import SessionLocal


def test_attribution_smh_deepsee_shock():
    """Jan 27 2025: DeepSeek shock — SMH dropped ~10%."""
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 27), db)
    db.close()

    assert "error" not in result, f"Got error: {result.get('error')}"
    assert result["etf_return_pct"] < -5.0, "SMH should have dropped >5% on DeepSeek day"
    assert len(result["top_negative_contributors"]) > 0
    assert result["reconciliation_error_bps"] < 200, "Reconciliation error should be reasonable"
    print(f"ETF return: {result['etf_return_pct']:.2f}%")
    print(f"Explained: {result['explained_return_pct']:.2f}%")
    print(f"Residual: {result['residual_return_pct']:.2f}%")
    print(f"Reconciliation error: {result['reconciliation_error_bps']:.1f} bps")


def test_attribution_returns_required_fields():
    """Test that attribution result contains all required fields."""
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 27), db)
    db.close()

    required_fields = [
        "etf_ticker", "date", "etf_return", "explained_return",
        "residual_return", "reconciliation_error", "reconciliation_error_bps",
        "attribution_coverage", "top_negative_contributors",
        "top_positive_contributors", "all_contributions",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"


def test_contributions_sum_to_explained():
    """Test that sum of contributions equals explained return."""
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 27), db)
    db.close()

    if "error" in result:
        pytest.skip("No data for this date")

    total = sum(c["contribution"] for c in result["all_contributions"])
    assert abs(total - result["explained_return"]) < 1e-8, "Contributions must sum to explained return"


def test_weights_are_valid():
    """Test that all weights are between 0 and 1."""
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 27), db)
    db.close()

    if "error" in result:
        pytest.skip("No data")

    for c in result["all_contributions"]:
        assert 0 < c["weight"] < 1, f"Invalid weight for {c['ticker']}: {c['weight']}"


def test_missing_date_returns_error():
    """Test that a weekend date returns an error gracefully."""
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 25), db)  # Saturday
    db.close()
    assert "error" in result


if __name__ == "__main__":
    db = SessionLocal()
    result = compute_attribution("SMH", date(2025, 1, 27), db)
    db.close()
    print(f"\nSMH DeepSeek shock (2025-01-27):")
    print(f"ETF return:      {result['etf_return_pct']:.2f}%")
    print(f"Explained:       {result['explained_return_pct']:.2f}%")
    print(f"Residual:        {result['residual_return_pct']:.2f}%")
    print(f"Recon error:     {result['reconciliation_error_bps']:.1f} bps")
    print(f"Coverage:        {result['attribution_coverage']*100:.1f}%")
    print(f"\nTop negative contributors:")
    for c in result["top_negative_contributors"]:
        print(f"  {c['ticker']:6s}: weight={c['weight_pct']:.2f}%  return={c['daily_return_pct']:.2f}%  contribution={c['contribution_pct']:.4f}%")
