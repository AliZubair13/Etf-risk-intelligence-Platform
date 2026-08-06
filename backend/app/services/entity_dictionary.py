"""
Ticker/company name dictionary for entity matching.
"""
from sqlalchemy.orm import Session
from app.models.security import Security

MANUAL_ALIASES = {
    "NVDA": ["Nvidia", "NVIDIA Corporation"],
    "AMD": ["Advanced Micro Devices", "AMD Inc"],
    "GOOGL": ["Google", "Alphabet", "Alphabet Inc"],
    "GOOG": ["Google", "Alphabet", "Alphabet Inc"],
    "META": ["Facebook", "Meta Platforms"],
    "BRK-B": ["Berkshire Hathaway", "Berkshire"],
    "TSM": ["Taiwan Semiconductor", "TSMC"],
    "AVGO": ["Broadcom", "Broadcom Inc"],
}

# Tickers that are also common English words - require stricter matching
# (only match the full company name or exact-case ticker, never lowercase alias)
AMBIGUOUS_TICKERS = {"COST", "ON", "ALL", "NOW", "SO", "KEY", "LOW", "WELL", "FAST", "REAL", "TWO", "ONE"}


def build_entity_dictionary(db: Session) -> dict:
    securities = db.query(Security).all()
    dictionary = {}

    for sec in securities:
        ticker = sec.ticker.upper()
        names = set()

        if ticker not in AMBIGUOUS_TICKERS:
            names.add(ticker.lower())

        if sec.company_name:
            clean_name = sec.company_name.lower()
            for suffix in [" inc", " inc.", " corp", " corporation", " corp.", " co", " co.", " ltd", " plc"]:
                clean_name = clean_name.replace(suffix, "")
            clean_name = clean_name.strip()
            if len(clean_name) >= 4:  # avoid short ambiguous fragments
                names.add(clean_name)
            names.add(sec.company_name.lower())

        for alias in MANUAL_ALIASES.get(ticker, []):
            names.add(alias.lower())

        dictionary[ticker] = list(names)

    return dictionary
