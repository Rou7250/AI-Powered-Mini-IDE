from fastapi import APIRouter, HTTPException

from backend.ai import assistant
from backend.ai.llm import LLMError
from backend.models.schemas import ActionRequest, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _guard(fn, *args):
    try:
        return fn(*args)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not (req.question or "").strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    return ChatResponse(**_guard(assistant.chat, req))


def _action_route(kind):
    def handler(req: ActionRequest):
        return ChatResponse(**_guard(assistant.run_action, kind, req))
    return handler


for _kind in ("explain", "debug", "fix", "optimize", "refactor", "tests"):
    router.add_api_route("/" + _kind, _action_route(_kind), methods=["POST"],
                         response_model=ChatResponse, name="ai_" + _kind)
