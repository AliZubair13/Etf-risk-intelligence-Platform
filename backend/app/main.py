from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.etfs import router as etfs_router
from app.api.investigations import router as investigations_router
from app.api.anomaly import router as anomaly_router

app = FastAPI(
    title="ETF Risk Attribution & Event Intelligence Platform",
    version="0.1.0",
)

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


@app.get("/")
def root():
    return {"name": "ETF Risk Intelligence Platform", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
