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

## Getting Started & Run Commands

Follow the steps below to set up and run CodeForge AI locally.

### 1. Prerequisites

- **Python**: 3.10 or higher
- **Node.js** *(Optional)*: Required for running JavaScript code
- **Java JDK** *(Optional)*: Required for running Java code

---

### 2. Clone Repository & Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Rou7250/AI-Powered-Mini-IDE.git
cd AI-Powered-Mini-IDE
```

#### Create and Activate Virtual Environment:

- **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

- **On Windows (Command Prompt):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  ```

- **On macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

---

### 3. Install Dependencies

Install all required Python packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables

Create your `.env` configuration file from the template:

- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **macOS / Linux / Git Bash:**
  ```bash
  cp .env.example .env
  ```

Open `.env` in an editor and configure your LLM settings:
```ini
# LLM Provider: "anthropic", "openai", or leave blank for mock mode
LLM_PROVIDER=anthropic
LLM_API_KEY=your_api_key_here
LLM_MODEL=claude-sonnet-4-5

# Backend URL used by the frontend
BACKEND_URL=http://localhost:8000
```
> **Tip:** If no `LLM_API_KEY` is provided, CodeForge AI automatically falls back to **Mock LLM mode**, allowing you to test UI and workflows without API costs.

---

### 5. Run the Application

The system requires two processes running: the **FastAPI Backend** and the **Streamlit Frontend**.

#### Option A: Running in Two Separate Terminals (Recommended)

**Terminal 1 — Start the Backend (FastAPI):**
```bash
uvicorn backend.main:app --reload --port 8000
```
*Or using the module syntax:*
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Start the Frontend (Streamlit):**
```bash
streamlit run frontend/app.py
```
*Or using the module syntax:*
```bash
python -m streamlit run frontend/app.py
```

---

#### Option B: Quick Start (Single Command / Background)

- **Windows (PowerShell - starts backend and frontend in separate windows):**
  ```powershell
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn backend.main:app --reload --port 8000"
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "streamlit run frontend/app.py"
  ```

- **macOS / Linux (Background with output):**
  ```bash
  uvicorn backend.main:app --reload --port 8000 & streamlit run frontend/app.py
  ```

---

### 6. Accessing the Application

Once both servers are running:

| Service | URL | Description |
|---|---|---|
| **Frontend Web IDE** | [http://localhost:8501](http://localhost:8501) | Main user interface (Code editor, terminal, AI chat, agent) |
| **Backend API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger UI documentation |
| **Backend Health Check** | [http://localhost:8000/api/health](http://localhost:8000/api/health) | API and LLM status verification |

---

### 7. Running Tests

Run the test suite with `pytest`:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test suite
pytest tests/test_execution.py
pytest tests/test_agent.py
pytest tests/test_rag_indexing.py
```

---

### 8. Project Structure

```text
├── backend/
│   ├── main.py              # FastAPI application entrypoint
│   ├── config.py            # Environment & application settings
│   ├── security.py          # Path validation & sandbox controls
│   ├── logging_config.py    # Structured logging setup
│   ├── agent/               # Autonomous ReAct agent (tools, planner, patch)
│   ├── ai/                  # LLM integrations & context router
│   ├── execution/           # Code execution runners (Python, JS, Java)
│   ├── models/              # Pydantic schemas
│   ├── rag/                 # Chunker, embeddings, indexer, ChromaDB retriever
│   └── routes/              # FastAPI endpoints (/code, /project, /ai, /agent)
├── frontend/
│   ├── app.py               # Streamlit application entrypoint
│   ├── components/          # UI modules (editor, chat, terminal, agent, sidebar)
│   └── services/            # Backend API client
├── tests/                   # Automated pytest suites
├── requirements.txt         # Project dependencies
└── README.md                # Documentation
```