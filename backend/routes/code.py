from fastapi import APIRouter, HTTPException

from backend.execution.languages import SUPPORTED
from backend.execution.runner import run_code
from backend.models.schemas import RunRequest, RunResponse

router = APIRouter(prefix="/api/code", tags=["code"])


@router.get("/languages")
def languages():
    return {"languages": SUPPORTED}


@router.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    try:
        return RunResponse(**run_code(req.language, req.code, req.timeout))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
