from sqlalchemy import Column, String, Date, DateTime, Text, UniqueConstraint, Numeric
from sqlalchemy.sql import func
from app.database.connection import Base


class Filing(Base):
    __tablename__ = "filings"

    id = Column(String(50), primary_key=True)
    ticker = Column(String(10), nullable=False)
    cik = Column(String(20), nullable=False)
    company_name = Column(String(200), nullable=True)
    filing_type = Column(String(10), nullable=False)
    filing_date = Column(Date, nullable=False)
    accepted_timestamp = Column(DateTime(timezone=True), nullable=True)
    accession_number = Column(String(30), nullable=False)
    document_url = Column(String(500), nullable=True)
    primary_doc = Column(String(200), nullable=True)
    item_codes = Column(String(200), nullable=True)
    cleaned_text = Column(Text, nullable=True)
    text_length = Column(String(20), nullable=True)

    # Phase 9 additions
    event_category = Column(String(30), nullable=True)  # earnings, guidance, regulation, etc.
    sentiment_label = Column(String(10), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Numeric(6, 4), nullable=True)  # -1 to 1
    content_hash = Column(String(64), nullable=True)  # for dedup
    embedding_generated = Column(String(5), default="false")  # "true"/"false" flag
    processing_status = Column(String(20), default="pending")  # pending, processed, failed

    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cik", "accession_number", name="uq_cik_accession"),
    )
