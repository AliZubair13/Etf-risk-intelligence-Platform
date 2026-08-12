from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.relevance_model_service import train_relevance_model

router = APIRouter(prefix="/api/model", tags=["Model Training"])


@router.post("/train-relevance")
def train_model(db: Session = Depends(get_db)):
    """Stage 2: train the event-relevance model from accumulated analyst feedback."""
    return train_relevance_model(db)
