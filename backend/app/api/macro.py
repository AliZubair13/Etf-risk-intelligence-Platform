from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.database.connection import get_db
from app.models.macro_observation import MacroObservation

router = APIRouter(prefix="/api/macro", tags=["Macro Data"])


@router.get("/{series_code}")
def get_macro_series(
    series_code: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MacroObservation).filter(MacroObservation.series_code == series_code.upper())
    if start:
        query = query.filter(MacroObservation.observation_date >= start)
    if end:
        query = query.filter(MacroObservation.observation_date <= end)

    obs = query.order_by(MacroObservation.observation_date.desc()).limit(50).all()
    if not obs:
        raise HTTPException(status_code=404, detail=f"No data for {series_code}")

    return {
        "series_code": series_code.upper(),
        "count": len(obs),
        "observations": [
            {
                "observation_date": str(o.observation_date),
                "release_date": str(o.release_date) if o.release_date else None,
                "value": float(o.value) if o.value else None,
                "change_pct": float(o.change_pct) if o.change_pct else None,
                "importance": o.importance,
            }
            for o in obs
        ],
    }


@router.get("/")
def list_macro_events_near_date(
    date_param: date,
    window_days: int = 3,
    db: Session = Depends(get_db)
):
    """Get all macro releases within N days of a target date (for event timeline)."""
    from datetime import timedelta
    start = date_param - timedelta(days=window_days)
    end = date_param + timedelta(days=window_days)

    obs = (
        db.query(MacroObservation)
        .filter(MacroObservation.release_date >= start, MacroObservation.release_date <= end)
        .order_by(MacroObservation.release_date)
        .all()
    )

    return {
        "target_date": str(date_param),
        "window_days": window_days,
        "count": len(obs),
        "releases": [
            {
                "series_code": o.series_code,
                "series_name": o.series_name,
                "release_date": str(o.release_date),
                "value": float(o.value) if o.value else None,
                "change_pct": float(o.change_pct) if o.change_pct else None,
                "importance": o.importance,
            }
            for o in obs
        ],
    }
