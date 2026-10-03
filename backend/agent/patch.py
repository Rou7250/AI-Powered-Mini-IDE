"""Diff creation, backup, apply and undo. Files are never written without a backup."""
import difflib
import os
import shutil
import time

from backend.security import SecurityError, safe_project_path

BACKUP_DIR = ".codeforge_backups"


def make_diff(file_path: str, original: str, proposed: str) -> str:
    diff = difflib.unified_diff(original.splitlines(keepends=True),
                                proposed.splitlines(keepends=True),
                                fromfile="a/" + file_path, tofile="b/" + file_path)
    return "".join(diff)


def validate(original: str, proposed: str) -> None:
    if proposed is None or not str(proposed).strip():
        raise ValueError("Proposed content is empty - refusing to write.")
    if proposed == original:
        raise ValueError("Proposed content is identical to the current file.")


def apply_change(project_path: str, file_path: str, proposed: str) -> str:
    """Back up the file, then write the new content. Returns the backup path."""
    full = safe_project_path(project_path, file_path)
    if not os.path.isfile(full):
        raise FileNotFoundError("File does not exist: %s" % file_path)
    backup_root = os.path.join(os.path.realpath(project_path), BACKUP_DIR)
    os.makedirs(backup_root, exist_ok=True)
    backup = os.path.join(backup_root, "%s.%d.bak"
                          % (file_path.replace(os.sep, "__"), int(time.time() * 1000)))
    shutil.copy2(full, backup)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(proposed)
    return backup


def undo_change(project_path: str, file_path: str, backup_path: str) -> None:
    full = safe_project_path(project_path, file_path)
    if not backup_path or not os.path.isfile(backup_path):
        raise FileNotFoundError("No backup available for %s" % file_path)
    real_backup = os.path.realpath(backup_path)
    expected_root = os.path.join(os.path.realpath(project_path), BACKUP_DIR)
    if not real_backup.startswith(expected_root + os.sep):
        raise SecurityError("Backup path is outside the project backup directory")
    shutil.copy2(real_backup, full)
