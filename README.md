# LocalMind

LocalMind is a local agentic hybrid RAG web research assistant built with Next.js, FastAPI, Ollama, ChromaDB, SQLite, Tavily, and LangGraph.

The goal is to demonstrate a full-stack AI assistant that can answer from uploaded documents, remember chat history, stream responses token-by-token, and use web search only when the system deterministically decides it is appropriate.

## Core Capabilities

- Local LLM chat through Ollama.
- Token-by-token streaming from FastAPI to Next.js.
- Session-based chat memory stored in SQLite.
- Session-scoped uploaded documents.
- Hybrid RAG retrieval over uploaded documents.
- Tavily web search for online/current information.
- Deterministic LangGraph routing instead of letting the LLM randomly choose tools.
- Source and citation display for document chunks and web links.
- Delete chat sessions and uploaded documents from the UI.

## Technology Stack

| Layer | Tool |
| --- | --- |
| Frontend | Next.js + TypeScript |
| Backend | FastAPI |
| Local LLM | Ollama |
| Chat model | `llama3.1:8b` |
| Embedding model | `nomic-embed-text` via Ollama |
| Vector DB | ChromaDB |
| Chat DB | SQLite |
| Web Search | Tavily |
| Agent Routing | LangGraph |

## System Architecture

```text
User
  |
  v
Next.js Chat UI
  |  sends message, session_id, web_search_mode
  v
FastAPI /chat/stream
  |
  +--> SQLite memory: save/load messages
  |
  +--> Hybrid RAG retrieval for current session
  |       semantic search: ChromaDB + Ollama embeddings
  |       keyword search: local BM25-style scoring
  |       merge: Reciprocal Rank Fusion
  |
  +--> LangGraph deterministic router
  |       CHAT / RAG / WEB_SEARCH / RAG_WEB
  |
  +--> Optional Tavily web search
  |
  +--> Ollama /api/chat streaming
  |
  v
Server-Sent Events back to Next.js
```

## Main User Flow

```text
User asks a question
  |
  v
Frontend sends:
  - session_id
  - message
  - web_search_mode
  |
  v
Backend saves user message
  |
  v
Hybrid RAG checks uploaded docs for this session only
  |
  v
Router decides route
  |
  +--> CHAT
  +--> RAG
  +--> WEB_SEARCH
  +--> RAG_WEB
  |
  v
Ollama generates answer
  |
  v
Backend streams tokens
  |
  v
Backend saves assistant response
```

## Session-Scoped Documents

Uploaded documents are scoped to the active `session_id`.

This is important because a user may upload different files in different chats. LocalMind should not answer a new chat using old documents from a previous chat.

Behavior:

- Uploading a file stores chunks with metadata:
  - `session_id`
  - `document`
  - `page`
  - `chunk`
- RAG retrieval filters ChromaDB by the active `session_id`.
- `GET /documents?session_id=...` only lists files for that chat.
- `DELETE /documents/{document_name}?session_id=...` deletes that file only for that chat.
- `DELETE /documents?session_id=...` clears documents for that chat.
- Legacy chunks without `session_id` are cleaned on backend startup.

## Hybrid RAG Retrieval

LocalMind uses hybrid RAG inside the `RAG` route.

Hybrid RAG here means:

```text
semantic search + keyword search + rank fusion
```

It does not mean "RAG plus web search." RAG plus web search is handled by the separate `RAG_WEB` route.

### Step 1: Chunk Documents

Uploaded PDFs, TXT, and Markdown files are extracted into text, cleaned, and split into overlapping chunks.

Current chunking method:

```text
chunk size: 900 words
overlap: 150 words
```

Each chunk is stored in ChromaDB with metadata.

### Step 2: Semantic Search

The user query is embedded using Ollama:

```text
nomic-embed-text
```

Then ChromaDB performs vector similarity search over chunks for the current session.

Semantic search is useful because it can match meaning even when the exact words differ.

Example:

```text
Question: What skills are needed for the AI internship?
```

Semantic search may find chunks about:

- machine learning
- Python libraries
- model evaluation
- data preprocessing

### Step 3: Keyword Search

LocalMind also performs local keyword scoring over the same session-scoped chunks.

The keyword search uses a simple BM25-style term-frequency formula:

```text
score += tf / (tf + 1.5 + 0.75 * document_length / 120)
```

This catches exact terms that semantic search can miss.

Example exact terms:

- `Experian`
- `AI Intern`
- `NumPy`
- `Pandas`
- `Scikit-learn`
- file names
- package names
- codes

### Step 4: Merge With Reciprocal Rank Fusion

Semantic results and keyword results are merged using Reciprocal Rank Fusion.

Formula:

```text
rrf_score = sum(1 / (k + rank))
```

Current value:

```text
k = 60
```

Why RRF is used:

- It does not require semantic distance and keyword score to be on the same scale.
- It rewards chunks that rank well in either search method.
- It is simple, explainable, and robust for a demo project.

Example:

```text
Chunk A:
  semantic rank = 2
  keyword rank = 1

Chunk B:
  semantic rank = 1
  keyword rank = none
```

Both can be useful, but Chunk A may rank higher because it is strong in both exact keywords and meaning.

### Step 5: Send Top Chunks to the LLM

The fused top chunks are sent to Ollama as context.

Sources include retrieval details such as:

```text
RRF: 0.0325; semantic rank: 2; keyword rank: 1
```

This helps explain why a chunk was selected.

## Agentic Routing Policy

LocalMind uses LangGraph for routing, but the route decision is deterministic and signal-based.

The LLM does not randomly decide whether to use web search or documents.

The router evaluates these signals:

| Signal | Meaning |
| --- | --- |
| `web_search_mode` | User explicitly enabled web search in the UI |
| `explicit_web_intent` | Message says things like "search the web", "find links", or "look up online" |
| `freshness_need` | Message asks for latest/current/today/news/price/schedule/release/policy updates |
| `document_intent` | Message references uploaded files, PDFs, reports, pages, citations, or "this file" |
| `analytical_depth` | Message asks to compare, evaluate, explain, recommend, or reason |
| `retrieval_confidence` | Hybrid RAG returned usable chunks for the active session |
| `strong_document_match` | Retrieval confidence is high enough to ground the answer |

## Routes

### `CHAT`

Used when:

- No uploaded document evidence is relevant.
- No current online information is needed.
- The question can be answered from normal conversation and memory.

Example:

```text
Explain what RAG means in simple terms.
```

### `RAG`

Used when:

- Uploaded documents in the current session are relevant.
- The user asks about "this file", "the uploaded document", "the PDF", or document content.
- Hybrid retrieval returns usable chunks.

Example:

```text
What does this file say in the conclusion?
```

Decision method:

```text
if hybrid_retrieval_returns_chunks and document_intent is present:
    route = RAG
```

### `WEB_SEARCH`

Used when:

- Web Search Mode is enabled.
- The user explicitly asks to search online.
- The question requires current information.

Example:

```text
Search the web for the latest AI regulation news.
```

### `RAG_WEB`

Used when both uploaded documents and current web information are needed.

Example:

```text
Compare this uploaded AI policy with the latest AI regulation news.
```

This route combines:

- session-scoped hybrid RAG results
- Tavily web search results

## Routing Score Logic

The route is selected using weighted scores.

Simplified version:

```python
web_score = 0
if web_search_mode:
    web_score += 1.0
if explicit_web_intent:
    web_score += 0.85
web_score += freshness_need * 0.7
web_score -= document_intent * 0.4

rag_score = retrieval_confidence
rag_score += document_intent * 0.55
if explicit_web_intent or web_search_mode:
    rag_score -= 0.5
if freshness_need and not document_intent:
    rag_score -= 0.25

chat_score = 0.35
chat_score += analytical_depth * 0.2
if no_web_signal and no_document_signal:
    chat_score += 0.25

rag_web_score = 0
if documents_exist and web_or_freshness_signal:
    rag_web_score = retrieval_confidence + freshness_need * 0.55 + document_intent * 0.45
```

The highest score wins.

The backend streams the chosen route, confidence score, and rationale to the frontend.

## Web Search Method

LocalMind uses Tavily for reliable web search.

DuckDuckGo was tested earlier, but it can rate-limit because it uses public endpoints rather than a stable API contract. Tavily is more reliable for demos.

Environment configuration:

```env
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_tavily_key
```

The backend also supports:

```env
SEARCH_PROVIDER=auto
BRAVE_API_KEY=your_brave_key
```

Provider order in `auto` mode:

```text
Tavily -> Brave Search -> DuckDuckGo fallback
```

## Chat Memory

Chat memory is stored in SQLite.

Tables:

- `sessions`
- `messages`

For each message:

- user messages are saved before generation
- assistant messages are saved after streaming completes

When generating a response, the backend loads recent chat history and includes it in the prompt.

## Streaming Method

FastAPI streams responses using Server-Sent Events.

Endpoint:

```text
POST /chat/stream
```

Events:

| Event | Purpose |
| --- | --- |
| `status` | Shows progress such as "Searching documents..." |
| `route` | Shows selected route, confidence, rationale, and signals |
| `token` | Streams assistant text token-by-token |
| `sources` | Sends final citations and links |
| `done` | Marks response completion |
| `error` | Sends readable error message |

## API Reference

### `GET /health`

Checks FastAPI.

### `GET /health/ollama`

Checks whether Ollama is reachable and whether configured models are installed.

### `GET /sessions`

Lists chat sessions.

### `GET /sessions/{session_id}/messages`

Gets messages for a session.

### `DELETE /sessions/{session_id}`

Deletes a chat session and its messages.

### `POST /documents/upload`

Uploads and indexes a document.

Form fields:

```text
session_id
file
```

Supported file types:

```text
.pdf
.txt
.md
```

### `GET /documents?session_id=...`

Lists indexed documents for one chat session.

### `DELETE /documents/{document_name}?session_id=...`

Deletes one document from one chat session.

### `DELETE /documents?session_id=...`

Clears all documents from one chat session.

### `POST /chat/stream`

Streams an assistant response.

Payload:

```json
{
  "session_id": "session_001",
  "message": "What does this file say in conclusion?",
  "web_search_mode": false
}
```

Response:

```text
text/event-stream
```

## Setup

### 1. Install Ollama

Download Ollama:

```text
https://ollama.com/download
```

Pull models:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Check Ollama:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

### 2. Configure Backend Environment

Create `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.1:8b
OLLAMA_EMBED_MODEL=nomic-embed-text
DATABASE_PATH=./data/localmind.sqlite3
CHROMA_PATH=./chroma
RAG_TOP_K=5
WEB_TOP_K=5
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=
```

### 3. Start Everything

From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_localmind.ps1
```

Frontend:

```text
http://localhost:3000
```

Backend:

```text
http://localhost:8000/health
```

Ollama through backend:

```text
http://localhost:8000/health/ollama
```

## Manual Backend Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Manual Frontend Start

```powershell
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Frontend says "Failed to fetch"

FastAPI is probably not running.

Check:

```text
http://localhost:8000/health
```

### Backend says "Ollama is not reachable"

Ollama is not running or the models are not pulled.

Run:

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Then restart the backend.

### Web search fails

Check `backend/.env`:

```env
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_tavily_key
```

Restart backend after changing `.env`.

### RAG answers from an old file

Documents are session-scoped. If this happens:

1. Restart backend so legacy cleanup runs.
2. Click `Clear docs` in the UI.
3. Upload the file again in the active chat.
4. Check:

```text
http://localhost:8000/documents?session_id=YOUR_SESSION_ID
```

### Uploading the same file twice

The backend deletes old chunks for the same filename in the same session before re-indexing the new copy.

## Why This Matches The Full-Stack AI Engineer JD

This project demonstrates:

- Next.js frontend development
- FastAPI backend development
- local LLM integration
- Ollama streaming
- RAG document indexing and retrieval
- hybrid retrieval with semantic search and keyword search
- agentic routing with LangGraph
- deterministic tool selection
- web search integration
- SQLite chat memory
- vector database usage
- SSE streaming
- session-aware state management
- source citation display

## Git Remote

This local repository is linked to:

```text
https://github.com/YongJinYit1214/Local-Agentic-RAG-Web-Research-Assistant.git
```
