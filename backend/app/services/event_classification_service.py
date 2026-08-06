"""
Event classification for SEC filings.
Maps 8-K Item codes to our event taxonomy deterministically.
This is NOT machine learning - item codes are self-reported by the
filer and are a reliable structured signal, so we use rule-based mapping.

Event categories (from product_requirements.md):
    earnings, guidance, regulation, product, merger_acquisition,
    leadership, legal, supply_chain, macroeconomic, geopolitical,
    analyst_action, other
"""
import hashlib

# SEC 8-K Item code -> our category
# Reference: https://www.sec.gov/files/form8-k.pdf
ITEM_CODE_MAP = {
    "1.01": "merger_acquisition",   # Entry into material agreement
    "1.02": "merger_acquisition",   # Termination of material agreement
    "1.03": "legal",                # Bankruptcy
    "2.01": "merger_acquisition",   # Completion of acquisition/disposition
    "2.02": "earnings",             # Results of operations (earnings)
    "2.03": "other",                # Creation of financial obligation
    "2.04": "other",                # Triggering events
    "2.05": "other",                # Costs associated with exit/disposal
    "2.06": "other",                # Material impairments
    "3.01": "regulation",           # Delisting/failure to satisfy listing rules
    "3.02": "other",                # Unregistered sales of securities
    "3.03": "other",                # Material modification to shareholder rights
    "4.01": "other",                # Changes in accountant
    "4.02": "other",                # Non-reliance on prior financials
    "5.01": "leadership",           # Changes in control
    "5.02": "leadership",           # Officer/director departure or election
    "5.03": "other",                # Amendments to articles/bylaws
    "5.04": "other",                # Trust suspension
    "5.05": "other",                # Code of ethics amendment
    "5.06": "other",                # Change in shell status
    "5.07": "other",                # Shareholder vote results
    "5.08": "leadership",           # Shareholder director nominations
    "6.01": "product",              # ABS informational/computational material
    "6.02": "product",              # Change of servicer/trustee
    "6.03": "product",              # Change in credit enhancement
    "6.04": "product",              # Failure to make distribution
    "6.05": "product",              # Securities Act updating disclosure
    "7.01": "guidance",             # Regulation FD disclosure
    "8.01": "other",                # Other events (catch-all)
    "9.01": "other",                # Financial statements and exhibits
}


def classify_event(item_codes: str) -> str:
    """
    Classify a filing's event category based on its 8-K item codes.
    If multiple items, prioritize the most "important" signal:
    earnings > merger_acquisition > leadership > legal > regulation > others.
    """
    if not item_codes:
        return "other"

    codes = [c.strip() for c in item_codes.split(",")]
    categories = [ITEM_CODE_MAP.get(c, "other") for c in codes]

    priority = [
        "earnings", "merger_acquisition", "leadership", "legal",
        "regulation", "guidance", "product", "supply_chain",
        "macroeconomic", "geopolitical", "analyst_action", "other",
    ]

    for p in priority:
        if p in categories:
            return p
    return "other"


def compute_content_hash(ticker: str, filing_date, item_codes: str, text: str = None) -> str:
    """
    Compute a dedup fingerprint.
    Uses ticker + date + item_codes as primary signal (SEC filings are
    already deduplicated by accession_number, but this helps catch
    conceptual duplicates like an 8-K + its exhibit).
    """
    text_sample = (text or "")[:500]
    raw = f"{ticker}|{filing_date}|{item_codes}|{text_sample}"
    return hashlib.sha256(raw.encode()).hexdigest()
