"""
Confidence Score Engine.

confidence = 0.30 * attribution_coverage
           + 0.25 * top_event_score
           + 0.15 * source_agreement
           + 0.15 * time_alignment
           + 0.15 * data_completeness

This is a SYSTEM confidence score - a measure of how well-supported
the investigation's evidence is, NOT a statistical probability that
the explanation is causally correct.
"""

WEIGHTS = {
    "attribution_coverage": 0.30,
    "top_event_score": 0.25,
    "source_agreement": 0.15,
    "time_alignment": 0.15,
    "data_completeness": 0.15,
}


def compute_data_completeness(attribution: dict) -> float:
    missing_count = len(attribution.get("missing_prices", []))
    total_holdings = attribution.get("total_holdings", 1)
    missing_penalty = missing_count / max(total_holdings, 1)

    covered_weight = attribution.get("covered_weight") or 0.5
    coverage_score = min(1.0, covered_weight)

    completeness = (1 - missing_penalty) * 0.5 + coverage_score * 0.5
    return max(0.0, min(1.0, completeness))


def compute_source_agreement(anomaly_stat: dict, anomaly_if: dict) -> float:
    if not anomaly_stat or not anomaly_if:
        return 0.5
    if "error" in anomaly_if:
        return 0.5

    stat_flag = anomaly_stat.get("is_anomaly", False)
    if_flag = anomaly_if.get("is_anomaly", False)
    return 1.0 if stat_flag == if_flag else 0.4


def compute_confidence(
    attribution: dict,
    ranked_events: dict,
    anomaly_stat: dict = None,
    anomaly_if: dict = None,
) -> dict:
    attribution_coverage = attribution.get("attribution_coverage", 0.0)

    top_events = ranked_events.get("top_events", [])
    top_event_score = top_events[0]["final_score"] if top_events else 0.0
    top_event_score_normalized = min(1.0, top_event_score / 0.5)

    time_alignment = (
        top_events[0]["score_breakdown"]["time_proximity"] if top_events else 0.0
    )

    data_completeness = compute_data_completeness(attribution)
    source_agreement = compute_source_agreement(anomaly_stat, anomaly_if)

    confidence = (
        WEIGHTS["attribution_coverage"] * attribution_coverage
        + WEIGHTS["top_event_score"] * top_event_score_normalized
        + WEIGHTS["source_agreement"] * source_agreement
        + WEIGHTS["time_alignment"] * time_alignment
        + WEIGHTS["data_completeness"] * data_completeness
    )

    return {
        "confidence": round(confidence, 4),
        "confidence_pct": round(confidence * 100, 1),
        "components": {
            "attribution_coverage": round(attribution_coverage, 4),
            "top_event_score": round(top_event_score_normalized, 4),
            "source_agreement": round(source_agreement, 4),
            "time_alignment": round(time_alignment, 4),
            "data_completeness": round(data_completeness, 4),
        },
        "disclaimer": (
            "This is a system confidence score reflecting evidence quality "
            "and completeness. It is not a statistical probability that the "
            "explanation is causally correct."
        ),
    }
