import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_contribution_chart(attribution: dict):
    st.subheader("📊 Holding Contribution")

    all_contribs = attribution.get("all_contributions", [])
    if not all_contribs:
        st.info("No contribution data available.")
        return

    df = pd.DataFrame(all_contribs)
    df = df.sort_values("contribution_pct")

    colors = ["#E74C3C" if v < 0 else "#2ECC71" for v in df["contribution_pct"]]

    fig = go.Figure(go.Bar(
        x=df["contribution_pct"],
        y=df["ticker"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}%" for v in df["contribution_pct"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Contribution to ETF Return (%)",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Explained Return", f"{attribution.get('explained_return_pct', 0):.2f}%")
    col2.metric("Residual Return", f"{attribution.get('residual_return_pct', 0):.2f}%")
    col3.metric("Reconciliation Error", f"{attribution.get('reconciliation_error_bps', 0):.1f} bps")

    if attribution.get("flags"):
        for flag in attribution["flags"]:
            st.caption(f"⚠️ {flag}")
