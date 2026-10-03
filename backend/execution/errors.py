"""Classifies execution failures into useful categories."""
import re

CATEGORIES = ("SYNTAX_ERROR", "RUNTIME_ERROR", "IMPORT_ERROR", "TYPE_ERROR", "NAME_ERROR",
              "DEPENDENCY_ERROR", "COMPILATION_ERROR", "TIMEOUT", "DOCKER_ERROR",
              "UNKNOWN_ERROR", "NONE")

_RULES = [
    ("TIMEOUT", re.compile(r"timed out", re.I)),
    ("DOCKER_ERROR", re.compile(r"^\s*(Docker error|Docker is not available|"
                                r"Cannot connect to the Docker daemon)", re.I | re.M)),
    ("SYNTAX_ERROR", re.compile(r"\b(SyntaxError|IndentationError|TabError|"
                                r"Unexpected token|Unexpected end of input)\b")),
    ("DEPENDENCY_ERROR", re.compile(r"(No module named|Cannot find module|"
                                    r"package .* does not exist)", re.I)),
    ("COMPILATION_ERROR", re.compile(r"((?<![A-Za-z])error: |cannot find symbol|javac|"
                                     r"compilation failed)", re.I)),
    ("IMPORT_ERROR", re.compile(r"\bImportError\b")),
    ("NAME_ERROR", re.compile(r"\b(NameError|ReferenceError|is not defined)\b")),
    ("TYPE_ERROR", re.compile(r"\bTypeError\b")),
]

EXPLANATIONS = {
    "SYNTAX_ERROR": "The code could not be parsed - there is a typo or malformed statement.",
    "RUNTIME_ERROR": "The code parsed and started, then failed while running.",
    "IMPORT_ERROR": "A module exists but could not be imported.",
    "TYPE_ERROR": "An operation was applied to a value of the wrong type.",
    "NAME_ERROR": "A name was used before it was defined - often a typo in a variable name.",
    "DEPENDENCY_ERROR": "A required package is not installed in the sandbox image.",
    "COMPILATION_ERROR": "Compilation failed before the program could run.",
    "TIMEOUT": "The program exceeded the execution time limit - possibly an infinite loop.",
    "DOCKER_ERROR": "The sandbox itself could not start. This is an environment problem.",
    "UNKNOWN_ERROR": "The program failed for a reason that could not be classified.",
    "NONE": "No error.",
}


def classify(result: dict) -> str:
    if result.get("success"):
        return "NONE"
    if result.get("exit_code") == 124:
        return "TIMEOUT"
    text = (result.get("error") or "") + "\n" + (result.get("output") or "")
    for name, pattern in _RULES:
        if pattern.search(text):
            return name
    if re.search(r"\b\w*(Error|Exception)\b", text):
        return "RUNTIME_ERROR"
    return "UNKNOWN_ERROR" if text.strip() else "RUNTIME_ERROR"


def explain(category: str) -> str:
    return EXPLANATIONS.get(category, EXPLANATIONS["UNKNOWN_ERROR"])
