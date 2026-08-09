from sqlalchemy import Column, String, Date, DateTime, Text, Numeric, JSON
from sqlalchemy.sql import func
from app.database.connection import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(50), primary_key=True)
    etf_ticker = Column(String(10), nullable=False)
    analysis_date = Column(Date, nullable=False)
    status = Column(String(20), default="created")

    is_anomaly = Column(String(5), nullable=True)
    primary_driver = Column(String(200), nullable=True)
    confidence_score = Column(Numeric(6, 4), nullable=True)

    attribution_json = Column(JSON, nullable=True)
    anomaly_json = Column(JSON, nullable=True)
    risk_decomposition_json = Column(JSON, nullable=True)
    ranked_events_json = Column(JSON, nullable=True)
    generated_summary = Column(Text, nullable=True)
    guardrail_json = Column(JSON, nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
