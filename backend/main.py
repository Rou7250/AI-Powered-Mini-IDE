from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.ai import llm
from backend.logging_config import setup as setup_logging
from backend.routes import agent, ai, code, project

setup_logging()

app = FastAPI(title="AI-powered mini IDE API", version="1.0.0",
              description="Backend for AI-powered mini IDE: code execution, RAG, AI actions.")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(code.router)
app.include_router(project.router)
app.include_router(ai.router)
app.include_router(agent.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": llm.is_configured(),
            "llm_model": config.LLM_MODEL if llm.is_configured() else None,
            "embedding_model": config.EMBEDDING_MODEL,
            "max_agent_iterations": config.MAX_AGENT_ITERATIONS}
