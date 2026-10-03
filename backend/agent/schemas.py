"""Pydantic models for agent actions, state and API traffic."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

STATUSES = ("planning", "searching", "reading", "running", "analyzing",
            "waiting_for_approval", "applying", "verifying", "completed",
            "failed", "cancelled", "max_iterations")


class AgentAction(BaseModel):
    """One structured decision from the LLM. Raw LLM output is never trusted."""
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class ToolCallLog(BaseModel):
    iteration: int
    tool: str
    reason: str = ""
    ok: bool = True
    summary: str = ""
    detail: Dict[str, Any] = Field(default_factory=dict)


class ProposedChange(BaseModel):
    file_path: str
    original: str
    proposed: str
    diff: str
    reason: str = ""
    applied: bool = False
    backup_path: Optional[str] = None


class ExecutionResult(BaseModel):
    status: str = "success"
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    error_category: str = "NONE"
    error_explanation: str = ""


class AgentState(BaseModel):
    session_id: str
    task: str
    project_id: str = "local-project"
    project_path: str = ""
    current_file: Optional[str] = None
    language: Optional[str] = None
    selected_code: Optional[str] = None
    current_code: str = ""
    retrieved_context: List[Dict[str, Any]] = Field(default_factory=list)
    execution_output: Optional[ExecutionResult] = None
    proposed_changes: List[ProposedChange] = Field(default_factory=list)
    activity: List[ToolCallLog] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    status: str = "planning"
    summary: str = ""
    error: str = ""

    def pending_change(self) -> Optional[ProposedChange]:
        for change in reversed(self.proposed_changes):
            if not change.applied:
                return change
        return None


class AgentRunRequest(BaseModel):
    task: str
    project_path: str = ""
    project_id: str = "local-project"
    language: str = "python"
    current_file: Optional[str] = None
    current_code: str = ""
    selected_code: str = ""


class AgentSessionRequest(BaseModel):
    session_id: str


class AgentResponse(BaseModel):
    session_id: str
    status: str
    iteration: int
    summary: str = ""
    error: str = ""
    activity: List[ToolCallLog] = Field(default_factory=list)
    pending_change: Optional[ProposedChange] = None
    execution_output: Optional[ExecutionResult] = None
    sources: List[str] = Field(default_factory=list)


def to_response(state: AgentState) -> AgentResponse:
    sources = []
    for chunk in state.retrieved_context:
        if chunk.get("file") and chunk["file"] not in sources:
            sources.append(chunk["file"])
    return AgentResponse(session_id=state.session_id, status=state.status,
                         iteration=state.iteration, summary=state.summary,
                         error=state.error, activity=state.activity,
                         pending_change=state.pending_change(),
                         execution_output=state.execution_output, sources=sources)
