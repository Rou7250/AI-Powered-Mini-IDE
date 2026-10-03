"""Controlled tool registry. The LLM can only name tools on this allowlist."""
from typing import Any, Dict

from backend import config
from backend.agent import patch
from backend.agent.schemas import AgentState, ExecutionResult, ProposedChange
from backend.execution import errors
from backend.execution.languages import SUPPORTED
from backend.execution.runner import run_code as _run_code
from backend.logging_config import get_logger
from backend.rag import indexer, retriever
from backend.security import SecurityError, check_file_size, is_probably_binary, truncate_output

log = get_logger("agent.tools")

ALLOWED_TOOLS = {
    "search_project", "read_project_file", "write_project_file", "run_code",
    "get_execution_output", "generate_fix", "apply_patch", "undo_change",
    "run_again", "finish",
}

TOOL_SPEC = """\
search_project(query: str, top_k: int = 5)
    Semantic search over the indexed project. Returns file, lines, score and content.
read_project_file(file_path: str, start_line: int = null, end_line: int = null)
    Read a file inside the project root.
run_code(file_path: str = null, language: str = null)
    Execute the given project file (or the current editor code if file_path is null)
    inside the execution sandbox. Returns stdout, stderr, exit code and error category.
get_execution_output()
    Return the most recent execution result without running anything again.
write_project_file(file_path: str, content: str, reason: str)
    Propose replacing a file's full content. This does NOT write - it creates a diff
    and pauses for user approval.
generate_fix(file_path: str, content: str, reason: str)
    Alias of write_project_file, for proposing a corrected version of a file.
apply_patch()
    Only valid after the user approved a proposed change.
undo_change()
    Restore the most recently applied change from its backup.
run_again(file_path: str = null, language: str = null)
    Re-run code after a fix, to verify it.
finish(summary: str)
    End the task. Summarise what you did and whether verification succeeded.
"""


class ToolError(Exception):
    pass


def _require(args: Dict[str, Any], name: str) -> Any:
    value = args.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ToolError("Missing required argument: %s" % name)
    return value


def _language_for(state: AgentState, args: Dict[str, Any], file_path: str = None) -> str:
    language = args.get("language") or (
        indexer.language_of(file_path) if file_path else None) or state.language or "python"
    if language not in SUPPORTED:
        raise ToolError("Unsupported language: %s (supported: %s)"
                        % (language, ", ".join(SUPPORTED)))
    return language


def _read(state: AgentState, file_path: str) -> str:
    if not state.project_path:
        raise ToolError("No project folder is open, so project files cannot be read.")
    from backend.security import safe_project_path
    full = safe_project_path(state.project_path, file_path)
    import os
    if not os.path.isfile(full):
        raise ToolError("File not found in project: %s" % file_path)
    if is_probably_binary(full):
        raise ToolError("Refusing to read a binary file: %s" % file_path)
    check_file_size(full)
    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def _execute_and_record(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    file_path = args.get("file_path")
    if file_path:
        code = _read(state, file_path)
        state.current_file = file_path
    else:
        code = state.current_code
    if not (code or "").strip():
        raise ToolError("There is no code to run.")
    language = _language_for(state, args, file_path)
    raw = _run_code(language, code)
    category = errors.classify(raw)
    result = ExecutionResult(status="success" if raw["success"] else "error",
                             stdout=truncate_output(raw.get("output", "")),
                             stderr=truncate_output(raw.get("error", "")),
                             exit_code=raw.get("exit_code", 1),
                             execution_time=raw.get("execution_time", 0.0),
                             error_category=category,
                             error_explanation=errors.explain(category))
    state.execution_output = result
    return result.model_dump()


def _propose(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    file_path = _require(args, "file_path")
    content = _require(args, "content")
    original = _read(state, file_path)
    patch.validate(original, content)
    change = ProposedChange(file_path=file_path, original=original, proposed=content,
                            diff=patch.make_diff(file_path, original, content),
                            reason=args.get("reason", ""))
    state.proposed_changes.append(change)
    state.status = "waiting_for_approval"
    return {"file_path": file_path, "diff": change.diff,
            "note": "Waiting for user approval. Nothing has been written yet."}


def _search(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    query = _require(args, "query")
    top_k = min(int(args.get("top_k") or config.RAG_TOP_K), 10)
    results = retriever.search(query, state.project_id, top_k)
    state.retrieved_context = results
    if not results:
        return {"results": [], "note": "Nothing retrieved. The project may not be indexed."}
    return {"results": [{k: r[k] for k in
                         ("file", "language", "score", "start_line", "end_line", "content")
                         if k in r} for r in results]}


def _read_tool(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    file_path = _require(args, "file_path")
    text = _read(state, file_path)
    lines = text.splitlines()
    start = max(1, int(args.get("start_line") or 1))
    end = min(len(lines), int(args.get("end_line") or len(lines)))
    state.current_file = file_path
    return {"file_path": file_path, "start_line": start, "end_line": end,
            "content": "\n".join(lines[start - 1:end])}


def _apply(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    change = state.pending_change()
    if change is None:
        raise ToolError("There is no pending change to apply.")
    backup = patch.apply_change(state.project_path, change.file_path, change.proposed)
    change.applied = True
    change.backup_path = backup
    state.current_code = change.proposed
    state.status = "verifying"
    return {"file_path": change.file_path, "applied": True}


def _undo(state: AgentState, args: Dict[str, Any]) -> Dict[str, Any]:
    for change in reversed(state.proposed_changes):
        if change.applied and change.backup_path:
            patch.undo_change(state.project_path, change.file_path, change.backup_path)
            change.applied = False
            return {"file_path": change.file_path, "restored": True}
    raise ToolError("There is no applied change to undo.")


HANDLERS = {
    "search_project": _search,
    "read_project_file": _read_tool,
    "write_project_file": _propose,
    "generate_fix": _propose,
    "run_code": _execute_and_record,
    "run_again": _execute_and_record,
    "get_execution_output": lambda state, args: (
        state.execution_output.model_dump() if state.execution_output
        else {"note": "Nothing has been executed yet."}),
    "apply_patch": _apply,
    "undo_change": _undo,
}

STATUS_BY_TOOL = {"search_project": "searching", "read_project_file": "reading",
                  "run_code": "running", "run_again": "verifying",
                  "get_execution_output": "analyzing", "write_project_file": "analyzing",
                  "generate_fix": "analyzing", "apply_patch": "applying",
                  "undo_change": "applying"}


def validate_action(tool: str, arguments: Dict[str, Any]) -> None:
    if tool not in ALLOWED_TOOLS:
        raise ToolError("Unknown or forbidden tool: %s" % tool)
    if not isinstance(arguments, dict):
        raise ToolError("Tool arguments must be an object.")


def execute(state: AgentState, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Validate then run a tool. Raises ToolError for anything not allowed."""
    validate_action(tool, arguments)
    if tool == "finish":
        raise ToolError("finish is handled by the agent loop, not the tool registry.")
    handler = HANDLERS[tool]
    from backend.logging_config import safe_args
    log.info("tool=%s session=%s args=%s", tool, state.session_id, safe_args(arguments))
    try:
        return handler(state, arguments)
    except (SecurityError, FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc))
