from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.event_entity import EventEntity
from app.models.filing import Filing

router = APIRouter(prefix="/api/entities", tags=["Entity Extraction"])


@router.get("/filing/{filing_id}")
def get_filing_entities(filing_id: str, db: Session = Depends(get_db)):
    entities = db.query(EventEntity).filter(EventEntity.filing_id == filing_id).all()
    if not entities:
        raise HTTPException(status_code=404, detail="No entities found for this filing")
    return {
        "filing_id": filing_id,
        "entities": [
            {
                "ticker": e.matched_ticker,
                "matched_text": e.extracted_text,
                "method": e.extraction_method,
                "confidence": float(e.confidence),
                "is_primary": e.is_primary == "true",
            }
            for e in entities
        ],
    }


@router.get("/mentions/{ticker}")
def get_filings_mentioning_ticker(ticker: str, db: Session = Depends(get_db)):
    """Find filings (from OTHER companies) that mention this ticker."""
    entities = (
        db.query(EventEntity)
        .filter(EventEntity.matched_ticker == ticker.upper(), EventEntity.is_primary == "false")
        .all()
    )
    if not entities:
        raise HTTPException(status_code=404, detail=f"No cross-mentions found for {ticker}")

    results = []
    for e in entities:
        filing = db.query(Filing).filter(Filing.id == e.filing_id).first()
        if filing:
            results.append({
                "mentioned_in_filing_by": filing.ticker,
                "filing_date": str(filing.filing_date),
                "filing_type": filing.filing_type,
                "matched_text": e.extracted_text,
                "confidence": float(e.confidence),
            })

    return {"ticker": ticker.upper(), "count": len(results), "mentions": results}
