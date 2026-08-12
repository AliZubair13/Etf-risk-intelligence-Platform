from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from app.database.connection import Base


class AnalystFeedback(Base):
    __tablename__ = "analyst_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    investigation_id = Column(String(50), nullable=False)
    event_id = Column(String(50), nullable=True)  # nullable - some feedback is investigation-level

    # Feedback types (per Phase 17 spec):
    # event_relevant, event_irrelevant, category_corrected,
    # missing_event_added, explanation_supported, explanation_unsupported,
    # investigation_approved
    feedback_type = Column(String(30), nullable=False)

    original_value = Column(String(200), nullable=True)  # e.g. original event_category
    corrected_value = Column(String(200), nullable=True)  # e.g. analyst-corrected category
    comment = Column(Text, nullable=True)

    model_version = Column(String(20), default="v1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
