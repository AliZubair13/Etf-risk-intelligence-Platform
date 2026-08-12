from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.connection import get_db
from app.services.feedback_service import (
    submit_feedback,
    get_feedback_for_investigation,
    compare_rankings_with_labels,
)

router = APIRouter(prefix="/api/feedback", tags=["Analyst Feedback"])


class FeedbackRequest(BaseModel):
    investigation_id: str
    feedback_type: str
    event_id: Optional[str] = None
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    comment: Optional[str] = None


@router.post("")
def create_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    result = submit_feedback(
        investigation_id=req.investigation_id,
        feedback_type=req.feedback_type,
        db=db,
        event_id=req.event_id,
        original_value=req.original_value,
        corrected_value=req.corrected_value,
        comment=req.comment,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{investigation_id}")
def list_feedback(investigation_id: str, db: Session = Depends(get_db)):
    return {"investigation_id": investigation_id, "feedback": get_feedback_for_investigation(investigation_id, db)}


@router.get("/evaluation/summary")
def evaluation_summary(db: Session = Depends(get_db)):
    """Stage 1: compare system rankings against accumulated analyst labels."""
    return compare_rankings_with_labels(db)
