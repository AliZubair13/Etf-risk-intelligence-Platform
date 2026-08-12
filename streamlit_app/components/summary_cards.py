import streamlit as st


def render_summary_cards(investigation: dict):
    attribution = investigation.get("attribution", {})
    anomaly = investigation.get("anomaly", {}).get("statistical", {})
    confidence = investigation.get("confidence_score")

    col1, col2, col3, col4, col5 = st.columns(5)

    daily_return = attribution.get("etf_return_pct", 0)
    abnormal_return = anomaly.get("abnormal_return_pct", 0)
    volatility = anomaly.get("rolling_volatility", 0)
    z_score = anomaly.get("z_score", 0)

    with col1:
        st.metric("Daily Return", f"{daily_return:.2f}%",
                   delta=None, delta_color="inverse" if daily_return < 0 else "normal")

    with col2:
        st.metric("Abnormal Return", f"{abnormal_return:.2f}%",
                   help="Return relative to benchmark")

    with col3:
        st.metric("30-Day Volatility", f"{volatility*100:.2f}%" if volatility else "N/A")

    with col4:
        risk_level = "🔴 High" if abs(z_score) >= 3 else ("🟡 Medium" if abs(z_score) >= 2 else "🟢 Low")
        st.metric("Anomaly Score (z)", f"{z_score:.2f}" if z_score else "N/A")
        st.caption(risk_level)

    with col5:
        conf_pct = confidence * 100 if confidence else 0
        st.metric("Confidence", f"{conf_pct:.0f}%")

    is_anomaly = investigation.get("is_anomaly")
    status = investigation.get("status")
    if is_anomaly:
        st.warning(f"⚠️ Abnormal movement detected — Status: **{status}**")
    else:
        st.success(f"✅ Normal trading day — Status: **{status}**")
