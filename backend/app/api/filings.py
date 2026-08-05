from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.database.connection import get_db
from app.models.filing import Filing

router = APIRouter(prefix="/api/filings", tags=["SEC Filings"])


@router.get("/{ticker}")
def get_filings(ticker: str, filing_type: Optional[str] = None,
                start: Optional[date] = None, end: Optional[date] = None,
                db: Session = Depends(get_db)):
    query = db.query(Filing).filter(Filing.ticker == ticker.upper())
    if filing_type:
        query = query.filter(Filing.filing_type == filing_type)
    if start:
        query = query.filter(Filing.filing_date >= start)
    if end:
        query = query.filter(Filing.filing_date <= end)

    filings = query.order_by(Filing.filing_date.desc()).limit(50).all()
    if not filings:
        raise HTTPException(status_code=404, detail=f"No filings found for {ticker}")

    return {
        "ticker": ticker.upper(),
        "count": len(filings),
        "filings": [
            {
                "filing_type": f.filing_type,
                "filing_date": str(f.filing_date),
                "item_codes": f.item_codes,
                "document_url": f.document_url,
            }
            for f in filings
        ],
    }
