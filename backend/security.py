"""Shared path and size validation. Used by indexing, reading, writing and the agent."""
import os

from backend import config


class SecurityError(ValueError):
    """Raised when an operation would escape the project root or exceed a limit."""


def safe_project_root(project_path: str) -> str:
    root = os.path.realpath(os.path.abspath(os.path.expanduser(project_path or "")))
    if not os.path.isdir(root):
        raise FileNotFoundError("Project path does not exist: %s" % project_path)
    return root


def safe_project_path(project_path: str, relative_path: str) -> str:
    """Resolve relative_path inside project_path or raise SecurityError.

    Blocks '..' traversal, absolute paths and symlinks that point outside the root.
    """
    root = safe_project_root(project_path)
    if not relative_path or not str(relative_path).strip():
        raise SecurityError("Empty file path")
    if os.path.isabs(relative_path):
        raise SecurityError("Absolute paths are not allowed: %s" % relative_path)
    full = os.path.realpath(os.path.join(root, relative_path))
    if full != root and not full.startswith(root + os.sep):
        raise SecurityError("Path escapes the project directory: %s" % relative_path)
    return full


def check_file_size(path: str) -> int:
    limit = config.MAX_FILE_SIZE_MB * 1024 * 1024
    size = os.path.getsize(path)
    if size > limit:
        raise SecurityError("File exceeds MAX_FILE_SIZE_MB (%d MB): %s"
                            % (config.MAX_FILE_SIZE_MB, os.path.basename(path)))
    return size


def is_probably_binary(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(2048)
    except OSError:
        return True


def truncate_output(text: str) -> str:
    limit = config.MAX_OUTPUT_SIZE_KB * 1024
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[output truncated at %d KB]" % config.MAX_OUTPUT_SIZE_KB
