import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_risk_decomposition(risk: dict):
    st.subheader("⚖️ Risk Decomposition")

    if not risk or "decomposition" in risk and risk.get("error"):
        st.info("Risk decomposition not available.")
        return

    decomp = risk.get("decomposition", {})
    labels = ["Alpha", "Market", "Sector", "Company-Specific"]
    values = [
        decomp.get("alpha_contribution_pct", 0),
        decomp.get("market_contribution_pct", 0),
        decomp.get("sector_contribution_pct", 0),
        decomp.get("company_specific_pct", 0),
    ]

    # Waterfall chart
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(labels) + ["total"],
        x=labels + ["ETF Return"],
        y=values + [risk.get("etf_return_pct", 0)],
        text=[f"{v:.2f}%" for v in values] + [f"{risk.get('etf_return_pct', 0):.2f}%"],
        connector={"line": {"color": "rgba(150,150,150,0.5)"}},
        decreasing={"marker": {"color": "#E74C3C"}},
        increasing={"marker": {"color": "#2ECC71"}},
        totals={"marker": {"color": "#4A90D9"}},
    ))
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Regression details table
    reg = risk.get("regression", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Beta (Market)", f"{reg.get('beta_market', 0):.3f}")
    col2.metric("Beta (Sector)", f"{reg.get('beta_sector', 0):.3f}" if reg.get('beta_sector') is not None else "N/A")
    col3.metric("R²", f"{reg.get('r_squared', 0):.3f}")

    st.caption(f"Sector proxy: {risk.get('sector_ticker', 'N/A')} | "
               f"Regression window: {reg.get('window_start')} to {reg.get('window_end')} "
               f"({reg.get('observations_used')} obs)")

    if risk.get("interpretation"):
        st.info(f"💡 {risk['interpretation']}")
