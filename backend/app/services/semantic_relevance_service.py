"""
Semantic relevance scoring.
Builds an "investigation context" string from attribution results,
embeds it, and compares against candidate event embeddings via cosine similarity.
"""
import logging
from sqlalchemy.orm import Session
from app.services.embedding_service import embed_text, cosine_similarity
from app.models.filing_embedding import FilingEmbedding
from app.models.filing import Filing

logger = logging.getLogger(__name__)


def build_investigation_context(
    etf_ticker: str,
    etf_return_pct: float,
    top_contributors: list,
) -> str:
    """
    Build a natural-language context string from attribution results.
    Example: "SMH semiconductor ETF declined unusually. Top negative
    contributors were NVIDIA, AMD and Broadcom."
    """
    direction = "declined" if etf_return_pct < 0 else "rose"
    magnitude = "unusually" if abs(etf_return_pct) > 3 else "moderately"

    contributor_names = [c.get("ticker", "") for c in top_contributors[:3]]
    contributor_str = ", ".join(contributor_names)

    context = (
        f"{etf_ticker} ETF {direction} {magnitude} by {abs(etf_return_pct):.1f}%. "
        f"Top contributors were {contributor_str}."
    )
    return context


def score_semantic_relevance(
    investigation_context: str,
    filing_id: str,
    db: Session,
) -> float:
    """
    Compare investigation context embedding to a filing's embedding.
    Returns cosine similarity (0 to 1, higher = more relevant).
    """
    context_embedding = embed_text(investigation_context)
    if context_embedding is None:
        return 0.0

    filing_emb = db.query(FilingEmbedding).filter(FilingEmbedding.filing_id == filing_id).first()
    if not filing_emb:
        return 0.0

    similarity = cosine_similarity(context_embedding, filing_emb.embedding)
    # Cosine similarity can be -1 to 1; clip to 0-1 range for scoring
    return max(0.0, similarity)


def rank_filings_by_relevance(
    investigation_context: str,
    candidate_filing_ids: list,
    db: Session,
) -> list:
    """
    Score and rank a list of candidate filings by semantic relevance
    to the investigation context.
    """
    context_embedding = embed_text(investigation_context)
    if context_embedding is None:
        return []

    results = []
    for filing_id in candidate_filing_ids:
        filing_emb = db.query(FilingEmbedding).filter(FilingEmbedding.filing_id == filing_id).first()
        if not filing_emb:
            continue
        similarity = cosine_similarity(context_embedding, filing_emb.embedding)
        results.append({"filing_id": filing_id, "relevance_score": max(0.0, similarity)})

    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results
