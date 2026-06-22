# LocalMind

A local agentic RAG web research assistant built with Next.js, FastAPI, Ollama, ChromaDB, SQLite, DuckDuckGo Search, and LangGraph-inspired deterministic routing.

## What It Does

- Streams local LLM responses token-by-token from Ollama.
- Answers from uploaded PDFs and text files using RAG.
- Stores chat sessions and message history in SQLite.
- Uses DuckDuckGo web search only when Web Search Mode is enabled or the user explicitly asks for current online information.
- Returns document citations and web links as sources.
- Keeps routing deterministic instead of letting the LLM randomly decide when to browse.

## Stack

| Layer | Tool |
| --- | --- |
| Frontend | Next.js + TypeScript |
| Backend | FastAPI |
| Local LLM | Ollama |
| Suggested models | `llama3.1:8b`, `qwen2.5:7b`, `mistral:7b` |
| Embedding | `nomic-embed-text` via Ollama |
| Vector DB | ChromaDB |
| Chat DB | SQLite |
| Web Search | DuckDuckGo Search |
| Agent Flow | Deterministic router, LangGraph-ready |

## Prerequisites

Install Ollama, then pull one chat model and the embedding model:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## API

### `POST /chat/stream`

Payload:

```json
{
  "session_id": "session_001",
  "message": "Search the web for latest AI regulation news",
  "web_search_mode": true
}
```

Response: `text/event-stream`

Events:

- `status`
- `token`
- `sources`
- `done`
- `error`

### `POST /documents/upload`

Uploads a PDF or text file, chunks it, embeds it with Ollama `nomic-embed-text`, and stores chunks in ChromaDB.

## Deterministic Routing Rule

```python
if web_search_mode:
    route = "WEB_SEARCH"
elif user_message contains ["search web", "latest", "current", "today", "online", "look up"]:
    route = "WEB_SEARCH"
elif uploaded docs are relevant:
    route = "RAG"
else:
    route = "CHAT"
```

## Git Remote

This local repository is linked to:

```text
https://github.com/YongJinYit1214/Local-Agentic-RAG-Web-Research-Assistant.git
```
