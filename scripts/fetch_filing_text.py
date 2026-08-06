"""
Fetch full text for 8-K filings that don't have it yet.
Prioritizes recent filings (last 2 years) to keep runtime reasonable.
"""
import sys
import os
import time
import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal
from app.models.filing import Filing
from app.ingestion.sec_filings import fetch_filing_document

db = SessionLocal()

cutoff = date.today() - timedelta(days=730)
filings = (
    db.query(Filing)
    .filter(Filing.filing_type == "8-K")
    .filter(Filing.filing_date >= cutoff)
    .filter(Filing.cleaned_text.is_(None))
    .filter(Filing.primary_doc.isnot(None))
    .all()
)

print(f"Fetching text for {len(filings)} 8-K filings...")

updated = 0
for i, f in enumerate(filings):
    if i % 25 == 0:
        print(f"Progress: {i}/{len(filings)}")
    text = fetch_filing_document(f.cik, f.accession_number, f.primary_doc)
    if text:
        f.cleaned_text = text
        f.text_length = str(len(text))
        updated += 1
    time.sleep(0.15)

db.commit()
db.close()
print(f"Done. Updated {updated} filings with full text.")
