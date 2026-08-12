"""
Centralized API client for the Streamlit dashboard.
All calls go to the FastAPI backend built in Phases 1-15.
"""
import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


def get(path: str, params: dict = None):
    try:
        r = httpx.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", f"Error {r.status_code}")
    except Exception as e:
        return None, str(e)


def post(path: str, json_body: dict):
    try:
        r = httpx.post(f"{BASE_URL}{path}", json=json_body, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", f"Error {r.status_code}")
    except Exception as e:
        return None, str(e)


def list_etfs():
    return get("/api/etfs/")


def get_price_history(ticker: str, start: str, end: str):
    return get(f"/api/etfs/{ticker}/prices", {"start": start, "end": end})


def run_investigation(etf: str, analysis_date: str):
    return post("/api/investigations", {"etf": etf, "analysis_date": analysis_date})


def get_investigation(etf: str, analysis_date: str):
    return get(f"/api/investigations/{etf}/{analysis_date}/full")


def scan_anomalies(etf: str, start: str, end: str):
    return get(f"/api/anomaly/{etf}/scan", {"start": start, "end": end})
