from fastapi import APIRouter, HTTPException

from backend.agent import agent
from backend.agent.schemas import (AgentResponse, AgentRunRequest, AgentSessionRequest,
                                   to_response)
from backend.ai.llm import LLMError

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _guard(fn, *args):
    try:
        return to_response(fn(*args))
    except agent.AgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/run", response_model=AgentResponse)
def run(req: AgentRunRequest):
    return _guard(agent.start, req.task, req.project_path, req.project_id, req.language,
                  req.current_file, req.current_code, req.selected_code)


@router.post("/approve", response_model=AgentResponse)
def approve(req: AgentSessionRequest):
    return _guard(agent.approve, req.session_id)


@router.post("/reject", response_model=AgentResponse)
def reject(req: AgentSessionRequest):
    return _guard(agent.reject, req.session_id)


@router.post("/undo", response_model=AgentResponse)
def undo(req: AgentSessionRequest):
    return _guard(agent.undo, req.session_id)


@router.post("/cancel", response_model=AgentResponse)
def cancel(req: AgentSessionRequest):
    return _guard(agent.cancel, req.session_id)


@router.get("/status/{session_id}", response_model=AgentResponse)
def status(session_id: str):
    return _guard(agent.get_session, session_id)
