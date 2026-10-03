"""Rule-based context router: decides what context a question needs."""
import re

GENERAL = "GENERAL"
CURRENT_CODE = "CURRENT_CODE"
ERROR = "ERROR"
PROJECT_RAG = "PROJECT_RAG"
AGENT = "AGENT"

_ERROR_WORDS = re.compile(
    r"(\b(error|exception|traceback|stack ?trace|crash|fail(?:s|ed|ing)?|bug|broken|"
    r"not working)\b|\w*(Error|Exception)\b)", re.I)

_PROJECT_WORDS = re.compile(
    r"\b(project|codebase|repo(?:sitory)?|across files|multiple files|other files?|module|"
    r"architecture|where is|where are|which file|what file|connect(?:s|ed|ion)?|entry ?point|"
    r"structure of|folder|imported)\b", re.I)

_CURRENT_WORDS = re.compile(
    r"\b(this (?:code|function|snippet|file|line|class|loop)|my code|the code above|"
    r"selected code)\b", re.I)

_GENERAL_WORDS = re.compile(
    r"^(what is|what are|explain the concept|difference between|how do i|when should i)\b", re.I)


def determine_context(question, current_code="", project_indexed=False,
                      execution_output="", force_rag=False, agent_mode=False):
    """Return one of GENERAL / CURRENT_CODE / ERROR / PROJECT_RAG / AGENT.

    AGENT is only returned when the UI is explicitly in agent mode; agent requests
    are handled by the tool loop rather than by a static prompt.
    """
    if agent_mode:
        return AGENT
    q = (question or "").strip()
    has_code = bool((current_code or "").strip())
    has_error = bool((execution_output or "").strip())

    if force_rag and project_indexed:
        return PROJECT_RAG
    if project_indexed and _PROJECT_WORDS.search(q) and not _CURRENT_WORDS.search(q):
        return PROJECT_RAG
    if has_error and _ERROR_WORDS.search(q):
        return ERROR
    if has_code and (_CURRENT_WORDS.search(q) or _ERROR_WORDS.search(q)):
        return CURRENT_CODE
    if _GENERAL_WORDS.search(q):
        return GENERAL
    if has_code:
        return CURRENT_CODE
    if project_indexed:
        return PROJECT_RAG
    return GENERAL
