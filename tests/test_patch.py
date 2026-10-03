import os

import pytest

from backend.agent import patch
from backend.security import SecurityError


@pytest.fixture
def project(tmp_path):
    (tmp_path / "calc.py").write_text("def divide(a, b):\n    return a / c\n")
    return tmp_path


def test_make_diff_shows_change():
    diff = patch.make_diff("calc.py", "return a / c\n", "return a / b\n")
    assert "-return a / c" in diff and "+return a / b" in diff


def test_validate_rejects_empty_and_identical():
    with pytest.raises(ValueError):
        patch.validate("x = 1\n", "   ")
    with pytest.raises(ValueError):
        patch.validate("x = 1\n", "x = 1\n")


def test_apply_creates_backup_and_writes(project):
    backup = patch.apply_change(str(project), "calc.py",
                                "def divide(a, b):\n    return a / b\n")
    assert os.path.isfile(backup)
    assert "a / b" in (project / "calc.py").read_text()
    assert "a / c" in open(backup).read()


def test_undo_restores_previous_version(project):
    backup = patch.apply_change(str(project), "calc.py", "def divide(a, b):\n    return a / b\n")
    patch.undo_change(str(project), "calc.py", backup)
    assert "a / c" in (project / "calc.py").read_text()


def test_apply_rejects_path_traversal(project):
    with pytest.raises(SecurityError):
        patch.apply_change(str(project), "../evil.py", "x = 1\n")


def test_apply_missing_file_raises(project):
    with pytest.raises(FileNotFoundError):
        patch.apply_change(str(project), "nope.py", "x = 1\n")


def test_undo_rejects_backup_outside_backup_dir(project, tmp_path):
    rogue = tmp_path.parent / "rogue.bak"
    rogue.write_text("malicious")
    with pytest.raises((SecurityError, FileNotFoundError)):
        patch.undo_change(str(project), "calc.py", str(rogue))
