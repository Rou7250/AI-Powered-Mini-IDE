import os
import shutil
import sys
from pathlib import Path



def _find_java():
    proj_root = Path(__file__).resolve().parent.parent.parent
    local_java = proj_root / "tools" / "jdk" / "bin" / ("java.exe" if os.name == "nt" else "java")
    if local_java.is_file():
        return str(local_java)
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        home_java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if home_java.is_file():
            return str(home_java)
    return shutil.which("java")


LANGUAGES = {
    "python": {
        "filename": "main.py",
        "command": [sys.executable, "{file}"],
        "editor_mode": "python",
    },
    "javascript": {
        "filename": "main.js",
        "command": ["node", "{file}"],
        "editor_mode": "javascript",
    },
    "java": {
        "filename": "Main.java",
        "command": None,
        "editor_mode": "java",
    },
}

SUPPORTED = sorted(LANGUAGES)


def get(language):
    key = (language or "").lower()
    if key not in LANGUAGES:
        raise ValueError("Unsupported language: %s. Supported: %s"
                         % (language, ", ".join(SUPPORTED)))
    spec = dict(LANGUAGES[key])
    if key == "java":
        java_cmd = _find_java()
        if java_cmd:
            spec["command"] = [java_cmd, "{file}"]
    return spec

