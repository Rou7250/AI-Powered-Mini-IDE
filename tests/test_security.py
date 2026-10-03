import os

import pytest

from backend import config
from backend.security import (SecurityError, check_file_size, is_probably_binary,
                              safe_project_path, safe_project_root, truncate_output)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "app.py").write_text("print('hi')\n")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "mod.py").write_text("x = 1\n")
    (tmp_path / "bin.dat").write_bytes(b"\x00\x01\x02")
    return tmp_path


def test_valid_paths_resolve(project):
    assert safe_project_path(str(project), "app.py").endswith("app.py")
    assert safe_project_path(str(project), "pkg/mod.py").endswith(os.path.join("pkg", "mod.py"))


@pytest.mark.parametrize("bad", ["../secret.txt", "../../etc/passwd", "pkg/../../out.py",
                                 "/etc/passwd", "", "   "])
def test_traversal_and_absolute_paths_blocked(project, bad):
    with pytest.raises(SecurityError):
        safe_project_path(str(project), bad)


def test_symlink_escaping_root_is_blocked(project, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret")
    link = project / "link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(SecurityError):
        safe_project_path(str(project), "link.txt")


def test_invalid_project_root_raises():
    with pytest.raises(FileNotFoundError):
        safe_project_root("/no/such/project")


def test_oversized_file_rejected(project, monkeypatch):
    big = project / "big.py"
    big.write_text("x" * 2048)
    monkeypatch.setattr(config, "MAX_FILE_SIZE_MB", 0)
    with pytest.raises(SecurityError):
        check_file_size(str(big))


def test_binary_detection(project):
    assert is_probably_binary(str(project / "bin.dat")) is True
    assert is_probably_binary(str(project / "app.py")) is False


def test_output_truncation(monkeypatch):
    monkeypatch.setattr(config, "MAX_OUTPUT_SIZE_KB", 1)
    out = truncate_output("a" * 5000)
    assert len(out) < 5000 and "truncated" in out
    assert truncate_output("short") == "short"
