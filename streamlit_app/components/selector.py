import streamlit as st
from datetime import date, timedelta

ETF_OPTIONS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "SMH": "VanEck Semiconductor ETF",
}


def render_selector():
    st.subheader("🔍 Select Investigation")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        etf = st.selectbox(
            "ETF",
            options=list(ETF_OPTIONS.keys()),
            format_func=lambda x: f"{x} — {ETF_OPTIONS[x]}",
        )

    with col2:
        selected_date = st.date_input(
            "Analysis date",
            value=date(2025, 1, 27),
            min_value=date(2022, 2, 1),
            max_value=date.today(),
        )

    with col3:
        st.write("")
        st.write("")
        run_clicked = st.button("🚀 Run Investigation", type="primary", use_container_width=True)

    return etf, selected_date, run_clicked
