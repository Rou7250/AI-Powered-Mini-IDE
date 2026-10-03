from backend.execution import errors


def _fail(text, exit_code=1):
    return {"success": False, "error": text, "output": "", "exit_code": exit_code}


def test_success_is_none():
    assert errors.classify({"success": True, "exit_code": 0}) == "NONE"


def test_categories():
    assert errors.classify(_fail("NameError: name 'c' is not defined")) == "NAME_ERROR"
    assert errors.classify(_fail("TypeError: unsupported operand")) == "TYPE_ERROR"
    assert errors.classify(_fail("SyntaxError: invalid syntax")) == "SYNTAX_ERROR"
    assert errors.classify(_fail("ModuleNotFoundError: No module named 'x'")) == "DEPENDENCY_ERROR"
    assert errors.classify(_fail("Docker error: daemon down")) == "DOCKER_ERROR"
    assert errors.classify(_fail("cannot find symbol")) == "COMPILATION_ERROR"
    assert errors.classify(_fail("anything", exit_code=124)) == "TIMEOUT"
    assert errors.classify(_fail("ZeroDivisionError: division by zero")) == "RUNTIME_ERROR"


def test_every_category_has_an_explanation():
    for name in errors.CATEGORIES:
        assert errors.explain(name)
