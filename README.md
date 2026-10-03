CodeForge AI — AI-Powered Mini IDE

A browser-based development environment that combines code editing, multi-language execution, repository-aware RAG, AI-assisted debugging, and a controlled autonomous coding agent.

Overview

CodeForge AI is an AI-assisted development environment designed to bring coding, execution, repository search, debugging, and code modification into a single workflow.

Unlike a conventional chatbot where developers manually copy code and error messages into a separate interface, CodeForge AI can work with the active editor, terminal output, and indexed project files. This allows the AI to provide context-aware assistance and, when the autonomous agent is enabled, investigate, reproduce, propose, apply, and verify code changes through a human approval step.

Key Capabilities

Web-based code editor with syntax highlighting and multi-language support.

Python, JavaScript, and Java execution through controlled subprocesses.

Repository-aware RAG using local embeddings and ChromaDB.

Incremental project indexing using SHA-256 file hashes.

Context-aware AI assistance for general questions, current code, errors, and project-level questions.

Autonomous ReAct coding agent with an explicit tool allowlist.

Human approval before file modifications through generated diffs.

Automatic backups and rollback for approved changes.

Post-change verification by executing the modified code.

Mock LLM mode for local evaluation without an API key.

Architecture

CodeForge AI follows a client-server architecture with a Streamlit frontend and FastAPI backend.

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
                         │       FastAPI Backend        │
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

Main Components

Layer

Technology

Responsibility

Frontend

Streamlit

Web IDE, editor, chat, terminal, project explorer, agent interface

Code Editor

Streamlit-Ace

Source editing and syntax highlighting

API

FastAPI

REST API, request validation, routing

Server

Uvicorn

ASGI application server

Validation

Pydantic

API request and response schemas

RAG

ChromaDB

Local vector storage and semantic retrieval

Embeddings

Sentence-Transformers

Code/query embeddings using all-MiniLM-L6-v2

LLM

Anthropic / OpenAI / Mock

AI reasoning and code assistance

Execution

Python Subprocess / Node / Java

Multi-language code execution

Configuration

python-dotenv

Environment-based configuration

Testing

Pytest

Automated test suite