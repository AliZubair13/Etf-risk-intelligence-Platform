from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.attribution_service import compute_attribution
from app.services.event_scoring_service import rank_events_for_investigation

router = APIRouter(prefix="/api/events", tags=["Event Ranking"])


@router.get("/{etf}/{date}/ranked")
def get_ranked_events(etf: str, date: date, window_days: int = 15, db: Session = Depends(get_db)):
    attr = compute_attribution(etf, date, db)
    if "error" in attr:
        raise HTTPException(status_code=404, detail=attr["error"])

    all_contributors = attr["top_negative_contributors"] + attr["top_positive_contributors"]

    result = rank_events_for_investigation(
        etf_ticker=etf.upper(),
        target_date=date,
        etf_return_pct=attr["etf_return_pct"],
        top_contributors=all_contributors,
        db=db,
        window_days=window_days,
    )
    return result
