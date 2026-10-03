import pytest

from backend.execution import runner
from backend.execution.languages import SUPPORTED, get


def test_supported_languages():
    assert SUPPORTED == ["java", "javascript", "python"]


def test_unsupported_language_raises():
    with pytest.raises(ValueError):
        get("cobol")
    with pytest.raises(ValueError):
        runner.run_code("cobol", "print(1)")


def test_empty_code_is_rejected():
    result = runner.run_code("python", "   ")
    assert result["success"] is False and "No code" in result["error"]


def test_python_success():
    result = runner.run_code("python", "print(10 + 20)")
    assert result["success"] is True and "30" in result["output"]


def test_python_error():
    result = runner.run_code("python", "print(1/0)")
    assert result["success"] is False and "ZeroDivisionError" in result["error"]


def test_timeout_is_enforced():
    result = runner.run_code("python", "import time\ntime.sleep(10)", timeout=1)
    assert result["exit_code"] == 124 and "timed out" in result["error"]


def test_java_missing_reports_clean_error(monkeypatch):
    monkeypatch.setattr("backend.execution.languages._find_java", lambda: None)
    result = runner.run_code("java", "class Main {}")
    assert result["success"] is False and "not installed" in result["error"].lower()


def test_javascript_success_if_node_installed():
    import shutil
    if shutil.which("node"):
        result = runner.run_code("javascript", "console.log(2 + 3);")
        assert result["success"] is True and "5" in result["output"]
