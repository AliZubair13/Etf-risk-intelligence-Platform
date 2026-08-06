from sqlalchemy import Column, String, Numeric, DateTime, Integer
from sqlalchemy.sql import func
from app.database.connection import Base


class EventEntity(Base):
    __tablename__ = "event_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filing_id = Column(String(50), nullable=False)
    matched_ticker = Column(String(10), nullable=False)
    extracted_text = Column(String(200), nullable=True)  # the actual matched phrase
    extraction_method = Column(String(20), nullable=False)  # exact_match, alias_match, ner
    confidence = Column(Numeric(5, 4), nullable=False)
    is_primary = Column(String(5), default="false")  # true if this is the filing's own ticker
    analyst_corrected = Column(String(5), default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
