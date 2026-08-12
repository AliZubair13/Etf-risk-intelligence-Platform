import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from api_client import run_investigation, list_etfs
from components.selector import render_selector
from components.summary_cards import render_summary_cards
from components.price_chart import render_price_chart
from components.contribution_chart import render_contribution_chart
from components.risk_decomposition import render_risk_decomposition
from components.event_timeline import render_event_timeline
from components.explanation import render_explanation
from components.feedback import render_feedback

st.set_page_config(
    page_title="ETF Risk Intelligence",
    page_icon="📊",
    layout="wide",
)

st.title("📊 ETF Risk Attribution & Event Intelligence")
st.caption(
    "Analyst-facing investigation platform — evidence-backed explanations for "
    "unusual ETF movements. Not investment advice."
)

# Backend health check
import httpx
try:
    r = httpx.get("http://localhost:8000/health", timeout=2.0)
    backend_ok = r.status_code == 200
except Exception:
    backend_ok = False

if not backend_ok:
    st.error("⚠️ Backend not reachable. Make sure uvicorn is running on port 8000.")
    st.stop()

# Component 1: Selector
etf, selected_date, run_clicked = render_selector()

# Session state to persist investigation across reruns
if "investigation" not in st.session_state:
    st.session_state.investigation = None

if run_clicked:
    with st.spinner(f"Running investigation for {etf} on {selected_date}..."):
        result, err = run_investigation(etf, selected_date.isoformat())
        if err:
            st.error(f"Investigation failed: {err}")
        else:
            st.session_state.investigation = result

investigation = st.session_state.investigation

if investigation:
    st.divider()

    # Component 2: Summary cards
    render_summary_cards(investigation)

    st.divider()
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Component 3: Price chart
        render_price_chart(etf, selected_date, investigation.get("is_anomaly", False))

        # Component 4: Contribution chart
        render_contribution_chart(investigation.get("attribution", {}))

    with col_right:
        # Component 5: Risk decomposition
        render_risk_decomposition(investigation.get("risk_decomposition", {}))

        # Component 6: Event timeline
        render_event_timeline(investigation.get("ranked_events", {}))

    st.divider()

    # Component 7: Explanation
    render_explanation(investigation)

    st.divider()

    # Component 8: Analyst feedback
    render_feedback(etf, selected_date.isoformat(), investigation.get("id", ""), investigation.get("ranked_events", {}).get("top_events", []))

else:
    st.info("👆 Select an ETF and date, then click **Run Investigation** to begin.")

    st.divider()
    st.subheader("💡 Try these known interesting dates")
    examples = [
        ("SMH", "2025-01-27", "DeepSeek shock — SMH dropped ~9.8%"),
        ("SMH", "2025-02-27", "Sector-wide semiconductor selloff — SMH dropped ~6.2%"),
        ("SMH", "2025-04-09", "Tariff pause rally — SMH jumped ~17.2%"),
    ]
    for tk, dt, desc in examples:
        st.caption(f"**{tk}** on **{dt}**: {desc}")
