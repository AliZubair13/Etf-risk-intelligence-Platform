"""
Analyst Feedback Service (Phase 17, Stage 1).

Handles storing analyst feedback and comparing system rankings
against analyst judgments.
"""
import logging
from sqlalchemy.orm import Session
from app.models.analyst_feedback import AnalystFeedback
from app.models.investigation import Investigation

logger = logging.getLogger(__name__)

VALID_FEEDBACK_TYPES = {
    "event_relevant",
    "event_irrelevant",
    "category_corrected",
    "missing_event_added",
    "explanation_supported",
    "explanation_unsupported",
    "investigation_approved",
}


def submit_feedback(
    investigation_id: str,
    feedback_type: str,
    db: Session,
    event_id: str = None,
    original_value: str = None,
    corrected_value: str = None,
    comment: str = None,
) -> dict:
    """Store one piece of analyst feedback."""
    if feedback_type not in VALID_FEEDBACK_TYPES:
        return {"error": f"Invalid feedback_type. Must be one of: {VALID_FEEDBACK_TYPES}"}

    feedback = AnalystFeedback(
        investigation_id=investigation_id,
        event_id=event_id,
        feedback_type=feedback_type,
        original_value=original_value,
        corrected_value=corrected_value,
        comment=comment,
    )
    db.add(feedback)

    # If this is an approval, update the investigation status
    if feedback_type == "investigation_approved":
        inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if inv:
            inv.status = "approved"

    db.commit()
    logger.info(f"Feedback stored: {feedback_type} for {investigation_id}")

    return {
        "id": feedback.id,
        "investigation_id": investigation_id,
        "feedback_type": feedback_type,
        "status": "saved",
    }


def get_feedback_for_investigation(investigation_id: str, db: Session) -> list:
    """Retrieve all feedback for one investigation."""
    records = (
        db.query(AnalystFeedback)
        .filter(AnalystFeedback.investigation_id == investigation_id)
        .order_by(AnalystFeedback.created_at)
        .all()
    )
    return [
        {
            "id": r.id,
            "event_id": r.event_id,
            "feedback_type": r.feedback_type,
            "original_value": r.original_value,
            "corrected_value": r.corrected_value,
            "comment": r.comment,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


def compare_rankings_with_labels(db: Session) -> dict:
    """
    Stage 1: Evaluation.
    Compare system event rankings against analyst relevance labels.
    Computes precision-style metrics: of events the system ranked highly,
    how many did analysts confirm as relevant?
    """
    all_feedback = db.query(AnalystFeedback).filter(
        AnalystFeedback.feedback_type.in_(["event_relevant", "event_irrelevant"])
    ).all()

    if not all_feedback:
        return {
            "total_labeled_events": 0,
            "message": "No analyst feedback collected yet. Submit feedback via the dashboard first.",
        }

    relevant_count = sum(1 for f in all_feedback if f.feedback_type == "event_relevant")
    irrelevant_count = sum(1 for f in all_feedback if f.feedback_type == "event_irrelevant")
    total = len(all_feedback)

    # Since our system only surfaces top-5 ranked events, every labeled event
    # WAS ranked highly by the system. So "precision of top-ranked events" =
    # fraction analysts confirmed relevant.
    precision_at_top = relevant_count / total if total > 0 else 0.0

    return {
        "total_labeled_events": total,
        "analyst_confirmed_relevant": relevant_count,
        "analyst_marked_irrelevant": irrelevant_count,
        "precision_at_top_ranked": round(precision_at_top, 4),
        "interpretation": (
            f"Of {total} top-ranked events analysts reviewed, "
            f"{relevant_count} ({precision_at_top*100:.1f}%) were confirmed relevant."
        ),
    }
