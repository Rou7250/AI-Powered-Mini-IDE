"""AI assistant chat panel plus the review/apply flow for suggested code."""
import streamlit as st

from components import output
from services import api_client

MODE_LABEL = {"GENERAL": "general knowledge", "CURRENT_CODE": "current code",
              "ERROR": "current code + error", "PROJECT_RAG": "project RAG"}


def render():
    st.markdown("#### AI assistant")
    _render_pending_code()

    box = st.container(height=380)
    with box:
        if not st.session_state.messages:
            st.caption("Ask about your code, an error, or the whole indexed project.")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("mode"):
                    st.caption("context: " + MODE_LABEL.get(msg["mode"], msg["mode"]))
                if msg.get("sources"):
                    st.caption("sources: " + ", ".join(msg["sources"]))
                if msg.get("source_lines"):
                    for line in msg["source_lines"]:
                        st.caption(line)

    question = st.chat_input("Ask the AI about your code or project...")
    if question:
        _ask(question)


def _ask(question):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Thinking..."):
        try:
            res = api_client.chat(
                question=question, language=st.session_state.language,
                current_file=st.session_state.current_file,
                current_code=st.session_state.code,
                selected_code=st.session_state.selected_code,
                execution_output=output.combined_output(),
                use_rag=st.session_state.use_rag,
                project_id=st.session_state.project_id,
                project_indexed=st.session_state.project_indexed)
        except api_client.APIError as exc:
            st.session_state.messages.append({"role": "assistant",
                                              "content": "Request failed: %s" % exc})
            st.rerun()
            return
    st.session_state.messages.append({"role": "assistant", "content": res["answer"],
                                      "sources": res.get("sources", []),
                                      "source_lines": res.get("source_lines", []),
                                      "mode": res.get("context_mode", "")})
    if res.get("suggested_code"):
        st.session_state.pending_code = res["suggested_code"]
    st.rerun()


def _render_pending_code():
    pending = st.session_state.pending_code
    if not pending:
        return
    with st.expander("AI suggested changes - review before applying", expanded=True):
        diff = st.session_state.get("pending_diff", "")
        if diff:
            tab_diff, tab_full = st.tabs(["Diff", "Full code"])
            tab_diff.code(diff, language="diff")
            tab_full.code(pending, language=st.session_state.language)
        else:
            st.code(pending, language=st.session_state.language)
        c1, c2 = st.columns(2)
        if c1.button("Apply changes", type="primary", use_container_width=True):
            st.session_state.code = pending
            st.session_state.pending_code = ""
            st.session_state.pending_diff = ""
            st.session_state.editor_version += 1
            st.rerun()
        if c2.button("Reject", use_container_width=True):
            st.session_state.pending_code = ""
            st.session_state.pending_diff = ""
            st.rerun()
