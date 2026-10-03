import os
from dotenv import load_dotenv

load_dotenv(override=True)
# Config loaded



def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MAX_TOKENS = _int("LLM_MAX_TOKENS", 1600)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_data")

CODE_EXECUTION_TIMEOUT = _int("CODE_EXECUTION_TIMEOUT", 10)

MAX_CHUNK_LINES = _int("MAX_CHUNK_LINES", 60)
CHUNK_OVERLAP_LINES = _int("CHUNK_OVERLAP_LINES", 10)
RAG_TOP_K = _int("RAG_TOP_K", 5)

# ---- Agent ----
MAX_AGENT_ITERATIONS = _int("MAX_AGENT_ITERATIONS", 5)

# ---- Limits ----
MAX_FILE_SIZE_MB = _int("MAX_FILE_SIZE_MB", 5)
MAX_PROJECT_SIZE_MB = _int("MAX_PROJECT_SIZE_MB", 100)
MAX_OUTPUT_SIZE_KB = _int("MAX_OUTPUT_SIZE_KB", 100)
