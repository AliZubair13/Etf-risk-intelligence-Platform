from sqlalchemy import Column, String, Date, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.connection import Base


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"

    id = Column(String(50), primary_key=True)  # etf|date|method
    etf_ticker = Column(String(10), nullable=False)
    analysis_date = Column(Date, nullable=False)
    method = Column(String(30), nullable=False)  # statistical | isolation_forest
    daily_return = Column(Numeric(10, 6), nullable=True)
    abnormal_return = Column(Numeric(10, 6), nullable=True)
    z_score = Column(Numeric(10, 4), nullable=True)
    is_anomaly = Column(Boolean, nullable=False)
    model_version = Column(String(20), default="v1")
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
