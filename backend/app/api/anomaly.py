from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.anomaly_service import (
    detect_anomaly_statistical,
    detect_anomaly_isolation_forest,
    compare_methods,
    scan_anomalies,
)

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


@router.get("/{etf}/{date}/statistical")
def get_statistical_anomaly(etf: str, date: date, db: Session = Depends(get_db)):
    result = detect_anomaly_statistical(etf, date, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{etf}/{date}/isolation-forest")
def get_isolation_forest_anomaly(etf: str, date: date, db: Session = Depends(get_db)):
    result = detect_anomaly_isolation_forest(etf, date, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{etf}/{date}/compare")
def compare_anomaly_methods(etf: str, date: date, db: Session = Depends(get_db)):
    return compare_methods(etf, date, db)


@router.get("/{etf}/scan")
def scan_etf_anomalies(
    etf: str,
    start: date = None,
    end: date = None,
    db: Session = Depends(get_db)
):
    results = scan_anomalies(etf, db, start, end)
    return {
        "etf_ticker": etf.upper(),
        "start": str(start) if start else None,
        "end": str(end) if end else None,
        "total_anomalies": len(results),
        "anomalies": results,
    }
