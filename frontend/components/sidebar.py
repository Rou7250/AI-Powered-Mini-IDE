"""Sidebar: project controls, language selector, AI actions."""
import streamlit as st

from components import editor, output, project
from services import api_client

LANGUAGES = ["python", "javascript", "java"]
ACTIONS = [("Explain", "explain"), ("Find bug", "debug"), ("Fix error", "fix"),
           ("Optimize", "optimize"), ("Refactor", "refactor"), ("Generate tests", "tests")]


def render():
    with st.sidebar:
        st.title("AI-powered mini IDE")
        health = api_client.health()
        if health:
            st.caption("Backend online — LLM: %s"
                       % ("on" if health.get("llm_configured") else "mock"))
        else:
            st.error("Backend offline. Start it with:\n`uvicorn backend.main:app --reload`")

        st.session_state.mode = st.radio(
            "Mode", ["Assistant", "Agent"],
            index=0 if st.session_state.mode == "Assistant" else 1,
            horizontal=True,
            help="Assistant answers questions. Agent searches, reads, runs code and "
                 "proposes patches you approve.")

        project.render()
        st.divider()

        language = st.selectbox("Language", LANGUAGES,
                                index=LANGUAGES.index(st.session_state.language))
        if language != st.session_state.language:
            st.session_state.language = language
            editor.reset(language)
            st.rerun()

        if st.button("Reset editor", use_container_width=True):
            editor.reset(language)
            st.rerun()

        st.divider()
        st.markdown("### AI actions")
        for label, kind in ACTIONS:
            if st.button(label, use_container_width=True, key="act_" + kind):
                _run_action(kind, label)

        st.divider()
        st.session_state.use_rag = st.checkbox(
            "Force project RAG for every question", value=st.session_state.use_rag,
            disabled=not st.session_state.project_indexed)
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    return st.session_state.language


def _run_action(kind, label):
    st.session_state.show_ai_panel = True
    code = st.session_state.selected_code.strip() or st.session_state.code
    with st.spinner("%s..." % label):
        try:
            res = api_client.action(kind, code, st.session_state.language,
                                    output.combined_output(), st.session_state.current_file,
                                    use_project_context=st.session_state.project_indexed,
                                    project_id=st.session_state.project_id)
        except api_client.APIError as exc:
            st.error(str(exc))
            return
    st.session_state.messages.append({"role": "user", "content": "[Action] %s" % label})
    st.session_state.messages.append({"role": "assistant", "content": res["answer"],
                                      "sources": res.get("sources", []),
                                      "source_lines": res.get("source_lines", []),
                                      "mode": res.get("context_mode", "")})
    if res.get("suggested_code"):
        st.session_state.pending_code = res["suggested_code"]
        st.session_state.pending_diff = res.get("diff", "")
    st.rerun()
