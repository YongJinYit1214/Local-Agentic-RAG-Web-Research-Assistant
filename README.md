# LocalMind

A local agentic hybrid RAG web research assistant built with Next.js, FastAPI, Ollama, ChromaDB, SQLite, Tavily, and LangGraph.

## What It Does

- Streams local LLM responses token-by-token from Ollama.
- Answers from uploaded PDFs and text files using hybrid RAG.
- Stores chat sessions and message history in SQLite.
- Uses Tavily web search when Web Search Mode is enabled or the request needs current online context.
- Returns document citations and web links as sources.
- Uses deterministic agentic routing instead of letting the LLM randomly decide which tool to call.

## Stack

| Layer | Tool |
| --- | --- |
| Frontend | Next.js + TypeScript |
| Backend | FastAPI |
| Local LLM | Ollama |
| Suggested models | `llama3.1:8b` |
| Embedding | `nomic-embed-text` via Ollama |
| Vector DB | ChromaDB |
| Chat DB | SQLite |
| Web Search | Tavily |
| Agent Flow | LangGraph deterministic router |

## Prerequisites

Install Ollama from the official site:

https://ollama.com/download

Then pull one chat model and the embedding model:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Check that Ollama is running:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

If the app says `All connection attempts failed`, FastAPI is usually running but Ollama is not. Start Ollama first, then restart the backend.

## Web Search Setup

DuckDuckGo does not need a token, but it is not consistent because it uses public search endpoints that can rate-limit. For a reliable demo, configure a real search API key.

Recommended:

- Tavily: set `TAVILY_API_KEY`
- Brave Search API: set `BRAVE_API_KEY`

Example `backend/.env`:

```env
SEARCH_PROVIDER=auto
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=
```

`SEARCH_PROVIDER=auto` tries Tavily first, then Brave Search, then DuckDuckGo. You can force one provider with `SEARCH_PROVIDER=tavily`, `SEARCH_PROVIDER=brave`, or `SEARCH_PROVIDER=duckduckgo`.

## Quick Start

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_localmind.ps1
```

Health checks:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/health
- Ollama through backend: http://localhost:8000/health/ollama

## Manual Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Manual Frontend

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
- `route`
- `token`
- `sources`
- `done`
- `error`

### `POST /documents/upload`

Uploads a PDF or text file, chunks it, embeds it with Ollama `nomic-embed-text`, and stores chunks in ChromaDB.

### `GET /documents`

Lists indexed documents and chunk counts.

## Hybrid RAG Retrieval

LocalMind uses hybrid RAG inside the `RAG` route. This is different from combining RAG with web search.

Flow:

1. User asks a question.
2. Semantic search uses Ollama embeddings and ChromaDB similarity search.
3. Keyword search uses a local BM25-style term-frequency score over indexed chunks.
4. Results are merged with Reciprocal Rank Fusion.
5. The top chunks are passed to the local LLM with citations.

Why this is better:

- Semantic search understands meaning and related context.
- Keyword search catches exact terms, names, tools, company names, and codes.
- Reciprocal Rank Fusion rewards chunks that rank well in either or both retrieval methods.

Example:

```text
User: What is Experian's AI intern requirement?
```

Semantic search may find chunks about machine learning, model evaluation, and Python AI libraries. Keyword search catches exact words like `Experian`, `AI Intern`, `NumPy`, `Pandas`, and `Scikit-learn`. The merged ranking gives the LLM stronger evidence than either method alone.

## Agentic Routing Policy

LocalMind uses a deterministic LangGraph router, but the decision is based on multiple signals instead of a simple keyword list:

- User control: Web Search Mode allows online search.
- Explicit source intent: requests such as "search the web", "find links", or "look up online" route to web search.
- Freshness requirement: questions about latest/current/news/price/schedule/release/policy updates are treated as external-information requests.
- Document-grounding intent: questions that refer to uploaded PDFs, pages, reports, citations, or "according to the document" prefer RAG.
- Retrieval confidence: uploaded documents are used when hybrid retrieval returns relevant chunks.
- RAG plus web: mixed questions can combine uploaded document evidence with current web context.
- Fallback reasoning: if neither web nor document evidence is strong, the assistant uses normal chat with memory.

Routes:

- `CHAT`
- `RAG`
- `WEB_SEARCH`
- `RAG_WEB`

The router streams the selected route, confidence score, and rationale to the frontend so the demo can explain why each tool path was chosen.

## Git Remote

This local repository is linked to:

```text
https://github.com/YongJinYit1214/Local-Agentic-RAG-Web-Research-Assistant.git
```
