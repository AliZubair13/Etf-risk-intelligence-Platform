from sqlalchemy import Column, String, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class ETF(Base):
    __tablename__ = "etfs"

    ticker = Column(String(10), primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    benchmark_ticker = Column(String(10), nullable=True)
    issuer = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    holdings = relationship("ETFHolding", back_populates="etf")
