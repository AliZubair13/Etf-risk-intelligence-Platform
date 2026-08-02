from sqlalchemy import Column, String, Date, Numeric, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database.connection import Base


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id = Column(String(50), primary_key=True)  # ticker|date
    ticker = Column(String(10), nullable=False)
    trade_date = Column(Date, nullable=False)
    open = Column(Numeric(12, 4), nullable=True)
    high = Column(Numeric(12, 4), nullable=True)
    low = Column(Numeric(12, 4), nullable=True)
    close = Column(Numeric(12, 4), nullable=True)
    adjusted_close = Column(Numeric(12, 4), nullable=False)
    volume = Column(Numeric(20, 0), nullable=True)
    daily_return = Column(Numeric(10, 6), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_ticker_date"),
    )
