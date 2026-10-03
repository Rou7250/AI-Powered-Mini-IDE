"""Orchestrates routing, retrieval, prompting and response parsing."""
import difflib
import re

from backend import config
from backend.ai import llm, prompts
from backend.ai.context_router import (CURRENT_CODE, ERROR, GENERAL, PROJECT_RAG,
                                       determine_context)

_FENCE = re.compile(r"```[a-zA-Z0-9+#]*\n(.*?)```", re.S)


def extract_code(answer):
    """Return the largest fenced code block from the answer, or ''."""
    blocks = _FENCE.findall(answer or "")
    if not blocks:
        return ""
    return max(blocks, key=len).strip()


def mentioned_files(answer, candidates):
    return [f for f in candidates if f.split("/")[-1] in (answer or "")]


def chat(req):
    """req: ChatRequest-like object. Returns dict for ChatResponse."""
    mode = determine_context(req.question, req.current_code, req.project_indexed,
                             req.execution_output, force_rag=req.use_rag)

    sources, source_lines = [], []
    system = prompts.BASE_SYSTEM

    if mode == PROJECT_RAG:
        from backend.rag import retriever
        results = retriever.search(req.question, req.project_id, config.RAG_TOP_K)
        sources = retriever.sources_of(results)
        source_lines = ["%s lines %s-%s" % (r["file"], r.get("start_line", "?"),
                                            r.get("end_line", "?")) for r in results]
        system = prompts.RAG_SYSTEM
        user = prompts.rag(req.question, retriever.build_context(results), req.language,
                           req.current_code, req.execution_output, req.current_file)
    elif mode == ERROR:
        user = prompts.error_context(req.question, req.language, req.current_code,
                                     req.execution_output, req.current_file)
    elif mode == CURRENT_CODE:
        user = prompts.current_code(req.question, req.language, req.current_code,
                                    req.current_file, req.selected_code)
    else:
        mode = GENERAL
        user = prompts.general(req.question)

    answer = llm.complete(system, user)
    return {"answer": answer, "suggested_code": extract_code(answer),
            "sources": sources, "source_lines": source_lines, "context_mode": mode}


def make_diff(original, proposed, filename="current"):
    """Unified diff between the editor code and an AI suggestion."""
    if not original.strip() or not proposed.strip() or original == proposed:
        return ""
    return "".join(difflib.unified_diff(original.splitlines(keepends=True),
                                        proposed.splitlines(keepends=True),
                                        fromfile="a/" + filename, tofile="b/" + filename))


def run_action(kind, req):
    """kind in explain/debug/fix/optimize/refactor/tests. req: ActionRequest-like."""
    code = (req.code or "").strip()
    if not code:
        return {"answer": "There is no code in the editor to work on.",
                "suggested_code": "", "diff": "", "sources": [], "source_lines": [],
                "context_mode": "GENERAL"}

    sources, source_lines = [], []
    instruction = req.instruction
    if getattr(req, "use_project_context", False):
        from backend.rag import retriever
        query = "%s %s" % (kind, (req.execution_output or code)[:400])
        results = retriever.search(query, req.project_id, config.RAG_TOP_K)
        if results:
            sources = retriever.sources_of(results)
            source_lines = ["%s lines %s-%s" % (r["file"], r.get("start_line", "?"),
                                                r.get("end_line", "?")) for r in results]
            instruction = (instruction + "\n\nRelevant project context:\n"
                           + retriever.build_context(results, max_chars=6000)).strip()

    user = prompts.action(kind, req.language, code, req.execution_output,
                          req.current_file, instruction)
    answer = llm.complete(prompts.BASE_SYSTEM, user)
    suggested = extract_code(answer) if kind != "explain" else ""
    return {"answer": answer, "suggested_code": suggested,
            "diff": make_diff(code, suggested, req.current_file or "current"),
            "sources": sources, "source_lines": source_lines,
            "context_mode": "ERROR" if req.execution_output.strip() else "CURRENT_CODE"}
