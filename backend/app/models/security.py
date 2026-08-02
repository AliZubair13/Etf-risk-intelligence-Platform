from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Security(Base):
    __tablename__ = "securities"

    id = Column(String(10), primary_key=True)  # ticker as ID
    ticker = Column(String(10), nullable=False, unique=True)
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(200), nullable=True)
    cik = Column(String(20), nullable=True)
    exchange = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    holdings = relationship("ETFHolding", back_populates="security")
