from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.etfs import router as etfs_router

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


@app.get("/")
def root():
    return {"name": "ETF Risk Intelligence Platform", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
