import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from api_client import get_price_history


def render_price_chart(etf: str, selected_date, is_anomaly: bool):
    st.subheader("📈 Price History")

    start = (selected_date - timedelta(days=180)).isoformat()
    end = (selected_date + timedelta(days=30)).isoformat()

    data, err = get_price_history(etf, start, end)
    if err or not data:
        st.info("No price history available for this range.")
        return

    df = pd.DataFrame(data["prices"])
    df["date"] = pd.to_datetime(df["date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["adjusted_close"],
        mode="lines", name=etf, line=dict(color="#4A90D9", width=2),
    ))

    # Mark the selected date
    target_row = df[df["date"] == pd.Timestamp(selected_date)]
    if not target_row.empty:
        marker_color = "red" if is_anomaly else "orange"
        fig.add_trace(go.Scatter(
            x=target_row["date"], y=target_row["adjusted_close"],
            mode="markers", name="Selected date",
            marker=dict(size=14, color=marker_color, symbol="star"),
        ))

    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        xaxis_title=None,
        yaxis_title="Adjusted Close ($)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
