from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.attribution_service import compute_attribution

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])


@router.get("/{etf}/{date}/attribution")
def get_attribution(etf: str, date: date, db: Session = Depends(get_db)):
    """
    Calculate holding-level attribution for an ETF on a given date.
    Returns contribution of each holding to the ETF's daily return.
    """
    result = compute_attribution(etf, date, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
