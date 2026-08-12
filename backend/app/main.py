from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.etfs import router as etfs_router
from app.api.investigations import router as investigations_router
from app.api.anomaly import router as anomaly_router
from app.api.risk import router as risk_router
from app.api.filings import router as filings_router
from app.api.macro import router as macro_router
from app.api.entities import router as entities_router
from app.api.event_ranking import router as event_ranking_router
from app.api.investigation_orchestration import router as orchestration_router
from app.api.feedback import router as feedback_router
from app.api.model_training import router as model_training_router

from app.scheduler import start_scheduler

app = FastAPI(title="ETF Risk Attribution & Event Intelligence Platform", version="0.1.0")

@app.on_event("startup")
def startup_event():
    start_scheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(etfs_router)
app.include_router(investigations_router)
app.include_router(anomaly_router)
app.include_router(risk_router)
app.include_router(filings_router)
app.include_router(macro_router)
app.include_router(entities_router)
app.include_router(event_ranking_router)
app.include_router(orchestration_router)
app.include_router(feedback_router)
app.include_router(model_training_router)

@app.get("/")
def root():
    return {"name": "ETF Risk Intelligence Platform", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
