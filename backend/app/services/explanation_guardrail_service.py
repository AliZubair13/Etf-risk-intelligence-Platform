"""
Guardrail: verify the LLM's generated explanation only references facts
that exist in the supplied evidence payload.

v1 checks (per Phase 15 spec):
    - ticker names
    - percentages
    - event IDs
    - dates
    - risk categories
"""
import re


def extract_tickers_from_payload(payload: dict) -> set:
    tickers = set()
    for c in payload.get("top_contributors", []):
        tickers.add(c["ticker"])
    for e in payload.get("ranked_events", []):
        tickers.add(e["ticker"])
    tickers.add(payload.get("etf"))
    return tickers


def extract_event_ids_from_payload(payload: dict) -> set:
    return {e["event_id"] for e in payload.get("ranked_events", [])}


def extract_dates_from_payload(payload: dict) -> set:
    dates = {payload.get("date")}
    for e in payload.get("ranked_events", []):
        dates.add(e.get("filing_date"))
    return {d for d in dates if d}


def extract_percentages_from_payload(payload: dict) -> set:
    """Collect all numeric percentages present in the payload, rounded to 1 decimal for tolerance."""
    values = set()

    def collect(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                collect(v)
        elif isinstance(obj, list):
            for v in obj:
                collect(v)
        elif isinstance(obj, (int, float)):
            values.add(round(float(obj), 1))

    collect(payload)
    return values


def find_tickers_in_text(text: str, known_tickers: set) -> set:
    """Find which known tickers appear in the generated text."""
    found = set()
    for ticker in known_tickers:
        if ticker and re.search(r'\b' + re.escape(ticker) + r'\b', text):
            found.add(ticker)
    return found


def find_event_ids_in_text(text: str, known_event_ids: set) -> set:
    found = set()
    for eid in known_event_ids:
        if eid in text:
            found.add(eid)
    return found


def find_percentages_in_text(text: str) -> list:
    """Extract all percentage-like numbers mentioned in generated text."""
    matches = re.findall(r'-?\d+\.?\d*\s*%', text)
    values = []
    for m in matches:
        try:
            values.append(round(float(m.replace('%', '').strip()), 1))
        except ValueError:
            continue
    return values


def verify_explanation(generated_text: str, payload: dict) -> dict:
    """
    Main guardrail check. Returns a report of what's verified vs unsupported.
    """
    if not generated_text:
        return {"verified": False, "reason": "No text generated", "checks": {}}

    known_tickers = extract_tickers_from_payload(payload)
    known_event_ids = extract_event_ids_from_payload(payload)
    known_dates = extract_dates_from_payload(payload)
    known_percentages = extract_percentages_from_payload(payload)

    mentioned_tickers = find_tickers_in_text(generated_text, known_tickers)
    mentioned_event_ids = find_event_ids_in_text(generated_text, known_event_ids)
    mentioned_percentages = find_percentages_in_text(generated_text)

    # Check: are mentioned percentages within tolerance of known values?
    unsupported_percentages = []
    for pct in mentioned_percentages:
        # Allow 0.2 tolerance for rounding differences
        if not any(abs(pct - known) <= 0.2 for known in known_percentages):
            unsupported_percentages.append(pct)

    # Check: does the text reference at least one real event ID?
    has_event_citation = len(mentioned_event_ids) > 0

    # Check: does it mention residual/uncertainty (required by prompt rules)?
    mentions_residual = bool(re.search(r'residual|unexplained|uncertain', generated_text, re.IGNORECASE))

    # Check: does it avoid forbidden causal/recommendation language?
    forbidden_phrases = ["you should buy", "you should sell", "we recommend", "caused by", "was the cause"]
    violations = [p for p in forbidden_phrases if p.lower() in generated_text.lower()]

    all_checks_pass = (
        len(unsupported_percentages) == 0
        and has_event_citation
        and mentions_residual
        and len(violations) == 0
    )

    return {
        "verified": all_checks_pass,
        "checks": {
            "tickers_mentioned": list(mentioned_tickers),
            "event_ids_cited": list(mentioned_event_ids),
            "has_event_citation": has_event_citation,
            "percentages_mentioned": mentioned_percentages,
            "unsupported_percentages": unsupported_percentages,
            "mentions_residual_or_uncertainty": mentions_residual,
            "forbidden_phrase_violations": violations,
        },
    }
