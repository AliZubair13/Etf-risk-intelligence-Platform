"""
Investigation Orchestration Engine.

run_investigation(etf, date) is the single entry point that ties together
everything built in Phases 4-12:
    1. Anomaly check (Phase 5)
    2. Attribution (Phase 4)
    3. Risk decomposition (Phase 6)
    4. Event ranking (Phase 12, which internally uses Phases 9-11)
    5. Confidence scoring (Phase 14)
    6. Persist as an Investigation record with a status

This function contains NO new financial math - it only orchestrates
calls to services already built and validated in prior phases.
"""
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.models.investigation import Investigation
from app.services.attribution_service import compute_attribution
from app.services.anomaly_service import detect_anomaly_statistical, detect_anomaly_isolation_forest
from app.services.risk_service import compute_risk_decomposition
from app.services.event_scoring_service import rank_events_for_investigation
from app.services.confidence_service import compute_confidence
from app.services.llm_explanation_service import generate_explanation
from app.services.explanation_guardrail_service import verify_explanation

logger = logging.getLogger(__name__)


def get_or_create_investigation(etf: str, target_date: date, db: Session) -> Investigation:
    inv_id = f"{etf.upper()}|{target_date}"
    inv = db.query(Investigation).filter(Investigation.id == inv_id).first()
    if not inv:
        inv = Investigation(
            id=inv_id,
            etf_ticker=etf.upper(),
            analysis_date=target_date,
            status="created",
        )
        db.add(inv)
        db.commit()
    return inv


def run_investigation(etf: str, target_date: date, db: Session, force_refresh: bool = False) -> dict:
    """
    Main orchestration entry point.
    Returns the full investigation result as a dict, and persists it.
    """
    etf = etf.upper()
    inv = get_or_create_investigation(etf, target_date, db)

    # Return cached result if already processed and not forcing refresh
    if inv.status in ("ready_for_review", "approved") and not force_refresh:
        logger.info(f"Returning cached investigation for {etf} {target_date}")
        return investigation_to_dict(inv)

    inv.status = "processing"
    db.commit()

    try:
        # Step 1: Anomaly check
        anomaly_stat = detect_anomaly_statistical(etf, target_date, db)
        anomaly_if = detect_anomaly_isolation_forest(etf, target_date, db)

        if "error" in anomaly_stat:
            inv.status = "failed"
            inv.error_message = anomaly_stat["error"]
            db.commit()
            return investigation_to_dict(inv)

        is_anomaly = anomaly_stat.get("is_anomaly", False)

        # Step 2: Attribution (holding contributions + benchmark-adjusted return)
        attribution = compute_attribution(etf, target_date, db)
        if "error" in attribution:
            inv.status = "failed"
            inv.error_message = attribution["error"]
            db.commit()
            return investigation_to_dict(inv)

        # Step 3: Risk decomposition (market/sector/company-specific)
        risk = compute_risk_decomposition(etf, target_date, db)

        # Step 4: Event ranking (retrieves candidates, extracts entities,
        # scores via semantic relevance + timing + weight + price + source + sentiment)
        all_contributors = (
            attribution.get("top_negative_contributors", [])
            + attribution.get("top_positive_contributors", [])
        )
        ranked_events = rank_events_for_investigation(
            etf_ticker=etf,
            target_date=target_date,
            etf_return_pct=attribution["etf_return_pct"],
            top_contributors=all_contributors,
            db=db,
            window_days=15,
        )

        # Step 5: Confidence score (Phase 14)
        confidence = compute_confidence(attribution, ranked_events, anomaly_stat, anomaly_if)

        # Step 5b: Generate evidence-backed explanation (Phase 15) - the ONLY LLM step
        investigation_snapshot = {
            "etf_ticker": etf,
            "analysis_date": str(target_date),
            "attribution": attribution,
            "risk_decomposition": risk,
            "ranked_events": ranked_events,
            "confidence_score": confidence["confidence"],
        }
        explanation_result = generate_explanation(investigation_snapshot)
        guardrail_report = None
        if explanation_result.get("generated_text"):
            guardrail_report = verify_explanation(
                explanation_result["generated_text"],
                explanation_result["payload_used"],
            )

        # Step 6: Determine primary driver (top-ranked event's category, or top contributor)
        top_events = ranked_events.get("top_events", [])
        if top_events:
            primary_driver = f"{top_events[0]['ticker']} - {top_events[0]['event_category']}"
        elif attribution.get("top_negative_contributors"):
            primary_driver = attribution["top_negative_contributors"][0]["ticker"]
        else:
            primary_driver = "unexplained"

        # Persist results
        inv.is_anomaly = "true" if is_anomaly else "false"
        inv.primary_driver = primary_driver
        inv.confidence_score = confidence["confidence"]
        inv.attribution_json = attribution
        inv.anomaly_json = {"statistical": anomaly_stat, "isolation_forest": anomaly_if}
        inv.risk_decomposition_json = risk
        inv.ranked_events_json = ranked_events
        inv.generated_summary = explanation_result.get("generated_text")
        inv.guardrail_json = guardrail_report
        inv.status = "ready_for_review"
        inv.error_message = None
        db.commit()

        logger.info(f"Investigation complete: {etf} {target_date} - confidence={confidence['confidence']}")
        return investigation_to_dict(inv)

    except Exception as e:
        logger.error(f"Investigation failed for {etf} {target_date}: {e}")
        inv.status = "failed"
        inv.error_message = str(e)
        db.commit()
        return investigation_to_dict(inv)


def investigation_to_dict(inv: Investigation) -> dict:
    return {
        "id": inv.id,
        "etf_ticker": inv.etf_ticker,
        "analysis_date": str(inv.analysis_date),
        "status": inv.status,
        "is_anomaly": inv.is_anomaly == "true" if inv.is_anomaly else None,
        "primary_driver": inv.primary_driver,
        "confidence_score": float(inv.confidence_score) if inv.confidence_score else None,
        "attribution": inv.attribution_json,
        "anomaly": inv.anomaly_json,
        "risk_decomposition": inv.risk_decomposition_json,
        "ranked_events": inv.ranked_events_json,
        "generated_summary": inv.generated_summary,
        "guardrail": inv.guardrail_json,
        "error_message": inv.error_message,
    }
