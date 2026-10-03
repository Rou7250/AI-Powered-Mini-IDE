"""Code editor panel.

Uses streamlit-ace (line numbers + syntax highlighting) when installed and falls
back to a plain text area otherwise.

LIMITATION: no Streamlit editor component reliably reports the user's text
selection back to Python. "Selected code" is therefore an explicit paste box the
user fills in; everything else works on the full current code.
"""
import os
import streamlit as st

try:
    from streamlit_ace import st_ace
    ACE = True
except ImportError:
    ACE = False

ACE_MODE = {
    "python": "python",
    "javascript": "javascript",
    "java": "java",
}

EXT_TO_ACE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sql": "sql",
    ".sh": "sh",
    ".bash": "sh",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".txt": "text",
    ".xml": "xml",
}

THEMES = [
    ("dracula", "VS Code (Dracula)"),
    ("tomorrow_night", "VS Code (Tomorrow Dark)"),
    ("nord_dark", "Nord Dark"),
    ("monokai", "Monokai Classic"),
    ("clouds_midnight", "Midnight Dark"),
]

DEFAULT_CODE = {
    "python": 'def divide(a, b):\n    return a / b\n\n\nprint(divide(10, 0))\n',
    "javascript": 'function divide(a, b) {\n  return a / b;\n}\n\nconsole.log(divide(10, 0));\n',
    "java": ('public class Main {\n    public static void main(String[] args) {\n'
             '        System.out.println(10 / 0);\n    }\n}\n'),
}


def _detect_ace_mode(filename, default_lang):
    if filename:
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in EXT_TO_ACE:
            return EXT_TO_ACE[ext]
        if filename.lower() in ("dockerfile", "dockerfile.dev"):
            return "dockerfile"
    return ACE_MODE.get(default_lang, "text")


def render(language):
    col_title, col_theme = st.columns([3.5, 1.5])
    col_title.markdown("#### Code editor - `%s`" % st.session_state.current_file)

    theme_keys = [t[0] for t in THEMES]
    current_idx = theme_keys.index(st.session_state.editor_theme) if st.session_state.editor_theme in theme_keys else 0
    selected_theme_label = col_theme.selectbox(
        "Theme",
        [t[1] for t in THEMES],
        index=current_idx,
        label_visibility="collapsed",
        key="theme_selector"
    )
    theme_key = THEMES[[t[1] for t in THEMES].index(selected_theme_label)][0]
    st.session_state.editor_theme = theme_key

    ace_mode = _detect_ace_mode(st.session_state.current_file, language)

    if ACE:
        code = st_ace(value=st.session_state.code, language=ace_mode,
                      theme=theme_key, font_size=14, tab_size=4, show_gutter=True,
                      wrap=False, auto_update=True, min_lines=32, key="ace_%s_%s_%s"
                      % (ace_mode, theme_key, st.session_state.editor_version))
    else:
        st.caption("Install `streamlit-ace` for line numbers and syntax highlighting.")
        code = st.text_area("code", value=st.session_state.code, height=580,
                            label_visibility="collapsed",
                            key="ta_%s" % st.session_state.editor_version)
    st.session_state.code = code or ""

    with st.expander("Ask about a specific snippet (paste selected code)"):
        st.session_state.selected_code = st.text_area(
            "Selected code", value=st.session_state.selected_code, height=110,
            label_visibility="collapsed",
            placeholder="Paste the lines you want the AI to focus on...")
    return st.session_state.code


def reset(language):
    st.session_state.code = DEFAULT_CODE.get(language, "")
    st.session_state.selected_code = ""
    st.session_state.editor_version += 1
