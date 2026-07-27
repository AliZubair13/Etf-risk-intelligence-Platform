import streamlit as st
import httpx

st.set_page_config(
    page_title="ETF Risk Intelligence",
    page_icon="📊",
    layout="wide",
)

st.title("📊 ETF Risk Attribution & Event Intelligence")
st.caption("Investigate why an ETF moved unusually on a given date.")

try:
    r = httpx.get("http://localhost:8000/health", timeout=2.0)
    if r.status_code == 200:
        st.success("Backend connected ✓")
    else:
        st.error(f"Backend returned {r.status_code}")
except Exception as e:
    st.warning(f"Backend not reachable: {e}")

st.markdown("---")
st.subheader("Coming soon")
st.markdown("""
- ETF selector and date picker
- Holding contribution chart
- Risk decomposition
- Event timeline
- Evidence-backed explanation
- Analyst review workspace
""")
