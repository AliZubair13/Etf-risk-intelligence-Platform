"""
Financial sentiment using FinBERT (ProsusAI/finbert).
Unlike VADER, this is trained specifically on financial text and
returns a full probability distribution across positive/negative/neutral,
which is what the design doc requires (not just a single label).
"""
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.services.sentiment_service import extract_content_section

logger = logging.getLogger(__name__)

_tokenizer = None
_model = None
LABELS = ["positive", "negative", "neutral"]  # ProsusAI/finbert label order


def get_finbert():
    global _tokenizer, _model
    if _model is None:
        logger.info("Loading FinBERT model (ProsusAI/finbert)...")
        _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        _model.eval()
    return _tokenizer, _model


def score_sentiment_finbert(text: str) -> dict:
    """
    Returns full probability distribution + final label.
    Example: {"label": "negative", "positive": 0.05, "negative": 0.88, "neutral": 0.07}
    """
    if not text:
        return {"label": "neutral", "positive": 0.0, "negative": 0.0, "neutral": 1.0}

    content = extract_content_section(text)
    if not content.strip():
        return {"label": "neutral", "positive": 0.0, "negative": 0.0, "neutral": 1.0}

    tokenizer, model = get_finbert()

    # FinBERT max length is 512 tokens
    inputs = tokenizer(content, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

    prob_dict = {LABELS[i]: round(float(probs[i]), 4) for i in range(len(LABELS))}
    label = max(prob_dict, key=prob_dict.get)

    return {
        "label": label,
        "positive": prob_dict["positive"],
        "negative": prob_dict["negative"],
        "neutral": prob_dict["neutral"],
    }
