"""
Financial sentiment scoring for filing text.
Uses VADER (lexicon-based, fast, no GPU needed).

FIX: SEC filings begin with ~1000-1500 chars of boilerplate cover-page
text (registrant info, checkboxes, legal disclosures) which is sentiment-
neutral noise. We skip past this and sample from the actual disclosure
content, which typically starts after the last "Item X.XX" marker in
the header block.
"""
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

BOILERPLATE_MARKERS = [
    "emerging growth company",
    "transition period for complying",
]


def extract_content_section(text: str) -> str:
    """
    Skip past SEC 8-K cover-page boilerplate to find actual disclosure content.
    Strategy: find the last occurrence of known boilerplate markers, then
    take text starting from there. Falls back to a fixed offset if markers
    aren't found.
    """
    if not text:
        return ""

    lower = text.lower()
    last_marker_pos = 0
    for marker in BOILERPLATE_MARKERS:
        pos = lower.find(marker)
        if pos > last_marker_pos:
            last_marker_pos = pos + len(marker)

    if last_marker_pos > 0:
        return text[last_marker_pos:last_marker_pos + 2500]

    # Fallback: SEC cover pages are typically 1200-1800 chars; skip first 1500
    return text[1500:4000] if len(text) > 1500 else text


def score_sentiment(text: str) -> dict:
    if not text:
        return {"label": "neutral", "score": 0.0}

    content = extract_content_section(text)
    if not content.strip():
        return {"label": "neutral", "score": 0.0}

    scores = _analyzer.polarity_scores(content)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {"label": label, "score": round(compound, 4)}
