# CodeForge AI — AI-Powered Mini IDE

A browser-based development environment that combines code editing, multi-language execution, repository-aware RAG, AI-assisted debugging, and a controlled autonomous coding agent.

---

## Overview

CodeForge AI is an AI-assisted development environment designed to bring coding, execution, repository search, debugging, and code modification into a single unified workflow.

Unlike a conventional chatbot where developers manually copy code and error messages into a separate interface, CodeForge AI can work with the active editor, terminal output, and indexed project files. This allows the AI to provide context-aware assistance and, when the autonomous agent is enabled, investigate, reproduce, propose, apply, and verify code changes through a human approval step.

---

## Key Capabilities

- **Web-based code editor**: Syntax highlighting and multi-language support (Python, JavaScript, Java, etc.).
- **Multi-language execution**: Run Python, JavaScript (Node.js), and Java through controlled subprocesses.
- **Repository-aware RAG**: Local embeddings and ChromaDB vector search for codebases.
- **Incremental indexing**: Efficient project indexing tracked via SHA-256 file hashes.
- **Context-aware AI assistance**: Dedicated routing for general questions, current code, execution errors, and project-level queries.
- **Autonomous ReAct coding agent**: Iterative loop with an explicit tool allowlist to plan, read files, run code, propose patches, and test fixes.
- **Human approval workflow**: Inspect interactive diffs before any changes are committed to disk.
- **Automatic backup & rollback**: Safety backups before any file patch with one-click restore.
- **Post-change verification**: Automatically executes modified code to confirm fixes.
- **Mock LLM mode**: Full local evaluation support without requiring paid API keys.

---

## Architecture

CodeForge AI follows a client-server architecture with a Streamlit frontend and FastAPI backend:

```text
                         ┌─────────────────────────────┐
                         │       Streamlit Frontend    │
                         │                             │
                         │  Editor │ Chat │ Terminal   │
                         │  Project │ Agent │ Settings │
                         └──────────────┬──────────────┘
                                        │
                                   HTTP / REST
                                        │
                         ┌──────────────▼──────────────┐
                         │       FastAPI Backend       │
                         │                             │
                         │ Code │ Project │ AI │ Agent │
                         └───────┬─────────┬───────────┘
                                 │         │
              ┌──────────────────┼─────────┼──────────────────┐
              │                  │         │                  │
      ┌───────▼──────┐   ┌──────▼─────┐  ┌▼───────────────┐  │
      │ Code Runner  │   │ RAG Engine  │  │ Context Router │  │
      │              │   │             │  │                │  │
      │ Python       │   │ Chunking    │  │ General        │  │
      │ JavaScript   │   │ Embeddings  │  │ Current Code   │  │
      │ Java         │   │ ChromaDB    │  │ Error          │  │
      └──────────────┘   └─────────────┘  │ Project RAG    │  │
                                           └────────────────┘  │
                                                              │
                                                   ┌──────────▼──────┐
                                                   │ Autonomous Agent│
                                                   │                 │
                                                   │ Plan → Inspect  │
                                                   │ → Run → Diff    │
                                                   │ → Approve → Fix │
                                                   │ → Verify        │
                                                   └─────────────────┘
```

---

## Main Components

| Layer | Technology | Responsibility |
|---|---|---|
| **Frontend** | Streamlit | Web IDE, editor, chat, terminal, project explorer, and agent interface |
| **Code Editor** | Streamlit-Ace | Source editing and syntax highlighting |
| **API** | FastAPI | REST API, request validation, routing |
| **Server** | Uvicorn | High-performance ASGI application server |
| **Validation** | Pydantic | API request and response data models |
| **Vector Database** | ChromaDB | Local vector storage and semantic retrieval |
| **Embeddings** | Sentence-Transformers | Code/query embeddings using `all-MiniLM-L6-v2` |
| **LLM** | Anthropic / OpenAI / Mock | AI reasoning and code generation/assistance |
| **Execution** | Python Subprocess / Node / Java | Controlled multi-language code execution |
| **Configuration** | python-dotenv | Environment variable loading |
| **Testing** | Pytest | Comprehensive test suite |

---

## How to Run

### 1. Activate Environment
```bash
# Windows (PowerShell)
.venv\Scripts\activate

# Windows (CMD)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 2. Run Backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### 3. Run Frontend
```bash
streamlit run frontend/app.py
```