import streamlit as st


def render_explanation(investigation: dict):
    st.subheader("🧾 Evidence-Backed Explanation")

    summary = investigation.get("generated_summary")
    guardrail = investigation.get("guardrail")

    if not summary:
        st.info("No explanation generated for this investigation.")
        return

    st.markdown(summary)

    st.divider()
    st.write("**Guardrail verification:**")

    if guardrail:
        if guardrail.get("verified"):
            st.success("✅ All claims verified against supplied evidence")
        else:
            st.error("⚠️ Some claims could not be verified")

        checks = guardrail.get("checks", {})
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Tickers mentioned: {', '.join(checks.get('tickers_mentioned', []))}")
            st.caption(f"Event citations: {len(checks.get('event_ids_cited', []))}")
        with col2:
            unsupported = checks.get("unsupported_percentages", [])
            if unsupported:
                st.caption(f"⚠️ Unsupported percentages: {unsupported}")
            else:
                st.caption("✅ No unsupported percentages")
            violations = checks.get("forbidden_phrase_violations", [])
            if violations:
                st.caption(f"⚠️ Forbidden phrases: {violations}")
            else:
                st.caption("✅ No forbidden phrases detected")

    st.caption(
        "⚠️ This is a system confidence score reflecting evidence quality, "
        "not a statistical probability of causal correctness. "
        "This tool does not provide investment advice."
    )
