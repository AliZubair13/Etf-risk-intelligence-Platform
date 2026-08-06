"""
Sentence embeddings for semantic similarity and dedup.
Uses sentence-transformers locally (free, no API calls).
"""
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info("Loading sentence-transformer model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # fast, 384-dim, good quality
    return _model


def embed_text(text: str) -> list:
    """Generate embedding vector for a piece of text."""
    if not text:
        return None
    model = get_model()
    sample = text[:1000]  # truncate for speed
    embedding = model.encode(sample, convert_to_numpy=True)
    return embedding.tolist()


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
