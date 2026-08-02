"""
Attribution Engine — Core quantitative component.
Calculates holding-level contribution to ETF daily return.
NO AI involved. Pure financial math.

Formula:
    contribution_i = weight_i(t-1) * return_i(t)
    explained_return = sum(contribution_i)
    residual = ETF_return - explained_return
    reconciliation_error = |residual|
"""
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.price import DailyPrice
from app.models.holding import ETFHolding

logger = logging.getLogger(__name__)


def get_etf_return(etf_ticker: str, target_date: date, db: Session) -> Optional[float]:
    """Get the daily return for an ETF on a specific date."""
    price = (
        db.query(DailyPrice)
        .filter(
            DailyPrice.ticker == etf_ticker,
            DailyPrice.trade_date == target_date,
        )
        .first()
    )
    if not price:
        logger.warning(f"No price found for {etf_ticker} on {target_date}")
        return None
    return float(price.daily_return) if price.daily_return else None


def get_holding_return(ticker: str, target_date: date, db: Session) -> Optional[float]:
    """Get the daily return for a holding on a specific date."""
    price = (
        db.query(DailyPrice)
        .filter(
            DailyPrice.ticker == ticker,
            DailyPrice.trade_date == target_date,
        )
        .first()
    )
    if not price or price.daily_return is None:
        return None
    return float(price.daily_return)


def get_most_recent_holdings(etf_ticker: str, target_date: date, db: Session):
    """
    Get the most recent holdings snapshot at or before the target date.
    IMPORTANT: Use t-1 weights to avoid look-ahead bias.
    """
    holdings = (
        db.query(ETFHolding)
        .filter(
            ETFHolding.etf_ticker == etf_ticker,
            ETFHolding.effective_date <= target_date,
        )
        .order_by(ETFHolding.effective_date.desc())
        .all()
    )

    if not holdings:
        logger.warning(f"No holdings found for {etf_ticker} on or before {target_date}")
        return []

    # Get only the most recent effective date
    most_recent_date = holdings[0].effective_date
    return [h for h in holdings if h.effective_date == most_recent_date]


def compute_attribution(etf_ticker: str, target_date: date, db: Session) -> dict:
    """
    Main attribution function.
    Returns full attribution breakdown for an ETF on a given date.
    """
    etf_ticker = etf_ticker.upper()

    # Step 1: Get ETF return
    etf_return = get_etf_return(etf_ticker, target_date, db)
    if etf_return is None:
        return {
            "error": f"No price data for {etf_ticker} on {target_date}",
            "etf_ticker": etf_ticker,
            "date": str(target_date),
        }

    # Step 2: Get holdings (most recent weights on or before target date)
    holdings = get_most_recent_holdings(etf_ticker, target_date, db)
    if not holdings:
        return {
            "error": f"No holdings data for {etf_ticker}",
            "etf_ticker": etf_ticker,
            "date": str(target_date),
        }

    holdings_date = holdings[0].effective_date
    covered_weight = float(holdings[0].covered_weight) if holdings[0].covered_weight else None

    # Step 3: Calculate contribution for each holding
    contributions = []
    missing_prices = []

    for h in holdings:
        ticker = h.security_ticker
        weight = float(h.weight)
        holding_return = get_holding_return(ticker, target_date, db)

        if holding_return is None:
            missing_prices.append(ticker)
            logger.warning(f"Missing price for {ticker} on {target_date}")
            continue

        contribution = weight * holding_return

        contributions.append({
            "ticker": ticker,
            "weight": round(weight, 6),
            "weight_pct": round(weight * 100, 4),
            "daily_return": round(holding_return, 6),
            "daily_return_pct": round(holding_return * 100, 4),
            "contribution": round(contribution, 6),
            "contribution_pct": round(contribution * 100, 4),
        })

    if not contributions:
        return {
            "error": "No holding returns available for this date",
            "etf_ticker": etf_ticker,
            "date": str(target_date),
        }

    # Step 4: Sort by contribution
    contributions.sort(key=lambda x: x["contribution"])

    # Step 5: Calculate summary metrics
    explained_return = sum(c["contribution"] for c in contributions)
    residual_return = etf_return - explained_return
    reconciliation_error = abs(residual_return)

    # Attribution coverage = how much of the absolute ETF move we explain
    if abs(etf_return) > 0:
        attribution_coverage = min(1.0, abs(explained_return) / abs(etf_return))
    else:
        attribution_coverage = 1.0

    # Step 6: Top contributors
    top_negative = sorted(contributions, key=lambda x: x["contribution"])[:5]
    top_positive = sorted(contributions, key=lambda x: x["contribution"], reverse=True)[:5]

    # Step 7: Validation flags
    flags = []
    if reconciliation_error > 0.02:
        flags.append(f"High reconciliation error: {reconciliation_error*100:.2f}%")
    if len(missing_prices) > 0:
        flags.append(f"Missing prices for: {', '.join(missing_prices)}")
    if covered_weight and covered_weight < 0.5:
        flags.append(f"Low coverage: only {covered_weight*100:.1f}% of ETF tracked")

    return {
        "etf_ticker": etf_ticker,
        "date": str(target_date),
        "etf_return": round(etf_return, 6),
        "etf_return_pct": round(etf_return * 100, 4),
        "explained_return": round(explained_return, 6),
        "explained_return_pct": round(explained_return * 100, 4),
        "residual_return": round(residual_return, 6),
        "residual_return_pct": round(residual_return * 100, 4),
        "reconciliation_error": round(reconciliation_error, 6),
        "reconciliation_error_bps": round(reconciliation_error * 10000, 2),
        "attribution_coverage": round(attribution_coverage, 4),
        "covered_weight": covered_weight,
        "holdings_date_used": str(holdings_date),
        "total_holdings": len(contributions),
        "missing_prices": missing_prices,
        "flags": flags,
        "top_negative_contributors": top_negative,
        "top_positive_contributors": top_positive,
        "all_contributions": contributions,
        "residual_note": (
            "Residual includes: untracked holdings, cash, fees, "
            "derivatives, timing differences, and tracking error. "
            "It is NOT purely unexplained market behavior."
        ),
    }
