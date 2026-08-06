"""
Entity extraction: determine which securities a filing text mentions.
"""
import re
import logging
from sqlalchemy.orm import Session
from app.models.filing import Filing
from app.models.event_entity import EventEntity
from app.services.entity_dictionary import build_entity_dictionary

logger = logging.getLogger(__name__)

# Tickers that represent the SAME underlying company (dual share classes etc.)
# Used to prevent a company's own filing from "mentioning" its sibling ticker
SAME_COMPANY_GROUPS = [
    {"GOOG", "GOOGL"},
]


def same_company(ticker_a: str, ticker_b: str) -> bool:
    if ticker_a == ticker_b:
        return True
    for group in SAME_COMPANY_GROUPS:
        if ticker_a in group and ticker_b in group:
            return True
    return False


def extract_entities_from_text(text: str, entity_dict: dict, primary_ticker: str = None) -> list:
    if not text:
        return []

    text_lower = text.lower()
    matches = []
    seen_tickers = set()

    for ticker, names in entity_dict.items():
        for name in names:
            if len(name) < 3:
                continue
            pattern = r'\b' + re.escape(name) + r'\b'
            match = re.search(pattern, text_lower)

            if match and ticker not in seen_tickers:
                is_ticker_match = name == ticker.lower()
                method = "ticker_match" if is_ticker_match else "alias_match"
                confidence = 0.95 if is_ticker_match else 0.85

                matches.append({
                    "ticker": ticker,
                    "matched_text": match.group(),
                    "method": method,
                    "confidence": confidence,
                    "is_primary": same_company(ticker, primary_ticker) if primary_ticker else False,
                })
                seen_tickers.add(ticker)
                break

    return matches


def process_filing_entities(filing: Filing, entity_dict: dict, db: Session) -> int:
    existing = db.query(EventEntity).filter(
        EventEntity.filing_id == filing.id,
        EventEntity.matched_ticker == filing.ticker
    ).first()

    if not existing:
        primary_entity = EventEntity(
            filing_id=filing.id,
            matched_ticker=filing.ticker,
            extracted_text=filing.ticker,
            extraction_method="exact_match",
            confidence=1.0,
            is_primary="true",
        )
        db.add(primary_entity)

    inserted = 1 if not existing else 0

    if filing.cleaned_text:
        matches = extract_entities_from_text(filing.cleaned_text, entity_dict, filing.ticker)
        for m in matches:
            if same_company(m["ticker"], filing.ticker):
                continue  # skip self-mentions (including sibling share classes)

            exists = db.query(EventEntity).filter(
                EventEntity.filing_id == filing.id,
                EventEntity.matched_ticker == m["ticker"]
            ).first()
            if exists:
                continue

            entity = EventEntity(
                filing_id=filing.id,
                matched_ticker=m["ticker"],
                extracted_text=m["matched_text"],
                extraction_method=m["method"],
                confidence=m["confidence"],
                is_primary="false",
            )
            db.add(entity)
            inserted += 1

    return inserted


def process_all_filings(db: Session) -> int:
    entity_dict = build_entity_dictionary(db)
    logger.info(f"Built entity dictionary with {len(entity_dict)} tickers")

    filings = db.query(Filing).filter(Filing.processing_status == "processed").all()
    logger.info(f"Extracting entities from {len(filings)} filings")

    total = 0
    for i, f in enumerate(filings):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(filings)}")
        count = process_filing_entities(f, entity_dict, db)
        total += count
        if i % 100 == 0:
            db.commit()

    db.commit()
    logger.info(f"Total entities extracted: {total}")
    return total
