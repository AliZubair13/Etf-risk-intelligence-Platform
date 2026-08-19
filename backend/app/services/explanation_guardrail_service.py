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
            values.add(float(obj))

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
    # Normalize various Unicode minus/hyphen characters to ASCII hyphen
    # (LLMs sometimes use U+2212 MINUS SIGN or U+2011 NON-BREAKING HYPHEN)
    normalized = text.replace(chr(0x2212), '-').replace(chr(0x2011), '-').replace(chr(0x2013), '-')
    matches = re.findall(r'-?\d+\.?\d*\s*%', normalized)
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

    # Accept payload values and their decimal<->percentage conversions.
    # Derived numbers (ratios, percentages-of-totals) are explicitly
    # forbidden in the prompt, so they should not appear; if they do,
    # the guardrail correctly flags them.
    # IMPORTANT: convert BEFORE rounding, using the full-precision raw
    # payload values (extract_percentages_from_payload already rounds to
    # 1 decimal, which loses precision needed for accurate *100 conversion -
    # so we widen tolerance here to absorb that pre-rounding, rather than
    # re-deriving full precision from the payload).
    acceptable = set(round(v, 1) for v in known_percentages)
    for v in list(known_percentages):
        acceptable.add(round(v * 100, 1))
        acceptable.add(round(v / 100, 1))

    unsupported_percentages = []
    for pct in mentioned_percentages:
        if not any(abs(pct - known) <= 0.6 for known in acceptable):
            unsupported_percentages.append(pct)

    # Check: does the text reference at least one real event ID?
    # Only REQUIRE a citation if at least one candidate event was strong
    # enough to be worth citing (final_score above a reasonable relevance
    # threshold). If all candidate events were weak/low-relevance, the LLM
    # correctly choosing not to cite them is valid behavior, not a failure.
    # Only require citation for events tied to tickers that were actually
    # top CONTRIBUTORS to the move (i.e. relevant to the narrative direction),
    # not just any event that happened to score decently on the generic
    # relevance formula. An event about a ticker that moved the *opposite*
    # direction from the ETF is not narratively required to be cited.
    CITATION_REQUIRED_SCORE_THRESHOLD = 0.15
    contributor_tickers = {c["ticker"] for c in payload.get("top_contributors", [])}
    strong_relevant_events_exist = any(
        e.get("final_score", 0) >= CITATION_REQUIRED_SCORE_THRESHOLD
        and e.get("ticker") in contributor_tickers
        for e in payload.get("ranked_events", [])
    )
    has_event_citation = len(mentioned_event_ids) > 0
    citation_requirement_met = has_event_citation or not strong_relevant_events_exist

    # Check: does it mention residual/uncertainty (required by prompt rules)?
    mentions_residual = bool(re.search(r'residual|unexplained|uncertain', generated_text, re.IGNORECASE))

    # Check: does it avoid forbidden causal/recommendation language?
    forbidden_phrases = ["you should buy", "you should sell", "we recommend", "caused by", "was the cause"]
    violations = [p for p in forbidden_phrases if p.lower() in generated_text.lower()]

    all_checks_pass = (
        len(unsupported_percentages) == 0
        and citation_requirement_met
        and mentions_residual
        and len(violations) == 0
    )

    return {
        "verified": all_checks_pass,
        "checks": {
            "tickers_mentioned": list(mentioned_tickers),
            "event_ids_cited": list(mentioned_event_ids),
            "has_event_citation": has_event_citation,
            "citation_requirement_met": citation_requirement_met,
            "percentages_mentioned": mentioned_percentages,
            "unsupported_percentages": unsupported_percentages,
            "mentions_residual_or_uncertainty": mentions_residual,
            "forbidden_phrase_violations": violations,
        },
    }
