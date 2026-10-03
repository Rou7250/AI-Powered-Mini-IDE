import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "status" in body and "llm_configured" in body


def test_run_unsupported_language_returns_400():
    r = client.post("/api/code/run", json={"language": "cobol", "code": "x"})
    assert r.status_code == 400


def test_run_endpoint_shape(monkeypatch):
    monkeypatch.setattr("backend.routes.code.run_code",
                        lambda l, c, t: {"success": True, "output": "30", "error": "",
                                         "execution_time": 0.12, "exit_code": 0})
    body = client.post("/api/code/run", json={"language": "python",
                                              "code": "print(10+20)"}).json()
    assert body == {"success": True, "output": "30", "error": "",
                    "execution_time": 0.12, "exit_code": 0}


def test_chat_requires_a_question():
    assert client.post("/api/ai/chat", json={"question": "  "}).status_code == 400


def test_chat_endpoint(monkeypatch):
    monkeypatch.setattr("backend.routes.ai.assistant.chat",
                        lambda req: {"answer": "ok", "suggested_code": "",
                                     "sources": ["auth.py"], "context_mode": "PROJECT_RAG"})
    body = client.post("/api/ai/chat", json={"question": "where is auth?"}).json()
    assert body["sources"] == ["auth.py"] and body["context_mode"] == "PROJECT_RAG"


def test_ai_action_endpoints_exist(monkeypatch):
    monkeypatch.setattr("backend.routes.ai.assistant.run_action",
                        lambda kind, req: {"answer": kind, "suggested_code": "x",
                                           "sources": [], "context_mode": "CURRENT_CODE"})
    for kind in ("explain", "debug", "fix", "optimize", "refactor", "tests"):
        r = client.post("/api/ai/" + kind, json={"code": "print(1)"})
        assert r.status_code == 200 and r.json()["answer"] == kind


def test_index_missing_path_returns_404():
    r = client.post("/api/project/index", json={"project_path": "/no/such/dir"})
    assert r.status_code == 404


def test_project_files_missing_path_returns_404():
    assert client.post("/api/project/files",
                       json={"project_path": "/no/such/dir"}).status_code == 404


def test_search_endpoint(monkeypatch):
    monkeypatch.setattr("backend.routes.project.retriever.search",
                        lambda q, p, k: [{"file": "auth.py", "language": "python",
                                          "chunk_index": 1, "content": "def login(): ...",
                                          "score": 0.8}])
    body = client.post("/api/project/search", json={"query": "login"}).json()
    assert body["sources"] == ["auth.py"] and body["results"][0]["file"] == "auth.py"


# ---- agent endpoints ----

def _fake_state(status="completed", **kw):
    from backend.agent.schemas import AgentState
    kw.setdefault("summary", "ok")
    return AgentState(session_id="sid", task="t", status=status, **kw)


def test_agent_run(monkeypatch):
    monkeypatch.setattr("backend.routes.agent.agent.start",
                        lambda *a: _fake_state())
    body = client.post("/api/agent/run", json={"task": "fix the bug"}).json()
    assert body["session_id"] == "sid" and body["status"] == "completed"


def test_agent_run_validation_error():
    assert client.post("/api/agent/run", json={}).status_code == 422


def test_agent_run_without_llm_returns_400(monkeypatch):
    from backend.agent import agent as agent_mod

    def boom(*a):
        raise agent_mod.AgentError("Agent mode needs a real LLM.")
    monkeypatch.setattr("backend.routes.agent.agent.start", boom)
    r = client.post("/api/agent/run", json={"task": "fix"})
    assert r.status_code == 400 and "LLM" in r.json()["detail"]


def test_agent_status_unknown_session_404(monkeypatch):
    r = client.get("/api/agent/status/does-not-exist")
    assert r.status_code == 404


def test_agent_approve_reject_undo(monkeypatch):
    for action in ("approve", "reject", "undo", "cancel"):
        monkeypatch.setattr("backend.routes.agent.agent." + action,
                            lambda sid, _a=action: _fake_state(summary=_a))
        body = client.post("/api/agent/" + action, json={"session_id": "sid"}).json()
        assert body["summary"] == action


def test_agent_approve_missing_session_id_422():
    assert client.post("/api/agent/approve", json={}).status_code == 422


def test_health_reports_agent_limit():
    assert client.get("/api/health").json()["max_agent_iterations"] >= 1
