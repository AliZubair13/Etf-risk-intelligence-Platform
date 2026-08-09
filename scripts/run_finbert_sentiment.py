import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal
from app.models.filing import Filing
from app.services.finbert_sentiment_service import score_sentiment_finbert

db = SessionLocal()

filings = db.query(Filing).filter(Filing.cleaned_text.isnot(None)).all()
print(f"Scoring {len(filings)} filings with FinBERT...")

for i, f in enumerate(filings):
    if i % 25 == 0:
        print(f"Progress: {i}/{len(filings)}")
        db.commit()

    result = score_sentiment_finbert(f.cleaned_text)
    f.sentiment_label = result["label"]
    f.sentiment_positive_prob = result["positive"]
    f.sentiment_negative_prob = result["negative"]
    f.sentiment_neutral_prob = result["neutral"]
    f.sentiment_score = result["positive"] - result["negative"]  # composite for backward compat
    f.sentiment_model = "finbert"

db.commit()
db.close()
print("Done.")
