"""
Macroeconomic data ingestion from FRED.

FIX: realtime_start does NOT reliably represent the original publication date
for historical observations - it reflects the vintage query window, which
defaults to "today" for most recent-vintage requests.

Correct approach: FRED release dates are tied to a release_id (e.g., CPI's
release_id is 10). We fetch the release dates separately and match them to
observations by proximity (each observation's actual release is the release
event that happens shortly after month-end for that period).
"""
import logging
import requests
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.macro_observation import MacroObservation

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"

# series_id -> (name, importance, release_id)
# release_id found via https://api.stlouisfed.org/fred/series/release?series_id=X
SERIES = {
    "CPIAUCSL": {"name": "CPI (All Urban Consumers)", "importance": "high", "release_id": 10},
    "UNRATE": {"name": "Unemployment Rate", "importance": "high", "release_id": 50},
    "PAYEMS": {"name": "Nonfarm Payroll", "importance": "high", "release_id": 50},
    "FEDFUNDS": {"name": "Federal Funds Rate", "importance": "high", "release_id": 18},
    "DGS2": {"name": "2-Year Treasury Yield", "importance": "medium", "release_id": None},
    "DGS10": {"name": "10-Year Treasury Yield", "importance": "medium", "release_id": None},
    "PPIACO": {"name": "Producer Price Index", "importance": "medium", "release_id": 46},
}


def fetch_series_observations(series_id: str, start_date: str = "2022-01-01") -> list:
    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("observations", [])


def fetch_release_dates(release_id: int) -> list:
    """
    Fetch actual publication dates for a release_id.
    Returns list of {"date": "YYYY-MM-DD"} sorted chronologically.
    """
    url = f"{FRED_BASE}/release/dates"
    params = {
        "release_id": release_id,
        "api_key": settings.fred_api_key,
        "file_type": "json",
        "include_release_dates_with_no_data": "false",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        dates = [d["date"] for d in data.get("release_dates", [])]
        return sorted(dates)
    except Exception as e:
        logger.warning(f"Could not fetch release dates for release_id {release_id}: {e}")
        return []


def match_release_date(obs_date: date, release_dates: list) -> Optional[date]:
    """
    Find the release date that corresponds to this observation.
    Logic: the release happens AFTER the observation period ends.
    We pick the earliest release date that is >= obs_date and within
    ~60 days (covers monthly data published with a lag).
    """
    if not release_dates:
        return None

    obs_date_str = obs_date.isoformat()
    candidates = [d for d in release_dates if d >= obs_date_str]
    if not candidates:
        return None

    best = min(candidates)
    best_date = datetime.strptime(best, "%Y-%m-%d").date()

    # Sanity check: release should be within 90 days of observation period
    if (best_date - obs_date).days > 90:
        return None

    return best_date


def ingest_series(series_id: str, db: Session, start_date: str = "2022-01-01") -> int:
    series_info = SERIES.get(series_id, {"name": series_id, "importance": "medium", "release_id": None})

    try:
        observations = fetch_series_observations(series_id, start_date)
    except Exception as e:
        logger.error(f"Failed to fetch {series_id}: {e}")
        return 0

    if not observations:
        logger.warning(f"No observations for {series_id}")
        return 0

    observations = [o for o in observations if o["value"] != "."]
    observations.sort(key=lambda o: o["date"])

    # Fetch release calendar once for this series
    release_id = series_info.get("release_id")
    release_dates = fetch_release_dates(release_id) if release_id else []

    inserted = 0
    previous_value = None

    for obs in observations:
        obs_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()
        value = float(obs["value"])

        # Match actual release date, or fall back to obs_date + typical lag
        release_date = match_release_date(obs_date, release_dates)
        if release_date is None:
            # Fallback: assume ~15 day publication lag (reasonable default for monthly macro data)
            release_date = obs_date + timedelta(days=15) if release_id else obs_date

        obs_id = f"{series_id}|{obs_date}"
        exists = db.query(MacroObservation).filter(MacroObservation.id == obs_id).first()
        if exists:
            previous_value = value
            continue

        change = None
        change_pct = None
        if previous_value is not None and previous_value != 0:
            change = value - previous_value
            change_pct = (change / abs(previous_value)) * 100

        record = MacroObservation(
            id=obs_id,
            series_code=series_id,
            series_name=series_info["name"],
            observation_date=obs_date,
            release_date=release_date,
            value=value,
            previous_value=previous_value,
            change=round(change, 4) if change is not None else None,
            change_pct=round(change_pct, 4) if change_pct is not None else None,
            importance=series_info["importance"],
        )
        db.add(record)
        inserted += 1
        previous_value = value

    db.commit()
    logger.info(f"{series_id}: inserted {inserted} observations")
    return inserted


def ingest_all_macro_series(db: Session, start_date: str = "2022-01-01") -> int:
    total = 0
    for series_id in SERIES.keys():
        logger.info(f"Ingesting {series_id}...")
        count = ingest_series(series_id, db, start_date)
        total += count
    logger.info(f"Total macro observations inserted: {total}")
    return total
