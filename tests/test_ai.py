import pytest

from backend.ai import assistant, llm
from backend.models.schemas import ActionRequest, ChatRequest

ANSWER = "Here is the fix.\n```python\nprint('fixed')\n```\nSee payment.py for details."


@pytest.fixture
def fake_llm(monkeypatch):
    calls = {}

    def fake(system, user, max_tokens=None, temperature=0.2):
        calls["system"] = system
        calls["user"] = user
        return ANSWER

    monkeypatch.setattr(assistant.llm, "complete", fake)
    return calls


def test_extract_code_picks_largest_block():
    assert assistant.extract_code(ANSWER) == "print('fixed')"
    assert assistant.extract_code("no code here") == ""


def test_general_question(fake_llm):
    res = assistant.chat(ChatRequest(question="What is inheritance in Python?"))
    assert res["context_mode"] == "GENERAL"
    assert res["sources"] == []


def test_current_code_question(fake_llm):
    res = assistant.chat(ChatRequest(question="Why is this function wrong?",
                                     current_code="def f():\n    return 1/0"))
    assert res["context_mode"] == "CURRENT_CODE"
    assert "Current code" in fake_llm["user"]


def test_error_question_includes_execution_output(fake_llm):
    res = assistant.chat(ChatRequest(question="Why am I getting this TypeError?",
                                     current_code="x = 1 + 'a'",
                                     execution_output="TypeError: unsupported operand"))
    assert res["context_mode"] == "ERROR"
    assert "TypeError: unsupported operand" in fake_llm["user"]


def test_rag_question_uses_retrieved_context(monkeypatch, fake_llm):
    monkeypatch.setattr("backend.rag.retriever.search",
                        lambda q, p, k: [{"file": "payment.py", "language": "python",
                                          "chunk_index": 0, "content": "def charge(): ...",
                                          "score": 0.9}])
    res = assistant.chat(ChatRequest(question="How does login connect to payment processing?",
                                     project_indexed=True))
    assert res["context_mode"] == "PROJECT_RAG"
    assert res["sources"] == ["payment.py"]
    assert "payment.py" in fake_llm["user"]
    assert fake_llm["system"].startswith("You are an AI programming assistant")


def test_action_with_empty_code_short_circuits(fake_llm):
    res = assistant.run_action("fix", ActionRequest(code="   "))
    assert "no code" in res["answer"].lower()
    assert res["suggested_code"] == ""


def test_explain_action_does_not_propose_code(fake_llm):
    res = assistant.run_action("explain", ActionRequest(code="print(1)"))
    assert res["suggested_code"] == ""


def test_fix_action_returns_suggested_code(fake_llm):
    res = assistant.run_action("fix", ActionRequest(code="print(1/0)",
                                                    execution_output="ZeroDivisionError"))
    assert res["suggested_code"] == "print('fixed')"


def test_llm_error_propagates(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("provider down")
    monkeypatch.setattr(assistant.llm, "complete", boom)
    with pytest.raises(llm.LLMError):
        assistant.chat(ChatRequest(question="hi"))
