"""
Risk Decomposition Engine.
Separates ETF daily return into:
    - Market effect (beta to SPY)
    - Sector effect (beta to sector benchmark, e.g. QQQ)
    - Company-specific / idiosyncratic residual

Method: rolling OLS regression
    ETF_return = alpha + beta_market * market_return + beta_sector * sector_return + epsilon

Design decisions (see product_requirements.md Section 15):
    - 60-day rolling window, refit daily
    - Minimum 40 observations
    - No look-ahead bias: coefficients fitted on data through t-1
    - No standardization of returns
"""
import logging
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import statsmodels.api as sm
from app.models.price import DailyPrice
from app.models.etf import ETF

logger = logging.getLogger(__name__)

REGRESSION_WINDOW = 60
MIN_OBSERVATIONS = 40
MARKET_PROXY = "SPY"


def get_return_series(ticker: str, db: Session) -> pd.Series:
    """Get daily return series for a ticker, indexed by date."""
    prices = (
        db.query(DailyPrice)
        .filter(DailyPrice.ticker == ticker)
        .order_by(DailyPrice.trade_date.asc())
        .all()
    )
    if not prices:
        return pd.Series(dtype=float)

    data = {p.trade_date: float(p.daily_return) for p in prices if p.daily_return is not None}
    return pd.Series(data).sort_index()


def get_sector_proxy(etf_ticker: str, db: Session) -> Optional[str]:
    """
    Determine sector proxy for an ETF.
    SPY has no sector factor (it IS the market).
    QQQ and SMH use QQQ's parent structure per Phase 1 hierarchy.
    """
    etf_record = db.query(ETF).filter(ETF.ticker == etf_ticker).first()
    if not etf_record:
        return None
    if etf_ticker == "SPY":
        return None  # SPY is the market itself
    if etf_ticker == "QQQ":
        return None  # QQQ's benchmark IS SPY (no separate sector factor needed)
    if etf_ticker == "SMH":
        return "QQQ"  # SMH's sector factor is QQQ (tech), market factor is SPY
    return etf_record.benchmark_ticker


def fit_rolling_regression(
    etf_ticker: str,
    target_date: date,
    db: Session,
    window: int = REGRESSION_WINDOW,
) -> dict:
    """
    Fit OLS regression using data from (target_date - window) to (target_date - 1).
    This avoids look-ahead bias: we never use same-day data to fit coefficients.
    """
    etf_ticker = etf_ticker.upper()
    etf_returns = get_return_series(etf_ticker, db)
    market_returns = get_return_series(MARKET_PROXY, db)
    sector_ticker = get_sector_proxy(etf_ticker, db)
    sector_returns = get_return_series(sector_ticker, db) if sector_ticker else None

    if etf_returns.empty or market_returns.empty:
        return {"error": "Insufficient price data"}

    # Fitting window: strictly BEFORE target_date (no look-ahead)
    window_start = target_date - timedelta(days=window * 2)  # buffer for weekends/holidays
    window_end = target_date - timedelta(days=1)

    etf_window = etf_returns[(etf_returns.index >= window_start) & (etf_returns.index <= window_end)]
    market_window = market_returns[(market_returns.index >= window_start) & (market_returns.index <= window_end)]

    # Build regression dataframe
    reg_df = pd.DataFrame({"etf": etf_window, "market": market_window})

    if sector_returns is not None:
        sector_window = sector_returns[(sector_returns.index >= window_start) & (sector_returns.index <= window_end)]
        reg_df["sector"] = sector_window

    reg_df = reg_df.dropna()

    # Take only the most recent `window` observations
    reg_df = reg_df.tail(window)

    if len(reg_df) < MIN_OBSERVATIONS:
        return {
            "error": f"Insufficient observations: {len(reg_df)} < {MIN_OBSERVATIONS}",
            "observations_available": len(reg_df),
        }

    # Build X matrix
    if sector_returns is not None:
        X = reg_df[["market", "sector"]]
        has_sector = True
    else:
        X = reg_df[["market"]]
        has_sector = False

    X = sm.add_constant(X)
    y = reg_df["etf"]

    try:
        model = sm.OLS(y, X).fit()
    except Exception as e:
        return {"error": f"Regression failed: {e}"}

    result = {
        "alpha": float(model.params.get("const", 0.0)),
        "beta_market": float(model.params.get("market", 0.0)),
        "beta_sector": float(model.params.get("sector", 0.0)) if has_sector else None,
        "r_squared": float(model.rsquared),
        "observations_used": len(reg_df),
        "window_start": str(reg_df.index.min()),
        "window_end": str(reg_df.index.max()),
        "has_sector_factor": has_sector,
        "sector_ticker": sector_ticker,
    }
    return result


def compute_risk_decomposition(etf_ticker: str, target_date: date, db: Session) -> dict:
    """
    Main risk decomposition function.
    Returns market effect, sector effect, and company-specific residual
    for the ETF's return on target_date.
    """
    etf_ticker = etf_ticker.upper()

    # Get actual returns on target date
    etf_returns = get_return_series(etf_ticker, db)
    market_returns = get_return_series(MARKET_PROXY, db)

    if target_date not in etf_returns.index:
        return {"error": f"No ETF return for {etf_ticker} on {target_date}"}
    if target_date not in market_returns.index:
        return {"error": f"No market return for {MARKET_PROXY} on {target_date}"}

    etf_return = float(etf_returns[target_date])
    market_return = float(market_returns[target_date])

    sector_ticker = get_sector_proxy(etf_ticker, db)
    sector_return = None
    if sector_ticker:
        sector_returns = get_return_series(sector_ticker, db)
        if target_date in sector_returns.index:
            sector_return = float(sector_returns[target_date])

    # Fit regression using data through t-1
    regression = fit_rolling_regression(etf_ticker, target_date, db)
    if "error" in regression:
        return {
            "etf_ticker": etf_ticker,
            "date": str(target_date),
            "error": regression["error"],
            "etf_return": etf_return,
        }

    alpha = regression["alpha"]
    beta_market = regression["beta_market"]
    beta_sector = regression["beta_sector"]

    # Compute contributions using fitted betas and TODAY's factor returns
    market_contribution = beta_market * market_return

    if beta_sector is not None and sector_return is not None:
        sector_contribution = beta_sector * sector_return
    else:
        sector_contribution = 0.0

    # Predicted return from the model
    predicted_return = alpha + market_contribution + sector_contribution

    # Company-specific / idiosyncratic residual
    company_specific = etf_return - predicted_return

    # Sanity check: alpha + market + sector + residual should equal etf_return
    reconstructed = alpha + market_contribution + sector_contribution + company_specific
    reconciliation_error = abs(reconstructed - etf_return)

    return {
        "etf_ticker": etf_ticker,
        "date": str(target_date),
        "etf_return_pct": round(etf_return * 100, 4),
        "market_return_pct": round(market_return * 100, 4),
        "sector_return_pct": round(sector_return * 100, 4) if sector_return is not None else None,
        "sector_ticker": sector_ticker,
        "regression": {
            "alpha": round(alpha, 6),
            "beta_market": round(beta_market, 4),
            "beta_sector": round(beta_sector, 4) if beta_sector is not None else None,
            "r_squared": round(regression["r_squared"], 4),
            "observations_used": regression["observations_used"],
            "window_start": regression["window_start"],
            "window_end": regression["window_end"],
        },
        "decomposition": {
            "alpha_contribution_pct": round(alpha * 100, 4),
            "market_contribution_pct": round(market_contribution * 100, 4),
            "sector_contribution_pct": round(sector_contribution * 100, 4),
            "company_specific_pct": round(company_specific * 100, 4),
        },
        "reconciliation_error_bps": round(reconciliation_error * 10000, 4),
        "interpretation": _interpret_decomposition(
            market_contribution, sector_contribution, company_specific, etf_return
        ),
    }


def _interpret_decomposition(market_c, sector_c, company_c, etf_return) -> str:
    """Generate a plain-language interpretation of what drove the move."""
    if abs(etf_return) < 0.001:
        return "Minimal movement; no dominant factor."

    components = {
        "market-wide": abs(market_c),
        "sector": abs(sector_c),
        "company-specific": abs(company_c),
    }
    dominant = max(components, key=components.get)
    dominant_pct = components[dominant] / sum(components.values()) * 100 if sum(components.values()) > 0 else 0

    return f"{dominant.capitalize()} effects were dominant ({dominant_pct:.0f}% of explained variance)."
