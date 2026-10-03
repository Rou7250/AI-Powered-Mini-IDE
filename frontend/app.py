"""AI-powered mini IDE - a lightweight IDE with project-aware RAG."""
# Reload trigger
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from components import agent_panel, chat, editor, output, sidebar  # noqa: E402
from services import api_client  # noqa: E402

st.set_page_config(page_title="AI-powered mini IDE", page_icon="</>", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
section[data-testid="stSidebar"] { background-color: #161a23; }
code, pre { font-family: 'JetBrains Mono', 'Fira Code', monospace !important; }

/* File tree styling in sidebar - strictly scoped to file tree keys */
section[data-testid="stSidebar"] div[class*="st-key-vsc_"] button {
    text-align: left !important;
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 3px !important;
    padding: 0px 6px !important;
    margin: 0 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    line-height: 24px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    width: 100% !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_"] button p {
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace !important;
    font-size: 12px !important;
    line-height: 24px !important;
    white-space: pre !important;
    text-align: left !important;
    margin: 0 !important;
    padding: 0 !important;
    color: #c9d1d9 !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_"] button:hover {
    background-color: rgba(255, 255, 255, 0.08) !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_"] button:hover p {
    color: #58a6ff !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_rootfld_"] button {
    background-color: rgba(56, 139, 253, 0.07) !important;
    border-left: 2px solid #58a6ff !important;
    margin-top: 2px !important;
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_rootfld_"] button p {
    font-weight: 700 !important;
    color: #79c0ff !important;
    letter-spacing: 0.3px !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_subfld_"] button p {
    font-weight: 600 !important;
    color: #e6edf3 !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_active_"] button {
    background-color: rgba(56, 139, 253, 0.22) !important;
    border-left: 2px solid #3fb950 !important;
}
section[data-testid="stSidebar"] div[class*="st-key-vsc_active_"] button p {
    color: #58a6ff !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

DEFAULTS = {
    "code": editor.DEFAULT_CODE["python"],
    "language": "python",
    "current_file": "main.py",
    "selected_code": "",
    "messages": [],
    "run_result": None,
    "pending_code": "",
    "pending_diff": "",
    "project_path": PROJECT_ROOT,
    "project_files": [],
    "project_id": "local-project",
    "project_indexed": False,
    "use_rag": False,
    "editor_version": 0,
    "mode": "Assistant",
    "force_reindex": False,
    "agent_session": None,
    "agent_result": None,
    "show_ai_panel": True,
    "editor_theme": "dracula",
    "expanded_folders": {"backend"},
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

language = sidebar.render()

head_left, head_toggle, head_right = st.columns([5, 1.8, 1.2])
head_left.markdown("### AI-powered mini IDE  -  Project-aware RAG & AI Agent")

panel_btn_text = "▶ Fold AI Panel" if st.session_state.show_ai_panel else "◀ Open AI Panel"
if head_toggle.button(panel_btn_text, use_container_width=True):
    st.session_state.show_ai_panel = not st.session_state.show_ai_panel
    st.rerun()

if head_right.button("Run code", type="primary", use_container_width=True):
    with st.spinner("Executing code..."):
        try:
            st.session_state.run_result = api_client.run_code(language, st.session_state.code)
        except api_client.APIError as exc:
            st.session_state.run_result = {"success": False, "output": "", "error": str(exc),
                                           "execution_time": 0.0, "exit_code": 1}

if st.session_state.show_ai_panel:
    left, right = st.columns([5, 3])
    with left:
        editor.render(language)
    with right:
        if st.session_state.mode == "Agent":
            st.markdown("#### AI agent")
            agent_panel.render()
        else:
            chat.render()
else:
    editor.render(language)

st.divider()
output.render()
