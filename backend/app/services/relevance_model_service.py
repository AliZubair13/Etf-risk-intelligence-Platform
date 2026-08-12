"""
Phase 17, Stage 2: Model Improvement.

Trains a simple relevance-prediction model using analyst feedback as labels
and the event score features (semantic, time, weight, price reaction,
source reliability, sentiment) as inputs.

This is intentionally a SIMPLE model (logistic regression) - the point
is to demonstrate the feedback loop mechanism, not to build a complex
ML system. With enough labeled data, this could be swapped for
random forest or LightGBM without changing the interface.
"""
import logging
import pickle
import os
from datetime import date
from sqlalchemy.orm import Session
from sklearn.linear_model import LogisticRegression
import numpy as np

from app.models.analyst_feedback import AnalystFeedback
from app.models.filing import Filing
from app.models.investigation import Investigation
from app.services.event_scoring_service import compute_event_score

logger = logging.getLogger(__name__)

MODEL_PATH = "models/saved/relevance_model.pkl"
MIN_TRAINING_SAMPLES = 10  # need at least this many labeled examples to train


def build_training_dataset(db: Session) -> tuple:
    """
    Build (X, y) from analyst feedback.
    X = [semantic_relevance, time_proximity, affected_etf_weight,
         price_reaction_strength, source_reliability, sentiment_alignment]
    y = 1 if event_relevant, 0 if event_irrelevant
    """
    feedback_records = (
        db.query(AnalystFeedback)
        .filter(AnalystFeedback.feedback_type.in_(["event_relevant", "event_irrelevant"]))
        .filter(AnalystFeedback.event_id.isnot(None))
        .all()
    )

    X, y = [], []

    for fb in feedback_records:
        inv = db.query(Investigation).filter(Investigation.id == fb.investigation_id).first()
        if not inv or not inv.ranked_events_json:
            continue

        # Find this event's score breakdown from the stored investigation
        top_events = inv.ranked_events_json.get("top_events", [])
        matching = [e for e in top_events if e["filing_id"] == fb.event_id]
        if not matching:
            continue

        breakdown = matching[0]["score_breakdown"]
        features = [
            breakdown["semantic_relevance"],
            breakdown["time_proximity"],
            breakdown["affected_etf_weight"],
            breakdown["price_reaction_strength"],
            breakdown["source_reliability"],
            breakdown["sentiment_alignment"],
        ]
        label = 1 if fb.feedback_type == "event_relevant" else 0

        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


def train_relevance_model(db: Session) -> dict:
    """
    Train a logistic regression model on accumulated analyst feedback.
    Returns training report. Saves model to disk if successful.
    """
    X, y = build_training_dataset(db)

    if len(X) < MIN_TRAINING_SAMPLES:
        return {
            "trained": False,
            "reason": f"Insufficient labeled data: {len(X)} samples, need at least {MIN_TRAINING_SAMPLES}",
            "samples_available": len(X),
            "samples_needed": MIN_TRAINING_SAMPLES,
        }

    if len(set(y)) < 2:
        return {
            "trained": False,
            "reason": "Need both relevant AND irrelevant examples to train a classifier",
            "samples_available": len(X),
        }

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    train_accuracy = model.score(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    feature_names = [
        "semantic_relevance", "time_proximity", "affected_etf_weight",
        "price_reaction_strength", "source_reliability", "sentiment_alignment",
    ]
    learned_weights = dict(zip(feature_names, model.coef_[0].tolist()))

    logger.info(f"Relevance model trained on {len(X)} samples, accuracy={train_accuracy:.3f}")

    return {
        "trained": True,
        "samples_used": len(X),
        "train_accuracy": round(train_accuracy, 4),
        "learned_weights": {k: round(v, 4) for k, v in learned_weights.items()},
        "model_path": MODEL_PATH,
        "note": (
            "These learned weights can be compared to the original hand-tuned "
            "weights (0.30/0.20/0.20/0.15/0.10/0.05) to see which features "
            "analyst feedback suggests matter most."
        ),
    }


def load_relevance_model():
    """Load the trained model if it exists, else None."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_relevance(score_breakdown: dict) -> float:
    """
    Use the trained model to predict relevance probability for an event,
    given its score breakdown. Falls back to None if no model trained yet.
    """
    model = load_relevance_model()
    if model is None:
        return None

    features = np.array([[
        score_breakdown["semantic_relevance"],
        score_breakdown["time_proximity"],
        score_breakdown["affected_etf_weight"],
        score_breakdown["price_reaction_strength"],
        score_breakdown["source_reliability"],
        score_breakdown["sentiment_alignment"],
    ]])
    prob = model.predict_proba(features)[0][1]  # probability of class 1 (relevant)
    return round(float(prob), 4)
