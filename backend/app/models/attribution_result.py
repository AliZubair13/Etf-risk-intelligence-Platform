from sqlalchemy import Column, String, Date, Numeric, DateTime, JSON
from sqlalchemy.sql import func
from app.database.connection import Base


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id = Column(String(50), primary_key=True)  # etf|date
    etf_ticker = Column(String(10), nullable=False)
    analysis_date = Column(Date, nullable=False)
    etf_return = Column(Numeric(10, 6), nullable=True)
    explained_return = Column(Numeric(10, 6), nullable=True)
    residual_return = Column(Numeric(10, 6), nullable=True)
    reconciliation_error_bps = Column(Numeric(10, 4), nullable=True)
    attribution_coverage = Column(Numeric(10, 4), nullable=True)
    market_contribution = Column(Numeric(10, 6), nullable=True)
    sector_contribution = Column(Numeric(10, 6), nullable=True)
    company_specific_contribution = Column(Numeric(10, 6), nullable=True)
    top_contributors_json = Column(JSON, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
