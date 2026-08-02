from sqlalchemy import Column, String, Date, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class ETFHolding(Base):
    __tablename__ = "etf_holdings"

    id = Column(String(50), primary_key=True)  # etf_ticker|security_ticker|date
    etf_ticker = Column(String(10), ForeignKey("etfs.ticker"), nullable=False)
    security_ticker = Column(String(10), ForeignKey("securities.ticker"), nullable=False)
    weight = Column(Numeric(10, 6), nullable=False)
    effective_date = Column(Date, nullable=False)
    covered_weight = Column(Numeric(10, 6), nullable=True)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    etf = relationship("ETF", back_populates="holdings")
    security = relationship("Security", back_populates="holdings")
