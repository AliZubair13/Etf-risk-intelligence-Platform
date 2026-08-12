import time
import logging
from datetime import date, timedelta
from typing import List
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from app.models.price import DailyPrice
from app.models.holding import ETFHolding
from app.models.etf import ETF

logger = logging.getLogger(__name__)
START_DATE = "2022-01-03"

def get_all_tickers(db: Session) -> List[str]:
    etf_tickers = [e.ticker for e in db.query(ETF).all()]
    holding_tickers = [h.security_ticker for h in db.query(ETFHolding.security_ticker).distinct().all()]
    all_tickers = list(set(etf_tickers + holding_tickers))
    logger.info(f"Total tickers to fetch: {len(all_tickers)}")
    return all_tickers

def fetch_prices_for_ticker(ticker: str, start: str, end: str) -> pd.DataFrame:
    for attempt in range(5):
        try:
            df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False, timeout=20)
            if df.empty:
                logger.warning(f"Empty response for {ticker}, attempt {attempt+1}")
                time.sleep(3 * (attempt + 1))
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            return df
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {ticker}: {e}")
            time.sleep(3 * (attempt + 1))
    logger.error(f"All attempts failed for {ticker} - likely rate limited")
    return pd.DataFrame()

def get_latest_stored_date(ticker: str, db: Session):
    result = (
        db.query(DailyPrice.trade_date)
        .filter(DailyPrice.ticker == ticker)
        .order_by(DailyPrice.trade_date.desc())
        .first()
    )
    return result[0] if result else None

def get_previous_close(ticker: str, before_date, db: Session):
    """Look up the most recent stored close price before a given date."""
    result = (
        db.query(DailyPrice.adjusted_close)
        .filter(DailyPrice.ticker == ticker, DailyPrice.trade_date < before_date)
        .order_by(DailyPrice.trade_date.desc())
        .first()
    )
    return float(result[0]) if result else None

def ingest_prices_for_ticker(ticker: str, db: Session, start: str = START_DATE):
    latest = get_latest_stored_date(ticker, db)
    if latest:
        fetch_start = (latest + timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"{ticker}: incremental from {fetch_start}")
    else:
        fetch_start = start
        logger.info(f"{ticker}: full backfill from {fetch_start}")

    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    if fetch_start >= end_date:
        logger.info(f"{ticker}: up to date")
        return 0

    df = fetch_prices_for_ticker(ticker, fetch_start, end_date)
    if df.empty:
        return 0

    df = df.sort_values("Date").copy()
    inserted = 0

    # Track previous close across rows, seeded from DB if this is a single/few-row batch
    prev_close = get_previous_close(ticker, df.iloc[0]["Date"].date(), db)

    for _, row in df.iterrows():
        trade_date = row["Date"].date() if hasattr(row["Date"], "date") else row["Date"]
        price_id = f"{ticker}|{trade_date}"

        exists = db.query(DailyPrice).filter(DailyPrice.id == price_id).first()
        if exists:
            prev_close = float(row["Close"]) if pd.notna(row["Close"]) else prev_close
            continue

        adj_close = float(row["Close"]) if pd.notna(row["Close"]) else None
        if adj_close is None or adj_close <= 0:
            continue

        daily_return = None
        if prev_close is not None and prev_close != 0:
            daily_return = (adj_close / prev_close) - 1

        price = DailyPrice(
            id=price_id,
            ticker=ticker,
            trade_date=trade_date,
            open=float(row["Open"]) if pd.notna(row.get("Open")) else None,
            high=float(row["High"]) if pd.notna(row.get("High")) else None,
            low=float(row["Low"]) if pd.notna(row.get("Low")) else None,
            close=float(row["Close"]) if pd.notna(row.get("Close")) else None,
            adjusted_close=adj_close,
            volume=int(row["Volume"]) if pd.notna(row.get("Volume")) else None,
            daily_return=daily_return,
        )
        db.add(price)
        inserted += 1
        prev_close = adj_close

    db.commit()
    logger.info(f"{ticker}: inserted {inserted} rows")
    return inserted

def ingest_all_prices(db: Session):
    tickers = get_all_tickers(db)
    total = 0
    failed_tickers = []
    for i, ticker in enumerate(tickers):
        logger.info(f"Processing {i+1}/{len(tickers)}: {ticker}")
        count = ingest_prices_for_ticker(ticker, db)
        if count == 0:
            latest = get_latest_stored_date(ticker, db)
            if not latest or latest < date.today() - timedelta(days=3):
                failed_tickers.append(ticker)
        total += count
        time.sleep(1.5)

    if failed_tickers:
        logger.warning(f"Retrying {len(failed_tickers)} likely rate-limited tickers: {failed_tickers}")
        time.sleep(10)
        for ticker in failed_tickers:
            count = ingest_prices_for_ticker(ticker, db)
            total += count
            time.sleep(2)

    logger.info(f"Total rows inserted: {total}")
    return total
