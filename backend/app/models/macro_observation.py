from sqlalchemy import Column, String, Date, Numeric, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database.connection import Base


class MacroObservation(Base):
    __tablename__ = "macro_observations"

    id = Column(String(60), primary_key=True)  # series_code|observation_date
    series_code = Column(String(20), nullable=False)  # e.g. CPIAUCSL, UNRATE
    series_name = Column(String(200), nullable=False)
    observation_date = Column(Date, nullable=False)  # the period the data describes
    release_date = Column(Date, nullable=True)  # when it became public (used for attribution)
    value = Column(Numeric(15, 4), nullable=True)
    previous_value = Column(Numeric(15, 4), nullable=True)
    change = Column(Numeric(15, 4), nullable=True)
    change_pct = Column(Numeric(10, 4), nullable=True)
    importance = Column(String(10), nullable=True)  # high, medium, low
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("series_code", "observation_date", name="uq_series_obs_date"),
    )
