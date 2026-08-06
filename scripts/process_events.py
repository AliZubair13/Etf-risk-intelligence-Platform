import sys
import os
import logging
from sqlalchemy import or_

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database.connection import SessionLocal
from app.models.filing import Filing
from app.models.filing_embedding import FilingEmbedding
from app.services.event_classification_service import classify_event, compute_content_hash
from app.services.sentiment_service import score_sentiment
from app.services.embedding_service import embed_text

db = SessionLocal()

filings = (
    db.query(Filing)
    .filter(Filing.cleaned_text.isnot(None))
    .filter(or_(Filing.processing_status != "processed", Filing.processing_status.is_(None)))
    .all()
)

print(f"Processing {len(filings)} filings...")

processed = 0
for i, f in enumerate(filings):
    if i % 50 == 0:
        print(f"Progress: {i}/{len(filings)}")

    f.event_category = classify_event(f.item_codes)

    sentiment = score_sentiment(f.cleaned_text)
    f.sentiment_label = sentiment["label"]
    f.sentiment_score = sentiment["score"]

    f.content_hash = compute_content_hash(f.ticker, f.filing_date, f.item_codes, f.cleaned_text)

    vector = embed_text(f.cleaned_text)
    if vector:
        existing_emb = db.query(FilingEmbedding).filter(FilingEmbedding.filing_id == f.id).first()
        if not existing_emb:
            emb = FilingEmbedding(filing_id=f.id, embedding=vector)
            db.add(emb)
        f.embedding_generated = "true"

    f.processing_status = "processed"
    processed += 1

    if i % 50 == 0:
        db.commit()

db.commit()
db.close()
print(f"Done. Processed {processed} filings.")
