import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal, create_tables
from app.ingestion.market_data import ingest_all_prices

create_tables()
db = SessionLocal()

try:
    print("Starting price ingestion...")
    total = ingest_all_prices(db)
    print(f"Done. Total rows inserted: {total}")
except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    db.close()
