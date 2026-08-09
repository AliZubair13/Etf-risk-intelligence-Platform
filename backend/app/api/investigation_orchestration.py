from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from app.database.connection import get_db
from app.services.investigation_service import run_investigation, investigation_to_dict, get_or_create_investigation

router = APIRouter(prefix="/api/investigations", tags=["Investigation Orchestration"])


class InvestigationRequest(BaseModel):
    etf: str
    analysis_date: date


@router.post("")
def create_investigation(req: InvestigationRequest, db: Session = Depends(get_db)):
    """
    Run the full investigation pipeline for an ETF and date.
    Ties together: anomaly detection -> attribution -> risk decomposition
    -> event ranking -> confidence scoring.
    """
    result = run_investigation(req.etf, req.analysis_date, db)
    if result["status"] == "failed":
        raise HTTPException(status_code=422, detail=result["error_message"])
    return result


@router.get("/{etf}/{date}/full")
def get_investigation(etf: str, date: date, db: Session = Depends(get_db)):
    """Retrieve an existing investigation, or run it if it doesn't exist yet."""
    result = run_investigation(etf, date, db)
    if result["status"] == "failed":
        raise HTTPException(status_code=422, detail=result["error_message"])
    return result
