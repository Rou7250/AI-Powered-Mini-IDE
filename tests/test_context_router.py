from backend.ai.context_router import determine_context

CODE = "def f():\n    return 1/0\n"


def test_general_question_without_code():
    assert determine_context("What is inheritance in Python?") == "GENERAL"


def test_current_code_question():
    assert determine_context("Why is this function wrong?", CODE) == "CURRENT_CODE"


def test_error_question_uses_execution_output():
    mode = determine_context("Why am I getting this TypeError?", CODE,
                             execution_output="TypeError: bad operand")
    assert mode == "ERROR"


def test_project_question_routes_to_rag_when_indexed():
    assert determine_context("Where is authentication implemented?", CODE,
                             project_indexed=True) == "PROJECT_RAG"


def test_project_question_without_index_does_not_use_rag():
    assert determine_context("Where is authentication implemented?", CODE,
                             project_indexed=False) != "PROJECT_RAG"


def test_force_rag_overrides_rules():
    assert determine_context("Explain this code", CODE, project_indexed=True,
                             force_rag=True) == "PROJECT_RAG"


def test_empty_question_is_safe():
    assert determine_context("", "", False) == "GENERAL"
