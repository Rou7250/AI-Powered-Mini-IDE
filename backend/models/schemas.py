from typing import List, Optional
from pydantic import BaseModel


class RunRequest(BaseModel):
    language: str
    code: str
    timeout: Optional[int] = None


class RunResponse(BaseModel):
    success: bool
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    exit_code: int = 0


class IndexRequest(BaseModel):
    project_path: str
    project_id: str = "local-project"
    reindex: bool = False


class IndexResponse(BaseModel):
    project_id: str
    files_indexed: int
    chunks_indexed: int
    files_skipped: int = 0
    files_updated: int = 0
    total_chunks: int = 0
    files: List[str] = []


class SearchRequest(BaseModel):
    query: str
    project_id: str = "local-project"
    top_k: int = 5


class ChunkResult(BaseModel):
    file: str
    language: str
    chunk_index: int
    start_line: int = 0
    end_line: int = 0
    content: str
    score: float = 0.0


class SearchResponse(BaseModel):
    results: List[ChunkResult] = []
    sources: List[str] = []


class ChatRequest(BaseModel):
    question: str
    language: str = "python"
    current_file: Optional[str] = None
    current_code: str = ""
    selected_code: str = ""
    execution_output: str = ""
    use_rag: bool = False
    project_id: str = "local-project"
    project_indexed: bool = False


class ChatResponse(BaseModel):
    answer: str
    suggested_code: str = ""
    diff: str = ""
    sources: List[str] = []
    source_lines: List[str] = []
    context_mode: str = "GENERAL"


class ActionRequest(BaseModel):
    code: str
    language: str = "python"
    execution_output: str = ""
    current_file: Optional[str] = None
    instruction: str = ""
    project_id: str = "local-project"
    use_project_context: bool = False


class ProjectFilesRequest(BaseModel):
    project_path: str


class ProjectFilesResponse(BaseModel):
    root: str
    files: List[str] = []
