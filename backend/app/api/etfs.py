from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date
from app.database.connection import get_db
from app.models.price import DailyPrice
from app.models.etf import ETF
from pydantic import BaseModel

router = APIRouter(prefix="/api/etfs", tags=["ETFs"])


class PriceResponse(BaseModel):
    ticker: str
    trade_date: date
    adjusted_close: float
    daily_return: Optional[float]

    class Config:
        from_attributes = True


@router.get("/")
def list_etfs(db: Session = Depends(get_db)):
    etfs = db.query(ETF).all()
    return [{"ticker": e.ticker, "name": e.name, "benchmark": e.benchmark_ticker} for e in etfs]


@router.get("/{ticker}/prices")
def get_prices(
    ticker: str,
    start: date,
    end: date,
    db: Session = Depends(get_db)
):
    ticker = ticker.upper()
    prices = (
        db.query(DailyPrice)
        .filter(
            and_(
                DailyPrice.ticker == ticker,
                DailyPrice.trade_date >= start,
                DailyPrice.trade_date <= end,
            )
        )
        .order_by(DailyPrice.trade_date)
        .all()
    )
    if not prices:
        raise HTTPException(status_code=404, detail=f"No prices found for {ticker}")

    return {
        "ticker": ticker,
        "start": start,
        "end": end,
        "count": len(prices),
        "prices": [
            {
                "date": str(p.trade_date),
                "adjusted_close": float(p.adjusted_close),
                "daily_return": float(p.daily_return) if p.daily_return else None,
            }
            for p in prices
        ],
    }


@router.get("/{ticker}/prices/summary")
def get_price_summary(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    count = db.query(DailyPrice).filter(DailyPrice.ticker == ticker).count()
    latest = (
        db.query(DailyPrice)
        .filter(DailyPrice.ticker == ticker)
        .order_by(DailyPrice.trade_date.desc())
        .first()
    )
    earliest = (
        db.query(DailyPrice)
        .filter(DailyPrice.ticker == ticker)
        .order_by(DailyPrice.trade_date.asc())
        .first()
    )
    return {
        "ticker": ticker,
        "total_rows": count,
        "earliest_date": str(earliest.trade_date) if earliest else None,
        "latest_date": str(latest.trade_date) if latest else None,
        "latest_close": float(latest.adjusted_close) if latest else None,
        "latest_return": float(latest.daily_return) if latest and latest.daily_return else None,
    }
