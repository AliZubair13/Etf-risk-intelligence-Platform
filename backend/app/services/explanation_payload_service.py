"""
Builds the structured, minimal evidence payload passed to the LLM.
The LLM sees ONLY this JSON - never raw filing text, never the database,
never anything it could use to invent facts not already computed.
"""


def build_explanation_payload(investigation: dict) -> dict:
    """
    Extract exactly what the LLM needs from a full investigation dict.
    Every field here must be traceable back to a deterministic calculation.
    """
    attribution = investigation.get("attribution", {})
    risk = investigation.get("risk_decomposition", {})
    ranked = investigation.get("ranked_events", {})
    confidence = investigation.get("confidence_score")

    top_contributors = [
        {
            "ticker": c["ticker"],
            "weight_pct": c["weight_pct"],
            "return_pct": c["daily_return_pct"],
            "contribution_pct": c["contribution_pct"],
        }
        for c in attribution.get("top_negative_contributors", [])[:5]
    ]

    risk_components = {}
    if risk and "decomposition" in risk:
        risk_components = {
            "market_contribution_pct": risk["decomposition"]["market_contribution_pct"],
            "sector_contribution_pct": risk["decomposition"]["sector_contribution_pct"],
            "company_specific_pct": risk["decomposition"]["company_specific_pct"],
            "sector_ticker": risk.get("sector_ticker"),
        }

    events = [
        {
            "event_id": e["filing_id"],
            "ticker": e["ticker"],
            "filing_type": e["filing_type"],
            "filing_date": e["filing_date"],
            "event_category": e["event_category"],
            "sentiment_label": e["sentiment_label"],
            "final_score": e["final_score"],
        }
        for e in ranked.get("top_events", [])[:5]
    ]

    payload = {
        "etf": investigation.get("etf_ticker"),
        "date": investigation.get("analysis_date"),
        "daily_return_pct": attribution.get("etf_return_pct"),
        "benchmark_adjusted_return_pct": None,  # computed below if available
        "explained_return_pct": attribution.get("explained_return_pct"),
        "residual_return_pct": attribution.get("residual_return_pct"),
        "reconciliation_error_bps": attribution.get("reconciliation_error_bps"),
        "attribution_coverage": attribution.get("attribution_coverage"),
        "top_contributors": top_contributors,
        "risk_components": risk_components,
        "ranked_events": events,
        "confidence": confidence,
        "residual_note": attribution.get("residual_note"),
    }

    return payload
