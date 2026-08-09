"""
Event Ranking Engine.

EventScore = 0.30 * semantic_relevance
           + 0.20 * time_proximity
           + 0.20 * affected_etf_weight
           + 0.15 * price_reaction_strength
           + 0.10 * source_reliability
           + 0.05 * sentiment_alignment

Weights are v1 defaults (from product_requirements.md), tunable via
analyst feedback in Phase 17.

IMPORTANT: This scoring is fully deterministic and transparent.
No LLM is involved in ranking - only in later explanation generation (Phase 15).
"""
import math
import logging
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.filing import Filing
from app.models.holding import ETFHolding
from app.models.price import DailyPrice
from app.services.semantic_relevance_service import score_semantic_relevance

logger = logging.getLogger(__name__)

WEIGHTS = {
    "semantic_relevance": 0.30,
    "time_proximity": 0.20,
    "affected_etf_weight": 0.20,
    "price_reaction_strength": 0.15,
    "source_reliability": 0.10,
    "sentiment_alignment": 0.05,
}

# Source reliability tiers - SEC filings are highest tier (regulatory, verified)
SOURCE_RELIABILITY = {
    "8-K": 1.0,
    "10-Q": 0.95,
    "10-K": 0.95,
}


def score_time_proximity(filing_date: date, target_date: date, max_days: int = 10) -> float:
    """
    Exponential decay: closer to target_date = higher score.
    Score of 1.0 for same-day, decaying to ~0 by max_days.
    """
    days_diff = abs((filing_date - target_date).days)
    if days_diff > max_days:
        return 0.0
    return math.exp(-days_diff / 3.0)  # decay constant tuned for ~3-day half-relevance


def score_affected_etf_weight(ticker: str, etf_ticker: str, target_date: date, db: Session) -> float:
    """
    How much of the ETF is exposed to this company.
    Returns the holding's weight in the ETF (0 to 1), or 0 if not a holding.
    """
    holding = (
        db.query(ETFHolding)
        .filter(
            ETFHolding.etf_ticker == etf_ticker,
            ETFHolding.security_ticker == ticker,
            ETFHolding.effective_date <= target_date,
        )
        .order_by(ETFHolding.effective_date.desc())
        .first()
    )
    if not holding:
        return 0.0
    return min(1.0, float(holding.weight) * 5)  # scale up since max weight is ~20%


def score_price_reaction_strength(ticker: str, target_date: date, db: Session) -> float:
    """
    How strongly did the company's stock move on/near this date?
    Normalized against typical volatility (rough z-score style, capped 0-1).
    """
    price = db.query(DailyPrice).filter(
        DailyPrice.ticker == ticker,
        DailyPrice.trade_date == target_date,
    ).first()

    if not price or price.daily_return is None:
        return 0.0

    abs_return = abs(float(price.daily_return))
    # Normalize: 10%+ move = max score, scale linearly below that
    return min(1.0, abs_return / 0.10)


def score_source_reliability(filing_type: str) -> float:
    return SOURCE_RELIABILITY.get(filing_type, 0.5)


def score_sentiment_alignment(
    sentiment_negative_prob: Optional[float],
    sentiment_positive_prob: Optional[float],
    etf_return_pct: float,
) -> float:
    """
    For a negative ETF move, negative event sentiment should score higher alignment.
    For a positive ETF move, positive event sentiment should score higher.
    """
    if sentiment_negative_prob is None or sentiment_positive_prob is None:
        return 0.5  # neutral default

    if etf_return_pct < 0:
        return float(sentiment_negative_prob)
    else:
        return float(sentiment_positive_prob)


def compute_event_score(
    filing: Filing,
    etf_ticker: str,
    target_date: date,
    etf_return_pct: float,
    investigation_context: str,
    db: Session,
) -> dict:
    """
    Compute the full weighted EventScore for one filing/event.
    """
    semantic = score_semantic_relevance(investigation_context, filing.id, db)
    time_prox = score_time_proximity(filing.filing_date, target_date)
    etf_weight = score_affected_etf_weight(filing.ticker, etf_ticker, target_date, db)
    price_reaction = score_price_reaction_strength(filing.ticker, filing.filing_date, db)
    source_rel = score_source_reliability(filing.filing_type)
    sentiment_align = score_sentiment_alignment(
        float(filing.sentiment_negative_prob) if filing.sentiment_negative_prob else None,
        float(filing.sentiment_positive_prob) if filing.sentiment_positive_prob else None,
        etf_return_pct,
    )

    final_score = (
        WEIGHTS["semantic_relevance"] * semantic
        + WEIGHTS["time_proximity"] * time_prox
        + WEIGHTS["affected_etf_weight"] * etf_weight
        + WEIGHTS["price_reaction_strength"] * price_reaction
        + WEIGHTS["source_reliability"] * source_rel
        + WEIGHTS["sentiment_alignment"] * sentiment_align
    )

    return {
        "filing_id": filing.id,
        "ticker": filing.ticker,
        "filing_type": filing.filing_type,
        "filing_date": str(filing.filing_date),
        "event_category": filing.event_category,
        "sentiment_label": filing.sentiment_label,
        "document_url": filing.document_url,
        "score_breakdown": {
            "semantic_relevance": round(semantic, 4),
            "time_proximity": round(time_prox, 4),
            "affected_etf_weight": round(etf_weight, 4),
            "price_reaction_strength": round(price_reaction, 4),
            "source_reliability": round(source_rel, 4),
            "sentiment_alignment": round(sentiment_align, 4),
        },
        "final_score": round(final_score, 4),
    }


def rank_events_for_investigation(
    etf_ticker: str,
    target_date: date,
    etf_return_pct: float,
    top_contributors: list,
    db: Session,
    window_days: int = 5,
    top_n: int = 5,
) -> list:
    """
    Main entry point: find candidate filings near target_date for the
    top contributing holdings, score them all, return top N ranked.
    """
    from app.services.semantic_relevance_service import build_investigation_context
    from datetime import timedelta

    context = build_investigation_context(etf_ticker, etf_return_pct, top_contributors)

    contributor_tickers = [c["ticker"] for c in top_contributors]
    window_start = target_date - timedelta(days=window_days)
    window_end = target_date + timedelta(days=window_days)

    candidates = db.query(Filing).filter(
        Filing.ticker.in_(contributor_tickers),
        Filing.filing_date >= window_start,
        Filing.filing_date <= window_end,
        Filing.embedding_generated == "true",
    ).all()

    logger.info(f"Found {len(candidates)} candidate events for {etf_ticker} on {target_date}")

    scored = [
        compute_event_score(f, etf_ticker, target_date, etf_return_pct, context, db)
        for f in candidates
    ]
    scored.sort(key=lambda x: x["final_score"], reverse=True)

    return {
        "investigation_context": context,
        "candidates_evaluated": len(candidates),
        "top_events": scored[:top_n],
    }
