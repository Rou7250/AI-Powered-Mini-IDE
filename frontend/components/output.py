"""Output / terminal panel."""
import streamlit as st


def render():
    st.markdown("#### Output / terminal")
    result = st.session_state.run_result
    if not result:
        st.code("$ ready - press Run to execute your code", language="bash")
        return
    status = "success (exit 0)" if result["success"] else "failed (exit %s)" % result["exit_code"]
    c1, c2 = st.columns(2)
    c1.metric("Status", status)
    c2.metric("Execution time", "%.3fs" % result["execution_time"])
    if result.get("output"):
        st.code(result["output"], language="bash")
    if result.get("error"):
        st.error("```\n%s\n```" % result["error"].strip())
    if not result.get("output") and not result.get("error"):
        st.caption("(no output)")


def combined_output():
    """Text form of the last run, used as AI context."""
    result = st.session_state.run_result
    if not result:
        return ""
    return "\n".join(p for p in [result.get("output", ""), result.get("error", "")] if p.strip())
