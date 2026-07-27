from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="ETF Risk Attribution & Event Intelligence Platform",
    description="Analyst-facing platform that investigates why an ETF moved unusually on a given date.",
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "ETF Risk Intelligence Platform",
        "version": "0.1.0",
        "env": settings.app_env,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
