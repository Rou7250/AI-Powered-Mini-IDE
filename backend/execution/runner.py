"""Executes code directly on the host system within a temporary sandbox directory."""
import os
import shutil
import subprocess
import tempfile
import time

from backend import config
from backend.execution.languages import get
from backend.security import truncate_output


def _capped(result):
    result["output"] = truncate_output(result.get("output", ""))
    result["error"] = truncate_output(result.get("error", ""))
    return result


def run_code(language, code, timeout=None):
    """Execute code. Output is truncated to MAX_OUTPUT_SIZE_KB."""
    timeout = timeout or config.CODE_EXECUTION_TIMEOUT
    spec = get(language)  # raises ValueError for unsupported languages

    if not (code or "").strip():
        return {
            "success": False,
            "output": "",
            "error": "No code to run.",
            "execution_time": 0.0,
            "exit_code": 1,
        }

    if not spec.get("command"):
        return {
            "success": False,
            "output": "",
            "error": f"{language.capitalize()} is not installed or not configured on this machine.",
            "execution_time": 0.0,
            "exit_code": 1,
        }

    executable = spec["command"][0]
    if not shutil.which(executable) and not os.path.isfile(executable):
        return {
            "success": False,
            "output": "",
            "error": f"Command '{executable}' not found. Please install {language.capitalize()} to run this code.",
            "execution_time": 0.0,
            "exit_code": 1,
        }

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, spec["filename"])
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)

        cmd = [c.replace("{file}", path) for c in spec["command"]]
        start = time.time()
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", os.getcwd()),
        }
        for var in ["SystemRoot", "SystemDrive", "TEMP", "TMP", "PATHEXT", "COMSPEC"]:
            val = os.environ.get(var)
            if val:
                env[var] = val

        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=tmp, env=env)
            return _capped({
                "success": proc.returncode == 0,
                "output": proc.stdout.decode("utf-8", "replace"),
                "error": proc.stderr.decode("utf-8", "replace"),
                "execution_time": round(time.time() - start, 3),
                "exit_code": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            return _capped({
                "success": False,
                "output": "",
                "error": f"Execution timed out after {timeout}s.",
                "execution_time": round(time.time() - start, 3),
                "exit_code": 124,
            })
        except OSError as exc:
            return _capped({
                "success": False,
                "output": "",
                "error": str(exc),
                "execution_time": 0.0,
                "exit_code": 1,
            })
