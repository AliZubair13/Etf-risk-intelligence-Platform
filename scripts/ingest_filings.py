import sys
import os
import logging
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal, create_tables
from app.ingestion.sec_filings import ingest_all_filings
from app.models.holding import ETFHolding

create_tables()
db = SessionLocal()

tickers = [t[0] for t in db.query(ETFHolding.security_ticker).distinct().all()]
print(f"Ingesting filings for {len(tickers)} tickers...")

try:
    total = ingest_all_filings(db, tickers, start_date=date(2022, 1, 1))
    print(f"Done. Total filings inserted: {total}")
except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    db.close()
