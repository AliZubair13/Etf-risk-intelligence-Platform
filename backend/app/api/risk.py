from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.risk_service import compute_risk_decomposition

router = APIRouter(prefix="/api/risk", tags=["Risk Decomposition"])


@router.get("/{etf}/{date}/decomposition")
def get_risk_decomposition(etf: str, date: date, db: Session = Depends(get_db)):
    result = compute_risk_decomposition(etf, date, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
