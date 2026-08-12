import streamlit as st


def render_event_timeline(ranked_events: dict):
    st.subheader("📰 Ranked Events (Evidence)")

    top_events = ranked_events.get("top_events", [])
    context = ranked_events.get("investigation_context", "")

    st.caption(f"Investigation context: *{context}*")

    if not top_events:
        st.info("No candidate events found near this date.")
        return

    for i, event in enumerate(top_events, 1):
        with st.expander(
            f"**#{i}** {event['ticker']} — {event['event_category'].replace('_', ' ').title()} "
            f"({event['filing_date']}) — Score: {event['final_score']:.3f}",
            expanded=(i == 1),
        ):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Filing type:** {event['filing_type']}")
                st.write(f"**Sentiment:** {event['sentiment_label']}")
                if event.get("document_url"):
                    st.markdown(f"[📄 View source filing]({event['document_url']})")

            with col2:
                breakdown = event["score_breakdown"]
                st.write("**Score breakdown:**")
                for k, v in breakdown.items():
                    st.caption(f"{k.replace('_', ' ').title()}: {v:.3f}")
