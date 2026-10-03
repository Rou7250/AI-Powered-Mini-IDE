from fastapi import APIRouter, HTTPException

from backend.models.schemas import (IndexRequest, IndexResponse, ProjectFilesRequest,
                                    ProjectFilesResponse, SearchRequest, SearchResponse)
from backend.rag import indexer, retriever
from backend.security import SecurityError

router = APIRouter(prefix="/api/project", tags=["project"])


@router.post("/files", response_model=ProjectFilesResponse)
def files(req: ProjectFilesRequest):
    try:
        root, found = indexer.list_project_files(req.project_path)
        return ProjectFilesResponse(root=root, files=found)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/file")
def read_file(req: ProjectFilesRequest, relative_path: str):
    try:
        return {"content": indexer.read_project_file(req.project_path, relative_path)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/index", response_model=IndexResponse)
def index(req: IndexRequest):
    try:
        result = indexer.index_project(req.project_path, req.project_id, req.reindex)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Indexing failed: %s" % exc)
    return IndexResponse(project_id=result["project_id"], files_indexed=result["files_indexed"],
                         chunks_indexed=result["chunks_indexed"],
                         files_skipped=result.get("files_skipped", 0),
                         files_updated=result.get("files_updated", 0),
                         total_chunks=result.get("total_chunks", 0), files=result["files"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    try:
        results = retriever.search(req.query, req.project_id, req.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Search failed: %s" % exc)
    return SearchResponse(results=results, sources=retriever.sources_of(results))
