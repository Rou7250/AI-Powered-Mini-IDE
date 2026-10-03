"""Project explorer: open a folder, browse files, index it for RAG."""
import os
import streamlit as st
from services import api_client


def render():
    st.markdown("### Project")
    path = st.text_input("Project folder path", value=st.session_state.project_path,
                         placeholder="/home/you/my-project")

    c1, c2 = st.columns(2)
    if c1.button("Open project", use_container_width=True):
        if not path or not path.strip():
            st.warning("Please provide a valid project folder path.")
        else:
            try:
                data = api_client.list_files(path.strip())
                st.session_state.project_path = data["root"]
                st.session_state.project_files = data["files"]
                st.session_state.project_indexed = False
                st.success("Found %d file(s)." % len(data["files"]))
            except api_client.APIError as exc:
                st.error(str(exc))

    if c2.button("Index project", use_container_width=True,
                 disabled=not st.session_state.project_files):
        full = st.session_state.force_reindex
        with st.spinner("Scanning, chunking, embedding and storing in ChromaDB..."):
            try:
                res = api_client.index_project(st.session_state.project_path,
                                               st.session_state.project_id, reindex=full)
                st.session_state.project_indexed = res.get("total_chunks", 0) > 0
                st.success("%d files scanned - %d new chunks, %d files unchanged "
                           "(skipped), %d re-indexed. Total chunks: %d."
                           % (res["files_indexed"], res["chunks_indexed"],
                              res.get("files_skipped", 0), res.get("files_updated", 0),
                              res.get("total_chunks", 0)))
            except api_client.APIError as exc:
                st.error(str(exc))

    st.session_state.force_reindex = st.checkbox(
        "Full re-index (wipe and rebuild)", value=st.session_state.force_reindex,
        help="Leave off for incremental indexing: unchanged files are skipped.")

    if st.session_state.project_files:
        st.caption("Indexed for RAG" if st.session_state.project_indexed else "Not indexed yet")

        root_name = os.path.basename(st.session_state.project_path.rstrip("/\\")) or "Project"
        st.markdown(
            f"""<div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #8b949e; margin-top: 6px; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span style="color: #58a6ff; font-size: 13px;">◧</span>
            <span>WORKSPACE</span>
            <span style="color: #484f58;">›</span>
            <span style="color: #e6edf3;">{root_name}</span>
            </div>""",
            unsafe_allow_html=True
        )

        st.markdown("""
        <style>
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #0d1117 !important;
            border: 1px solid #30363d !important;
            border-radius: 6px !important;
            padding: 6px 4px !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
            gap: 1px !important;
        }
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

        tree = _build_tree(st.session_state.project_files)
        with st.container(height=400, border=True):
            _render_tree_node(tree)


def _file_icon(fname):
    lower = fname.lower()
    if lower.endswith(".py"):
        return "🐍"
    elif lower.endswith((".js", ".jsx", ".ts", ".tsx")):
        return "📜"
    elif lower.endswith(".java"):
        return "☕"
    elif lower.endswith((".md", ".markdown")):
        return "📖"
    elif lower.endswith((".json", ".toml")):
        return "📋"
    elif lower.endswith((".yml", ".yaml")) or "docker" in lower:
        return "🐳"
    elif lower.startswith(".env") or lower in (".gitignore", ".gitattributes"):
        return "⚙️"
    elif lower.endswith((".html", ".css")):
        return "🌐"
    elif lower.endswith((".sh", ".bash", ".ps1", ".bat")):
        return "⚡"
    return "📄"


def _build_tree(paths):
    tree = {}
    for p in paths:
        norm = p.replace("\\", "/")
        parts = norm.split("/")
        curr = tree
        for part in parts[:-1]:
            curr = curr.setdefault(part, {})
        curr[parts[-1]] = norm
    return tree


def _get_guide_prefix(is_last_stack):
    if not is_last_stack:
        return ""
    if len(is_last_stack) == 1:
        return "  " + ("└─ " if is_last_stack[0] else "├─ ")
    res = "  "
    for is_last in is_last_stack[:-1]:
        res += "   " if is_last else "│  "
    res += "└─ " if is_last_stack[-1] else "├─ "
    return res


def _render_tree_node(node, prefix="", depth=0, is_last_stack=None):
    if is_last_stack is None:
        is_last_stack = []

    folders = []
    files = []
    for k, v in node.items():
        if isinstance(v, dict):
            folders.append((k, v))
        else:
            files.append((k, v))

    folders.sort(key=lambda x: x[0].lower())
    files.sort(key=lambda x: x[0].lower())

    total = len(folders) + len(files)
    idx = 0

    for folder_name, subnode in folders:
        is_last = (idx == total - 1)
        folder_path = f"{prefix}/{folder_name}".lstrip("/")
        is_expanded = folder_path in st.session_state.expanded_folders
        chevron = "▾" if is_expanded else "▸"
        safe_path = folder_path.replace("/", "_").replace(".", "_")

        if depth == 0:
            # Main / Top-level folder: clean chevron, no tree branch lines, distinct styling
            btn_label = f"{chevron} {folder_name}/"
            btn_key = f"vsc_rootfld_{safe_path}"
            next_stack = []
        else:
            # Subfolder: connected with tree guide branch lines
            guide = _get_guide_prefix(is_last_stack + [is_last])
            btn_label = f"{guide}{chevron} {folder_name}/"
            btn_key = f"vsc_subfld_{safe_path}"
            next_stack = is_last_stack + [is_last]

        if st.button(btn_label, key=btn_key, use_container_width=True):
            if is_expanded:
                st.session_state.expanded_folders.discard(folder_path)
            else:
                st.session_state.expanded_folders.add(folder_path)
            st.rerun()

        if is_expanded:
            _render_tree_node(subnode, prefix=folder_path, depth=depth + 1, is_last_stack=next_stack)
        idx += 1

    for file_name, full_path in files:
        is_last = (idx == total - 1)
        icon = _file_icon(file_name)
        is_active = (st.session_state.current_file == full_path)
        active_mark = "● " if is_active else ""
        safe_path = full_path.replace("/", "_").replace("\\", "_").replace(".", "_")

        if depth == 0:
            guide = ""
        else:
            guide = _get_guide_prefix(is_last_stack + [is_last])

        btn_label = f"{guide}{active_mark}{icon} {file_name}"
        btn_key = ("vsc_active_" if is_active else "vsc_fl_") + safe_path

        if st.button(btn_label, key=btn_key, use_container_width=True):
            _open_file(full_path)
        idx += 1


def _open_file(filepath):
    try:
        content = api_client.read_file(st.session_state.project_path, filepath)["content"]
        st.session_state.code = content
        st.session_state.current_file = filepath
        st.session_state.editor_version += 1
        st.rerun()
    except api_client.APIError as exc:
        st.error(str(exc))

