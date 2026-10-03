"""The controlled agent loop: plan -> validate -> run one tool -> repeat, with limits."""
import json
import re
import uuid
from typing import Dict, Optional

from pydantic import ValidationError

from backend import config
from backend.agent import prompts, tools
from backend.agent.schemas import AgentAction, AgentState, ToolCallLog
from backend.ai import llm
from backend.logging_config import get_logger

log = get_logger("agent")

SESSIONS: Dict[str, AgentState] = {}
_JSON = re.compile(r"\{.*\}", re.S)


class AgentError(Exception):
    pass


def get_session(session_id: str) -> AgentState:
    state = SESSIONS.get(session_id)
    if state is None:
        raise KeyError("Unknown agent session: %s" % session_id)
    return state


def _parse_action(text: str) -> AgentAction:
    """Parse and validate raw LLM output. Never trust it directly."""
    raw = (text or "").strip()
    raw = re.sub(r"^```[a-zA-Z]*\n|```$", "", raw).strip()
    match = _JSON.search(raw)
    if not match:
        raise ValueError("no JSON object found")
    data = json.loads(match.group(0))
    action = AgentAction(**data)
    tools.validate_action(action.tool, action.arguments)
    return action


def _next_action(state: AgentState) -> AgentAction:
    user = prompts.build_user_prompt(state)
    text = llm.complete(prompts.SYSTEM, user, temperature=0.0)
    try:
        return _parse_action(text)
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError, tools.ToolError) as exc:
        log.warning("invalid agent action (%s); retrying once", exc)
        text = llm.complete(prompts.SYSTEM, user + "\n\n" + prompts.RETRY, temperature=0.0)
        try:
            return _parse_action(text)
        except Exception as exc2:
            raise AgentError("The model did not return a valid tool call: %s" % exc2)


def _summarise(result: dict) -> str:
    try:
        return json.dumps(result)[:1200]
    except (TypeError, ValueError):
        return str(result)[:1200]


VERIFICATION_BUDGET = 3


def _loop(state: AgentState) -> AgentState:
    max_iterations = state.max_iterations
    while state.iteration < max_iterations:
        state.iteration += 1
        state.status = "planning"
        try:
            action = _next_action(state)
        except AgentError as exc:
            state.status = "failed"
            state.error = str(exc)
            return state

        if action.tool == "finish":
            state.summary = str(action.arguments.get("summary") or action.reason
                                or "Task finished.")
            state.status = "completed"
            return state

        state.status = tools.STATUS_BY_TOOL.get(action.tool, "analyzing")
        try:
            result = tools.execute(state, action.tool, action.arguments)
            state.activity.append(ToolCallLog(iteration=state.iteration, tool=action.tool,
                                              reason=action.reason, ok=True,
                                              summary=_summarise(result), detail={}))
        except tools.ToolError as exc:
            state.activity.append(ToolCallLog(iteration=state.iteration, tool=action.tool,
                                              reason=action.reason, ok=False,
                                              summary="Tool error: %s" % exc))
            continue

        if state.status == "waiting_for_approval":
            state.summary = "A change is proposed and waiting for your approval."
            return state

    state.status = "max_iterations"
    state.summary = ("Agent stopped because the maximum of %d iterations was reached."
                     % max_iterations)
    return state


def start(task: str, project_path: str = "", project_id: str = "local-project",
          language: str = "python", current_file: Optional[str] = None,
          current_code: str = "", selected_code: str = "") -> AgentState:
    if not llm.is_configured():
        raise AgentError("Agent mode needs a real LLM. Set LLM_API_KEY in your .env - "
                         "the agent will not pretend to run tools in mock mode.")
    if not (task or "").strip():
        raise AgentError("Task must not be empty.")
    state = AgentState(session_id=str(uuid.uuid4()), task=task.strip(),
                       project_id=project_id, project_path=project_path,
                       language=language, current_file=current_file,
                       current_code=current_code, selected_code=selected_code,
                       max_iterations=config.MAX_AGENT_ITERATIONS)
    SESSIONS[state.session_id] = state
    log.info("agent start session=%s task=%s", state.session_id, task[:120])
    return _loop(state)


def approve(session_id: str) -> AgentState:
    """User approved the pending diff: apply it, then let the agent verify."""
    state = get_session(session_id)
    if state.pending_change() is None:
        raise AgentError("There is no change waiting for approval.")
    # applying a change opens a small extra budget so the agent can verify and report
    state.max_iterations = state.iteration + VERIFICATION_BUDGET
    state.status = "applying"
    try:
        tools.execute(state, "apply_patch", {})
    except tools.ToolError as exc:
        state.status = "failed"
        state.error = str(exc)
        return state
    state.activity.append(ToolCallLog(iteration=state.iteration, tool="apply_patch",
                                      reason="User approved the change.", ok=True,
                                      summary="Change applied with a backup."))
    return _loop(state)


def reject(session_id: str) -> AgentState:
    state = get_session(session_id)
    change = state.pending_change()
    if change is None:
        raise AgentError("There is no change waiting for approval.")
    state.proposed_changes.remove(change)
    state.status = "cancelled"
    state.summary = "You rejected the proposed change. Nothing was written."
    state.activity.append(ToolCallLog(iteration=state.iteration, tool="reject",
                                      reason="User rejected the change.", ok=True,
                                      summary="No files were modified."))
    return state


def undo(session_id: str) -> AgentState:
    state = get_session(session_id)
    try:
        result = tools.execute(state, "undo_change", {})
    except tools.ToolError as exc:
        raise AgentError(str(exc))
    state.status = "completed"
    state.summary = "Restored %s from its backup." % result["file_path"]
    state.activity.append(ToolCallLog(iteration=state.iteration, tool="undo_change",
                                      reason="User requested undo.", ok=True,
                                      summary=_summarise(result)))
    return state


def cancel(session_id: str) -> AgentState:
    state = get_session(session_id)
    if state.status not in ("completed", "failed"):
        state.status = "cancelled"
        state.summary = "Agent stopped by the user. No unapproved change was written."
    return state
