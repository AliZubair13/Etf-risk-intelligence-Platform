import time
import logging
import requests
from datetime import datetime, date
from typing import Optional
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.config import settings
from app.models.filing import Filing

logger = logging.getLogger(__name__)

SEC_HEADERS = {"User-Agent": settings.sec_user_agent}
TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

_ticker_cik_cache = None


def get_ticker_cik_map() -> dict:
    global _ticker_cik_cache
    if _ticker_cik_cache is not None:
        return _ticker_cik_cache
    resp = requests.get(TICKER_CIK_URL, headers=SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    mapping = {}
    for entry in data.values():
        ticker = entry["ticker"].upper()
        cik = str(entry["cik_str"]).zfill(10)
        mapping[ticker] = cik
    _ticker_cik_cache = mapping
    logger.info(f"Loaded {len(mapping)} ticker-CIK mappings")
    return mapping


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    mapping = get_ticker_cik_map()
    ticker_clean = ticker.upper().replace("-", ".")
    return mapping.get(ticker.upper()) or mapping.get(ticker_clean)


def fetch_submissions(cik: str) -> dict:
    url = SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers=SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def clean_filing_text(html_content: str, max_length: int = 20000) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text[:max_length]


def fetch_filing_document(cik: str, accession_number: str, primary_doc: str) -> Optional[str]:
    acc_no_dashes = accession_number.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/{primary_doc}"
    try:
        resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
        resp.raise_for_status()
        return clean_filing_text(resp.text)
    except Exception as e:
        logger.warning(f"Failed to fetch document {url}: {e}")
        return None


def ingest_filings_for_ticker(ticker: str, db: Session, filing_types: list = None,
                               start_date: date = None, fetch_text: bool = True) -> int:
    if filing_types is None:
        filing_types = ["8-K", "10-Q", "10-K"]

    cik = get_cik_for_ticker(ticker)
    if not cik:
        logger.warning(f"No CIK found for {ticker}")
        return 0

    try:
        submissions = fetch_submissions(cik)
    except Exception as e:
        logger.error(f"Failed to fetch submissions for {ticker}: {e}")
        return 0

    company_name = submissions.get("name", "")
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    accepted_times = recent.get("acceptanceDateTime", [])
    items = recent.get("items", [])

    inserted = 0
    for i in range(len(forms)):
        form_type = forms[i]
        if form_type not in filing_types:
            continue

        f_date = datetime.strptime(filing_dates[i], "%Y-%m-%d").date()
        if start_date and f_date < start_date:
            continue

        accession = accession_numbers[i]
        filing_id = f"{cik}|{accession}"

        exists = db.query(Filing).filter(Filing.id == filing_id).first()
        if exists:
            continue

        primary_doc = primary_docs[i] if i < len(primary_docs) else None
        accepted = accepted_times[i] if i < len(accepted_times) else None
        item_codes = items[i] if i < len(items) else None

        cleaned_text = None
        if fetch_text and primary_doc:
            cleaned_text = fetch_filing_document(cik, accession, primary_doc)
            time.sleep(0.2)

        filing = Filing(
            id=filing_id,
            ticker=ticker.upper(),
            cik=cik,
            company_name=company_name,
            filing_type=form_type,
            filing_date=f_date,
            accepted_timestamp=datetime.fromisoformat(accepted) if accepted else None,
            accession_number=accession,
            document_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{primary_doc}" if primary_doc else None,
            primary_doc=primary_doc,
            item_codes=item_codes,
            cleaned_text=cleaned_text,
            text_length=str(len(cleaned_text)) if cleaned_text else None,
        )
        db.add(filing)
        inserted += 1

    db.commit()
    logger.info(f"{ticker}: inserted {inserted} filings")
    return inserted


def ingest_all_filings(db: Session, tickers: list, start_date: date = None):
    total = 0
    for i, ticker in enumerate(tickers):
        logger.info(f"Filings {i+1}/{len(tickers)}: {ticker}")
        count = ingest_filings_for_ticker(ticker, db, start_date=start_date, fetch_text=False)
        total += count
        time.sleep(0.3)
    logger.info(f"Total filings inserted: {total}")
    return total
