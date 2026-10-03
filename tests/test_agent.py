"""Agent tests. The LLM is always mocked - no API credentials are needed."""
import json

import pytest

from backend import config
from backend.agent import agent, tools
from backend.agent.schemas import AgentState


@pytest.fixture
def project(tmp_path):
    (tmp_path / "calc.py").write_text("def divide(a, b):\n    return a / c\n\n\n"
                                      "print(divide(10, 2))\n")
    return tmp_path


@pytest.fixture
def state(project):
    return AgentState(session_id="s1", task="fix it", project_path=str(project),
                      project_id="p1", language="python")


def script(*actions):
    """Turn a list of dicts into a fake sequential LLM."""
    queue = list(actions)

    def fake(system, user, max_tokens=None, temperature=0.2):
        return json.dumps(queue.pop(0)) if queue else json.dumps(
            {"tool": "finish", "arguments": {"summary": "done"}, "reason": "end"})
    return fake


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(agent.llm, "is_configured", lambda: True)


# ---- tool registry ----

def test_allowlist_blocks_unknown_tools():
    with pytest.raises(tools.ToolError):
        tools.validate_action("rm_rf", {})
    with pytest.raises(tools.ToolError):
        tools.validate_action("os.system", {})


def test_every_allowed_tool_has_a_handler():
    assert set(tools.HANDLERS) | {"finish"} == tools.ALLOWED_TOOLS


def test_arguments_must_be_an_object():
    with pytest.raises(tools.ToolError):
        tools.validate_action("search_project", "not-a-dict")


def test_missing_required_argument_is_rejected(state):
    with pytest.raises(tools.ToolError):
        tools.execute(state, "read_project_file", {})


def test_read_tool_blocks_traversal(state):
    with pytest.raises(tools.ToolError):
        tools.execute(state, "read_project_file", {"file_path": "../../etc/passwd"})


def test_read_tool_returns_line_range(state):
    result = tools.execute(state, "read_project_file",
                           {"file_path": "calc.py", "start_line": 1, "end_line": 2})
    assert "def divide" in result["content"] and result["end_line"] == 2


def test_run_code_records_error_category(state, monkeypatch):
    monkeypatch.setattr(tools, "_run_code",
                        lambda lang, code: {"success": False, "output": "",
                                            "error": "NameError: name 'c' is not defined",
                                            "exit_code": 1, "execution_time": 0.02})
    result = tools.execute(state, "run_code", {"file_path": "calc.py"})
    assert result["error_category"] == "NAME_ERROR"
    assert state.execution_output.exit_code == 1


def test_write_tool_only_proposes_and_never_writes(state, project):
    before = (project / "calc.py").read_text()
    result = tools.execute(state, "write_project_file",
                           {"file_path": "calc.py", "content": "x = 1\n", "reason": "fix"})
    assert (project / "calc.py").read_text() == before
    assert state.status == "waiting_for_approval"
    assert "+x = 1" in result["diff"]


def test_search_tool_reuses_existing_rag(state, monkeypatch):
    monkeypatch.setattr("backend.rag.retriever.search",
                        lambda q, p, k: [{"file": "calc.py", "language": "python",
                                          "score": 0.9, "start_line": 1, "end_line": 2,
                                          "content": "def divide", "chunk_index": 0}])
    result = tools.execute(state, "search_project", {"query": "divide"})
    assert result["results"][0]["file"] == "calc.py"
    assert state.retrieved_context


# ---- agent loop ----

def test_agent_requires_a_configured_llm(monkeypatch, project):
    monkeypatch.setattr(agent.llm, "is_configured", lambda: False)
    with pytest.raises(agent.AgentError):
        agent.start("fix it", str(project))


def test_empty_task_rejected(configured):
    with pytest.raises(agent.AgentError):
        agent.start("   ")


def test_invalid_llm_output_fails_cleanly(configured, monkeypatch, project):
    monkeypatch.setattr(agent.llm, "complete", lambda s, u, **k: "I am not JSON")
    state = agent.start("fix it", str(project))
    assert state.status == "failed" and "valid tool call" in state.error


def test_invalid_output_is_retried_once(configured, monkeypatch, project):
    replies = ["not json", json.dumps({"tool": "finish", "arguments": {"summary": "ok"},
                                       "reason": "done"})]
    monkeypatch.setattr(agent.llm, "complete", lambda s, u, **k: replies.pop(0))
    state = agent.start("fix it", str(project))
    assert state.status == "completed" and state.summary == "ok"


def test_forbidden_tool_from_llm_is_rejected(configured, monkeypatch, project):
    monkeypatch.setattr(agent.llm, "complete", lambda s, u, **k: json.dumps(
        {"tool": "delete_everything", "arguments": {}, "reason": "no"}))
    state = agent.start("fix it", str(project))
    assert state.status == "failed"


def test_max_iterations_is_enforced(configured, monkeypatch, project):
    monkeypatch.setattr(config, "MAX_AGENT_ITERATIONS", 3)
    monkeypatch.setattr(agent.llm, "complete", lambda s, u, **k: json.dumps(
        {"tool": "read_project_file", "arguments": {"file_path": "calc.py"},
         "reason": "looping"}))
    state = agent.start("fix it", str(project))
    assert state.status == "max_iterations" and state.iteration == 3


def test_failed_tool_does_not_stop_the_loop(configured, monkeypatch, project):
    monkeypatch.setattr(agent.llm, "complete", script(
        {"tool": "read_project_file", "arguments": {"file_path": "missing.py"},
         "reason": "try"},
        {"tool": "finish", "arguments": {"summary": "recovered"}, "reason": "done"}))
    state = agent.start("fix it", str(project))
    assert state.status == "completed"
    assert state.activity[0].ok is False and "not found" in state.activity[0].summary


def test_approve_without_pending_change_errors(configured, monkeypatch, project):
    monkeypatch.setattr(agent.llm, "complete", script(
        {"tool": "finish", "arguments": {"summary": "nothing to do"}, "reason": "done"}))
    state = agent.start("fix it", str(project))
    with pytest.raises(agent.AgentError):
        agent.approve(state.session_id)


def test_reject_leaves_files_untouched(configured, monkeypatch, project):
    before = (project / "calc.py").read_text()
    monkeypatch.setattr(agent.llm, "complete", script(
        {"tool": "generate_fix", "arguments": {"file_path": "calc.py",
                                               "content": "x = 1\n", "reason": "fix"},
         "reason": "propose"}))
    state = agent.start("fix it", str(project))
    assert state.status == "waiting_for_approval"
    rejected = agent.reject(state.session_id)
    assert rejected.status == "cancelled"
    assert (project / "calc.py").read_text() == before


def test_unknown_session_raises():
    with pytest.raises(KeyError):
        agent.get_session("nope")


def test_cancel_marks_session_cancelled(configured, monkeypatch, project):
    monkeypatch.setattr(agent.llm, "complete", script(
        {"tool": "generate_fix", "arguments": {"file_path": "calc.py",
                                               "content": "x = 2\n", "reason": "fix"},
         "reason": "propose"}))
    state = agent.start("fix it", str(project))
    assert agent.cancel(state.session_id).status == "cancelled"


# ---- the full scenario from the spec ----

FIXED = "def divide(a, b):\n    return a / b\n\n\nprint(divide(10, 2))\n"


def test_end_to_end_find_bug_propose_approve_verify(configured, monkeypatch, project):
    """Run code -> NameError -> propose fix -> approve -> re-run -> verify -> finish."""
    runs = []

    def fake_run(language, code):
        runs.append(code)
        if "a / c" in code:
            return {"success": False, "output": "",
                    "error": "NameError: name 'c' is not defined",
                    "exit_code": 1, "execution_time": 0.02}
        return {"success": True, "output": "5.0\n", "error": "", "exit_code": 0,
                "execution_time": 0.02}

    monkeypatch.setattr(tools, "_run_code", fake_run)
    monkeypatch.setattr("backend.rag.retriever.search",
                        lambda q, p, k: [{"file": "calc.py", "language": "python",
                                          "score": 0.91, "start_line": 1, "end_line": 4,
                                          "content": "def divide(a, b):\n    return a / c",
                                          "chunk_index": 0}])
    monkeypatch.setattr(agent.llm, "complete", script(
        {"tool": "search_project", "arguments": {"query": "divide"}, "reason": "locate"},
        {"tool": "read_project_file", "arguments": {"file_path": "calc.py"},
         "reason": "read it"},
        {"tool": "run_code", "arguments": {"file_path": "calc.py"}, "reason": "reproduce"},
        {"tool": "generate_fix", "arguments": {"file_path": "calc.py", "content": FIXED,
                                               "reason": "c should be b"},
         "reason": "propose fix"},
        # after approval:
        {"tool": "run_again", "arguments": {"file_path": "calc.py"}, "reason": "verify"},
        {"tool": "finish", "arguments": {"summary": "Renamed c to b; verified exit code 0."},
         "reason": "done"}))

    state = agent.start("Find the error and fix it.", str(project), "p1")

    # paused for approval, nothing written yet
    assert state.status == "waiting_for_approval"
    assert "a / c" in (project / "calc.py").read_text()
    assert state.execution_output.error_category == "NAME_ERROR"
    assert [a.tool for a in state.activity] == ["search_project", "read_project_file",
                                                "run_code", "generate_fix"]
    assert "-    return a / c" in state.pending_change().diff

    final = agent.approve(state.session_id)

    assert final.status == "completed"
    assert (project / "calc.py").read_text() == FIXED   # really written
    assert len(runs) == 2                               # really re-executed
    assert final.execution_output.status == "success"
    assert final.execution_output.exit_code == 0
    assert "verified" in final.summary

    restored = agent.undo(final.session_id)
    assert "a / c" in (project / "calc.py").read_text()
    assert restored.status == "completed"
