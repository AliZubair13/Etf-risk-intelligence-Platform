"""
Deduplication logic.
Layer 1 (deterministic): content_hash match, same accession_number (DB constraint already handles this)
Layer 2 (semantic): cosine similarity on embeddings within a time window
"""
import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.filing import Filing
from app.models.filing_embedding import FilingEmbedding
from app.services.embedding_service import cosine_similarity

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92  # high bar - only near-identical content


def find_semantic_duplicates(db: Session, ticker: str, window_days: int = 3) -> list:
    """
    Find groups of filings for a ticker that are semantically near-duplicate
    within a rolling time window (e.g. same earnings reported via 8-K + press release).
    """
    filings = (
        db.query(Filing)
        .filter(Filing.ticker == ticker, Filing.processing_status == "processed")
        .order_by(Filing.filing_date)
        .all()
    )

    duplicate_groups = []
    checked = set()

    for i, f1 in enumerate(filings):
        if f1.id in checked:
            continue
        emb1 = db.query(FilingEmbedding).filter(FilingEmbedding.filing_id == f1.id).first()
        if not emb1:
            continue

        group = [f1.id]
        for f2 in filings[i + 1:]:
            if abs((f2.filing_date - f1.filing_date).days) > window_days:
                break
            emb2 = db.query(FilingEmbedding).filter(FilingEmbedding.filing_id == f2.id).first()
            if not emb2:
                continue
            sim = cosine_similarity(emb1.embedding, emb2.embedding)
            if sim >= SIMILARITY_THRESHOLD:
                group.append(f2.id)
                checked.add(f2.id)

        if len(group) > 1:
            duplicate_groups.append(group)
        checked.add(f1.id)

    return duplicate_groups
