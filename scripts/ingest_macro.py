import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal, create_tables
from app.ingestion.macro_data import ingest_all_macro_series

create_tables()
db = SessionLocal()

try:
    print("Ingesting macro series...")
    total = ingest_all_macro_series(db, start_date="2022-01-01")
    print(f"Done. Total observations inserted: {total}")
except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    db.close()
