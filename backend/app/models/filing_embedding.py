from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database.connection import Base


class FilingEmbedding(Base):
    __tablename__ = "filing_embeddings"

    filing_id = Column(String(50), primary_key=True)
    embedding = Column(JSON, nullable=False)  # list of 384 floats
    model_name = Column(String(50), default="all-MiniLM-L6-v2")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
