"""Small HTTP client wrapping the FastAPI backend."""
import os

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


class APIError(Exception):
    pass


def _post(path, payload, timeout=180, params=None):
    try:
        r = requests.post(BACKEND_URL + path, json=payload, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise APIError("Cannot reach the backend at %s (%s)" % (BACKEND_URL, exc))
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise APIError(str(detail))
    return r.json()


def health():
    try:
        r = requests.get(BACKEND_URL + "/api/health", timeout=10)
        return r.json() if r.status_code == 200 else None
    except requests.RequestException:
        return None


def run_code(language, code):
    return _post("/api/code/run", {"language": language, "code": code}, timeout=90)


def list_files(project_path):
    return _post("/api/project/files", {"project_path": project_path}, timeout=60)


def read_file(project_path, relative_path):
    return _post("/api/project/file", {"project_path": project_path},
                 params={"relative_path": relative_path}, timeout=60)


def index_project(project_path, project_id="local-project", reindex=False):
    return _post("/api/project/index",
                 {"project_path": project_path, "project_id": project_id,
                  "reindex": reindex}, timeout=900)


def search_project(query, project_id="local-project", top_k=5):
    return _post("/api/project/search",
                 {"query": query, "project_id": project_id, "top_k": top_k})


def chat(**payload):
    return _post("/api/ai/chat", payload)


def action(kind, code, language, execution_output="", current_file=None, instruction="",
           use_project_context=False, project_id="local-project"):
    return _post("/api/ai/" + kind,
                 {"code": code, "language": language, "execution_output": execution_output,
                  "current_file": current_file, "instruction": instruction,
                  "use_project_context": use_project_context, "project_id": project_id})


# ---- Agent ----

def agent_run(task, project_path, project_id, language, current_file, current_code,
              selected_code=""):
    return _post("/api/agent/run",
                 {"task": task, "project_path": project_path, "project_id": project_id,
                  "language": language, "current_file": current_file,
                  "current_code": current_code, "selected_code": selected_code},
                 timeout=600)


def agent_approve(session_id):
    return _post("/api/agent/approve", {"session_id": session_id}, timeout=600)


def agent_reject(session_id):
    return _post("/api/agent/reject", {"session_id": session_id})


def agent_undo(session_id):
    return _post("/api/agent/undo", {"session_id": session_id})


def agent_cancel(session_id):
    return _post("/api/agent/cancel", {"session_id": session_id})


def agent_status(session_id):
    try:
        r = requests.get(BACKEND_URL + "/api/agent/status/" + session_id, timeout=30)
    except requests.RequestException as exc:
        raise APIError(str(exc))
    if r.status_code >= 400:
        raise APIError(r.text)
    return r.json()
