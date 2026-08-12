import streamlit as st
from api_client import post


def render_feedback(etf: str, analysis_date: str, investigation_id: str, ranked_events: list = None):
    st.subheader("👤 Analyst Review")

    # Per-event feedback (if events exist)
    if ranked_events:
        st.write("**Rate individual events:**")
        for i, event in enumerate(ranked_events[:5]):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.caption(f"{event['ticker']} — {event['event_category']} ({event['filing_date']})")
            with col2:
                if st.button("✅ Relevant", key=f"rel_{i}_{investigation_id}"):
                    result, err = post("/api/feedback", {
                        "investigation_id": investigation_id,
                        "feedback_type": "event_relevant",
                        "event_id": event["filing_id"],
                    })
                    if err:
                        st.error(err)
                    else:
                        st.success("Saved")
            with col3:
                if st.button("❌ Irrelevant", key=f"irr_{i}_{investigation_id}"):
                    result, err = post("/api/feedback", {
                        "investigation_id": investigation_id,
                        "feedback_type": "event_irrelevant",
                        "event_id": event["filing_id"],
                    })
                    if err:
                        st.error(err)
                    else:
                        st.success("Saved")
            with col4:
                if st.button("🏷️ Wrong Cat.", key=f"cat_{i}_{investigation_id}"):
                    result, err = post("/api/feedback", {
                        "investigation_id": investigation_id,
                        "feedback_type": "category_corrected",
                        "event_id": event["filing_id"],
                        "original_value": event["event_category"],
                    })
                    if err:
                        st.error(err)
                    else:
                        st.success("Saved")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚫 Explanation Unsupported", use_container_width=True):
            result, err = post("/api/feedback", {
                "investigation_id": investigation_id,
                "feedback_type": "explanation_unsupported",
            })
            if err:
                st.error(err)
            else:
                st.warning("Flagged explanation as unsupported")

    with col2:
        if st.button("✔️ Explanation Supported", use_container_width=True):
            result, err = post("/api/feedback", {
                "investigation_id": investigation_id,
                "feedback_type": "explanation_supported",
            })
            if err:
                st.error(err)
            else:
                st.success("Confirmed explanation supported")

    st.divider()
    approve_col, comment_col = st.columns([1, 3])
    with approve_col:
        approved = st.button("✅ Approve Investigation", type="primary", use_container_width=True)
    with comment_col:
        comment = st.text_input("Analyst comment (optional)", key=f"comment_{investigation_id}")

    if approved:
        result, err = post("/api/feedback", {
            "investigation_id": investigation_id,
            "feedback_type": "investigation_approved",
            "comment": comment,
        })
        if err:
            st.error(err)
        else:
            st.success("Investigation approved and saved.")
