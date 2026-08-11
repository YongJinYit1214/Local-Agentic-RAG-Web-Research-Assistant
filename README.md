# EvidenceDocs

EvidenceDocs is a seeded PDF RAG research assistant built with Next.js, FastAPI, vLLM, ChromaDB, SQLite, Tavily, and LangGraph.

The goal is to demonstrate a full-stack AI assistant that answers only from seeded or uploaded PDFs by default. If the active PDFs cannot answer a question, the assistant says it cannot answer from the available evidence. It uses web search only when Web Search Mode is enabled or the user explicitly writes `web search`.

## Core Capabilities

- Local LLM chat through vLLM OpenAI-compatible serving.
- Token-by-token streaming from FastAPI to Next.js.
- Layered chat memory with recent messages, session summaries, and structured user memories.
- Session-scoped uploaded documents.
- Seed PDF pack for repeatable demos.
- Hybrid RAG retrieval over seeded PDFs and uploaded documents.
- Tavily web search for online/current information.
- Deterministic LangGraph routing instead of letting the LLM randomly choose tools.
- Structured JSON groundedness verification with Pydantic validation.
- Source and citation display for document chunks and web links.
- Delete chat sessions and uploaded documents from the UI.

## Technology Stack

| Layer | Tool |
| --- | --- |
| Frontend | Next.js + TypeScript |
| Backend | FastAPI |
| Local LLM serving | vLLM OpenAI-compatible server |
| Chat model | `Qwen/Qwen3-4B-Instruct-2507-FP8` |
| Embedding model | `BAAI/bge-small-en-v1.5` via vLLM `/v1/embeddings` |
| Vector DB | ChromaDB |
| Keyword index | SQLite `keyword_chunks` table + BM25 |
| Chat DB | SQLite |
| Memory DB | SQLite structured memory + Chroma semantic summary index |
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
  +--> SQLite memory
  |       recent messages
  |       session summary
  |       relevant structured memories
  |       follow-up query rewrite
  |
  +--> Hybrid RAG retrieval over shared seed PDFs + current-session uploads
  |       semantic search: ChromaDB + vLLM embeddings
  |       keyword search: SQLite keyword chunk index + BM25 with IDF
  |       merge: Reciprocal Rank Fusion
  |       rerank: relevance scoring
  |       confidence: RRF + rerank + coverage + diversity
  |
  +--> LangGraph deterministic router
  |       CHAT / RAG / WEB_SEARCH / RAG_WEB
  |
  +--> Optional Tavily web search
  |
  +--> vLLM /v1/chat/completions streaming
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
Memory system:
  - loads recent messages
  - retrieves relevant memories only
  - rewrites follow-up questions into standalone retrieval queries
  |
  v
Hybrid RAG checks:
  - pre-indexed shared seed PDFs
  - uploaded docs for this session only
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
vLLM generates answer
  |
  v
Backend streams tokens
  |
  v
Backend saves assistant response
```

## Session-Scoped Documents

Uploaded documents are scoped to the active `session_id`.

This is important because a user may upload different files in different chats. EvidenceDocs should not answer a new chat using old documents from a previous chat.

Behavior:

- Uploading a file stores chunks with metadata:
  - `session_id`
  - `document`
  - `page`
  - `chunk`
- Each chunk is written to both retrieval indexes:
  - ChromaDB for semantic vector similarity
  - SQLite `keyword_chunks` for BM25 keyword retrieval
- RAG retrieval searches uploaded documents for the active `session_id` plus the shared seed corpus stored under `session_id="__seed__"`.
- `GET /documents?session_id=...` only lists files for that chat.
- `DELETE /documents/{document_name}?session_id=...` deletes that file only for that chat.
- `DELETE /documents?session_id=...` clears documents for that chat.
- Legacy chunks without `session_id` are cleaned on backend startup.

## Seed PDF Pack

EvidenceDocs includes a seed PDF pack for repeatable demos. The seed PDFs are stored in:

```text
backend/seeds/pdfs
```

Current seed PDFs:

- `101 Memory.pdf`
- `102 The Memory Hierarchy.pdf`
- `103 Virtual Memory.pdf`
- `104 Memory Management - Partitioning.pdf`
- `105 Memory Management - Paging.pdf`
- `106 Memory Management - Segmentation.pdf`
- `ai_internship_requirements.pdf`

The current demo seed pack contains memory-management lecture PDFs plus an AI internship requirements PDF.

Seed PDFs are not indexed per chat. They are manually pre-indexed once into the shared retrieval indexes under the seed namespace:

```text
session_id="__seed__"
source_type="seed"
```

Pre-indexing writes the same chunks into:

- ChromaDB, for semantic vector search.
- SQLite `keyword_chunks`, for BM25 keyword search.

Every chat can retrieve from this shared seed corpus, but the frontend does not show seed PDFs in the uploaded document strip. The strip is reserved for user-uploaded files only.

This gives a predictable demo:

```text
Pre-index seed PDFs once into ChromaDB + SQLite BM25 index
  |
  v
New chat
  |
  v
Ask questions about the seeded PDFs
```

If the question cannot be answered from the seeded or uploaded PDFs, EvidenceDocs refuses to answer unless web search is enabled or triggered.

## Company-Controlled Seed Corpus

The seed PDF pack is designed to be company-configurable.

In a real company deployment, the company owns the seed corpus. That means the organization decides which PDFs EvidenceDocs should trust as the default knowledge base.

Examples of company seed documents:

- onboarding guides
- internal policy manuals
- product documentation
- job descriptions
- compliance guidelines
- engineering standards
- customer support playbooks
- API documentation
- HR benefits documents
- security procedures

This is useful because EvidenceDocs is not trying to be a general chatbot. It is designed to be a controlled document-grounded assistant.

### Why Company-Controlled Seeds Matter

The seed corpus gives the company control over:

- what the assistant is allowed to know by default
- which documents are considered trusted evidence
- when the assistant should refuse to answer
- what sources are cited in responses
- how often the knowledge base is updated

This makes the system safer than a generic assistant because answers are grounded in approved documents.

### How To Replace The Seed Corpus

To customize EvidenceDocs for another company or domain:

1. Delete or archive the demo PDFs in:

```text
backend/seeds/pdfs
```

2. Add the company's own PDFs to the same folder.

Example:

```text
backend/seeds/pdfs/company_onboarding_guide.pdf
backend/seeds/pdfs/security_policy.pdf
backend/seeds/pdfs/product_api_manual.pdf
backend/seeds/pdfs/hr_benefits_handbook.pdf
```

3. Start the vLLM embedding server.

4. Rebuild the shared seed index:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.preindex_seeds --reset
```

The pre-index command calls the embedding server because PDFs must be converted into vectors before they can be stored in ChromaDB. If `http://localhost:8002/v1` is not running with `BAAI/bge-small-en-v1.5`, the command stops before modifying the index and tells you to start the embedding server first.

5. Restart the backend and frontend.

No frontend code change is required.

### Important Behavior

Seed PDFs are available to RAG after pre-indexing, but they are hidden from the visible uploaded-document strip in the UI.

Reason:

- Seed PDFs are the system's default company knowledge base.
- The document strip is reserved for user-uploaded temporary documents.
- This keeps the UI clean while still allowing the assistant to answer from company-approved sources.

### Updating Seed PDFs

If a company changes a seed PDF, rebuild the shared seed index.

Recommended operational workflow:

```text
Update PDFs in backend/seeds/pdfs
  |
  v
Start vLLM embedding server
  |
  v
Run python -m app.preindex_seeds --reset
  |
  v
Restart backend/frontend
  |
  v
All chats retrieve the updated shared seeds
```

### Governance Model

EvidenceDocs separates knowledge into two layers:

| Layer | Purpose | Visible In UI |
| --- | --- | --- |
| Seed PDFs | Company-approved default knowledge base | No |
| Uploaded files | Temporary user-provided documents for the current chat | Yes |

This makes the assistant suitable for demos where the system must answer from controlled sources but still allow the user to upload extra context.

### Example Company Use Case

Suppose a company wants an internal HR assistant.

The company can place these files in `backend/seeds/pdfs`:

```text
employee_handbook.pdf
leave_policy.pdf
benefits_guide.pdf
remote_work_policy.pdf
```

Then employees can ask:

```text
How many annual leave days do I get?
```

If the answer exists in the seed PDFs, EvidenceDocs answers with citations.

If the answer does not exist, EvidenceDocs says it cannot answer from the available PDFs.

If Web Search Mode is enabled, the assistant can use online information, but this is a deliberate user-controlled action.

## Hybrid RAG Retrieval

EvidenceDocs uses hybrid RAG inside the `RAG` route.

Hybrid RAG here means:

```text
semantic search + keyword search + rank fusion
```

It does not mean "RAG plus web search." RAG plus web search is handled by the separate `RAG_WEB` route.

EvidenceDocs does not use two vector databases. It uses two different retrieval indexes over the same chunks:

| Index | Storage | Purpose |
| --- | --- | --- |
| Semantic index | ChromaDB | Finds chunks by embedding similarity and meaning |
| Keyword index | SQLite `keyword_chunks` table | Feeds BM25 exact-term search |

Both indexes store the same chunk IDs. This lets the backend merge semantic and keyword results reliably without guessing whether two results refer to the same source text.

### Step 1: Chunk Documents

Uploaded PDFs, TXT, and Markdown files are extracted into text, cleaned, and split using a parent-child chunking strategy.

Current chunking method:

```text
parent chunk: 1200 tokens/words
child chunk: 420 tokens/words
child overlap: 80 tokens/words
```

Retrieval searches child chunks because smaller chunks improve precision. Generation receives the larger parent chunk stored in metadata because parent context gives the LLM enough surrounding information to answer completely.

Each child chunk is stored in two places:

1. ChromaDB, with the embedding vector and metadata.
2. SQLite `keyword_chunks`, with raw chunk text and metadata for BM25.

Both rows use the same generated `chunk_id`.

Chunk metadata:

```text
session_id
source_type
document
page
parent
chunk
parent_text
```

This means upload indexing and seed pre-indexing follow the same method. There is no special hidden retrieval path for seeds.

### Step 2: Semantic Search

The user query is embedded using the vLLM embedding server:

```text
BAAI/bge-small-en-v1.5
```

Then ChromaDB performs vector similarity search over:

- the shared seed namespace: `session_id="__seed__"`
- the current chat upload namespace: `session_id=<active_session_id>`

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

EvidenceDocs also performs BM25 keyword retrieval over the SQLite `keyword_chunks` table.

The keyword search scope is the same as semantic search:

- shared seed chunks
- uploaded chunks for the active chat only

BM25 uses term frequency and inverse document frequency, so rare important terms are rewarded more strongly than common words.

```text
BM25(query, chunk) = IDF(term) * term-frequency normalization
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

The fused top chunks are sent to the vLLM chat model as context.

Sources include retrieval details such as:

```text
RRF: 0.0325; semantic rank: 2; keyword rank: 1
```

This helps explain why a chunk was selected.

### Step 6: Rerank Fused Candidates

After RRF, EvidenceDocs reranks fused candidates before sending them to the LLM.

Current reranker:

```text
deterministic heuristic reranker
```

It scores each candidate from 0 to 5 using:

- query term coverage in the child chunk
- query term coverage in the parent chunk
- whether the chunk appeared in semantic results
- whether the chunk appeared in BM25 results
- a bonus when both semantic and BM25 agree

The system keeps the best chunks after reranking. This is designed as a local-first demo reranker and can later be replaced by a cross-encoder or LLM judge.

### Step 7: Retrieval Confidence

Retrieval confidence is no longer based only on whether chunks exist.

EvidenceDocs computes:

```text
retrieval_confidence =
    0.4 * normalized_rrf_score
  + 0.3 * reranker_score
  + 0.2 * query_term_coverage
  + 0.1 * source_diversity
```

Thresholds:

```text
confidence >= 0.75: strong document match
0.45 - 0.75: weak/medium document match
confidence < 0.45: no reliable document grounding
```

## Agentic Routing Policy

EvidenceDocs uses LangGraph for routing, but the route decision is deterministic and signal-based.

The LLM does not randomly decide whether to use web search or documents.

The router evaluates these signals:

| Signal | Meaning |
| --- | --- |
| `web_search_mode` | User explicitly enabled web search in the UI |
| `explicit_web_intent` | Message contains the exact phrase `web search` |
| `freshness_need` | Message asks for latest/current/today/news/price/schedule/release/policy updates. This is tracked for explanation, but it does not trigger web search by itself. |
| `document_intent` | Message references uploaded files, PDFs, reports, pages, citations, or "this file" |
| `analytical_depth` | Message asks to compare, evaluate, explain, recommend, or reason |
| `retrieval_confidence` | Hybrid RAG returned usable chunks for the active session |
| `strong_document_match` | Retrieval confidence is high enough to ground the answer |

## Routes

### `CHAT`

Used when:

- No uploaded document evidence is relevant.
- Web Search Mode is off and the user did not write `web search`.
- The system should refuse to answer from general knowledge.

Example:

```text
What's the weather now?
```

In this route, EvidenceDocs returns a grounded refusal:

```text
I can't answer that from the uploaded or seeded PDFs in this chat.
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
- The user explicitly includes the phrase `web search`.

Example:

```text
Use web search for the latest AI regulation news.
```

### `RAG_WEB`

Used when both uploaded documents and web information are needed.

Example:

```text
Use web search to compare this uploaded AI policy with the latest AI regulation news.
```

This route combines:

- session-scoped hybrid RAG results
- Tavily web search results

## Routing Decision Policy

The route is selected using an explainable decision policy. This is easier to test and explain than asking the LLM to choose tools.

Simplified version:

```python
if web_search_mode or explicit_web_intent:
    if retrieval_confidence >= 0.45:
        route = "RAG_WEB"
    else:
        route = "WEB_SEARCH"

elif freshness_need:
    if retrieval_confidence >= 0.45:
        route = "RAG"
    else:
        route = "CHAT"

elif document_intent:
    if retrieval_confidence >= 0.45:
        route = "RAG"
    else:
        route = "CHAT"

elif retrieval_confidence >= 0.75:
    route = "RAG"

else:
    route = "CHAT"
```

The backend streams the chosen route, confidence score, and rationale to the frontend.

## Evaluation

EvidenceDocs includes a small evaluation scaffold in:

```text
backend/evaluation/eval_cases.json
backend/evaluation/run_eval.py
```

Run it from `backend`:

```powershell
.\.venv\Scripts\python -m evaluation.run_eval
```

Current evaluation focuses on routing accuracy. The recommended next benchmark should include:

- 20 document questions
- 10 web questions
- 10 chat questions
- 10 mixed RAG plus web questions

Recommended metrics:

| Metric | Purpose |
| --- | --- |
| Route accuracy | Measures whether the router selected CHAT, RAG, WEB_SEARCH, or RAG_WEB correctly |
| Recall@5 | Measures whether relevant chunks appear in the top 5 retrieved chunks |
| MRR | Measures how early the first relevant chunk appears |
| nDCG@5 | Measures ranking quality when relevance has graded scores |
| Citation accuracy | Measures whether cited sources actually support the answer |
| Faithfulness | Measures whether factual claims are grounded in retrieved evidence |
| Latency | Measures the speed trade-off of reranking and verification |

Example comparison table for a future report:

| Retrieval Method | Recall@5 | MRR |
| --- | ---: | ---: |
| Semantic only | 0.72 | 0.61 |
| BM25 only | 0.68 | 0.57 |
| Semantic + BM25 + RRF | 0.84 | 0.73 |
| RRF + reranker | 0.90 | 0.81 |

## Grounded Answer Verification

EvidenceDocs uses a structured internal LLM step for grounded answer verification.

The final chat answer is still streamed as normal text. The JSON requirement is used in an internal judge step after generation:

```text
question + answer + retrieved evidence + sources
  |
  v
vLLM structured output / JSON schema
  |
  v
Pydantic validation
  |
  v
supported / partially_supported / unsupported
```

Implemented file:

```text
backend/app/services/structured_llm.py
```

The verifier must return this Pydantic shape:

```python
class GroundednessVerdict(BaseModel):
    verdict: Literal["supported", "partially_supported", "unsupported"]
    confidence: float
    unsupported_claims: list[str]
    reason: str
```

Method:

- The backend calls vLLM `/v1/chat/completions` with `stream: false`.
- The request includes `guided_json: GroundednessVerdict.model_json_schema()` plus JSON response mode.
- The prompt still explicitly says to return only JSON.
- The response is parsed and validated with Pydantic.
- If parsing or validation fails, the backend retries and includes the validation error.
- After repeated JSON failures, a deterministic evidence-overlap fallback checks the answer against retrieved source text so parser failures do not get mislabeled as unsupported evidence.

This gives the project a clear structured-output component without letting the LLM make risky routing/tool decisions.

## Web Search Method

EvidenceDocs uses Tavily for reliable web search.

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

EvidenceDocs uses layered memory instead of blindly injecting the full transcript.

Tables:

- `sessions`
- `messages`
- `session_memories`
- `user_memories`

### Memory Layers

| Layer | Storage | Purpose |
| --- | --- | --- |
| Recent messages | SQLite `messages` | Handles immediate conversation flow |
| Session summary | SQLite `session_memories` | Keeps compact context for the current chat |
| Structured user memory | SQLite `user_memories` | Stores durable preferences, goals, projects, and stable facts |
| Semantic memory summaries | ChromaDB `evidencedocs_memory_summaries` | Retrieves related past-session summaries for fuzzy recall |

### Runtime Flow

```text
User sends message
  |
  v
Save raw user message
  |
  v
Load memory context:
  - recent messages
  - current session summary
  - relevant structured memories
  - related semantic memory summaries
  |
  v
Rewrite follow-up question if needed
  |
  v
Run deterministic routing + RAG/web retrieval
  |
  v
Stream answer
  |
  v
Save assistant message
  |
  v
Background memory update
```

### Relevance Gate

EvidenceDocs does not inject every stored memory into every prompt.

Memory storage is hybrid:

- SQLite stores precise structured facts such as preferences, goals, and project names.
- ChromaDB stores embeddings of compact session summaries for fuzzy recall across sessions.

The memory gate filters by:

- current message terms
- semantic similarity over compact session summaries
- memory type
- confidence
- sensitivity
- whether the current message is a follow-up

Only a small number of relevant memories are included.

### Follow-Up Query Rewrite

Memory helps convert vague follow-ups into standalone retrieval queries.

Example:

```text
Previous topic: memory-management PDFs
User: can u explain it more briefly?
Standalone retrieval query: Briefly explain what the memory-management PDFs are about.
```

The rewritten query is used for RAG retrieval and routing. The final answer still cites PDFs or web sources.

### Important Safety Rule

Memory is not evidence.

Memory can help interpret what the user means, but it cannot be used as the factual source for an answer. For normal mode, factual claims still need retrieved PDF evidence. For online claims, Web Search Mode or the exact phrase `web search` is still required.

### Memory Extraction

After a response completes, a background memory updater asks the local vLLM model for structured JSON:

```json
{
  "session_summary": "Compact summary of the current chat.",
  "memories": [
    {
      "memory_type": "project",
      "key": "current_project",
      "value": "Building EvidenceDocs, a local RAG assistant.",
      "confidence": 0.8,
      "sensitivity": "normal",
      "expires_in_days": null
    }
  ]
}
```

The extractor is instructed not to store facts copied from PDFs or web results as user memory. Those facts belong in retrieval sources, not memory.

### User Control

The frontend sidebar includes a Memory panel. The user can:

- view saved memories
- delete one memory
- clear all memories

This prevents silent memory drift and makes mistakes correctable.

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
| `verification` | Sends the structured groundedness verdict returned by the JSON verifier |
| `sources` | Sends final citations and links |
| `done` | Marks response completion |
| `error` | Sends readable error message |

## API Reference

### `GET /health`

Checks FastAPI.

### `GET /health/vllm`

Checks whether the vLLM chat and embedding servers are reachable and whether configured models are served.

### `GET /sessions`

Lists chat sessions.

### `GET /sessions/{session_id}/messages`

Gets messages for a session.

### `DELETE /sessions/{session_id}`

Deletes a chat session and its messages.

### `GET /memory`

Lists stored user memories for the local user.

Returns:

```json
[
  {
    "id": 1,
    "memory_type": "project",
    "memory_key": "current_project",
    "memory_value": "Building EvidenceDocs.",
    "confidence": 0.8,
    "sensitivity": "normal"
  }
]
```

### `DELETE /memory/{memory_id}`

Deletes one stored memory.

### `DELETE /memory`

Clears all stored user memories for the local user.

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

### `POST /documents/seed`

Indexes the built-in seed PDF pack into the shared seed namespace. The recommended approach is the terminal command below, but this endpoint is available for testing/admin use.

Seed PDFs are hidden from the normal `GET /documents?session_id=...` response because that response is used by the frontend uploaded-document strip.

Form fields:

```text
reset
```

Returns:

```json
{
  "documents": [
    {
      "filename": "101 Memory.pdf",
      "status": "indexed",
      "chunks": 3
    }
  ]
}
```

### `GET /documents?session_id=...`

Lists user-uploaded indexed documents for one chat session. Seed PDFs are not shown here even though they are searchable by RAG.

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

### 1. Install and Start vLLM

Install vLLM in WSL/Linux with a supported NVIDIA GPU/CUDA setup.

On the RTX 4060 Laptop GPU used for this project, the stable local setup is:

```powershell
wsl -d Ubuntu
python3 -m venv ~/vllm-env
source ~/vllm-env/bin/activate
pip install vllm==0.8.5
pip install transformers==4.51.3 tokenizers==0.21.4 numpy==2.2.6
```

Recommended Windows startup:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\start_vllm_windows.ps1
```

This runs the shared WSL vLLM launcher in the current terminal:

- `Qwen/Qwen3-4B-Instruct-2507-FP8` chat on port `8001`
- `BAAI/bge-small-en-v1.5` embeddings on port `8002`

Keep this terminal open while using EvidenceDocs.

Alternative manual WSL startup:

```powershell
wsl -d Ubuntu
bash "/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/start_vllm_servers.sh"
```

That command intentionally keeps the WSL terminal open. Start FastAPI and Next.js in separate terminals.

Start one vLLM server only:

```powershell
bash "/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/start_vllm_chat.sh"
bash "/mnt/c/Users/jinyi/OneDrive/Desktop/stock research/backend/start_vllm_embed.sh"
```

The chat model is intentionally `Qwen/Qwen3-4B-Instruct-2507-FP8`, not a 7B model, because it is more suitable for an 8 GB laptop GPU. The server starts with a 4096-token context and one concurrent sequence so the backend can request up to 2048 response tokens.

The embedding model remains `BAAI/bge-small-en-v1.5`. In this local vLLM install, CPU serving is not supported, so the embedding server also runs through vLLM on the GPU.

Check vLLM:

```powershell
$headers = @{ Authorization = "Bearer token-local" }
Invoke-RestMethod http://127.0.0.1:8001/v1/models -Headers $headers
Invoke-RestMethod http://127.0.0.1:8002/v1/models -Headers $headers
```

### 2. Configure Backend Environment

Create `backend/.env`:

```env
VLLM_CHAT_BASE_URL=http://localhost:8001/v1
VLLM_EMBED_BASE_URL=http://localhost:8002/v1
VLLM_API_KEY=token-local
VLLM_CHAT_MODEL=Qwen/Qwen3-4B-Instruct-2507-FP8
VLLM_EMBED_MODEL=BAAI/bge-small-en-v1.5
DATABASE_PATH=./data/evidencedocs.sqlite3
CHROMA_PATH=./chroma
RAG_TOP_K=5
WEB_TOP_K=5
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=
```

### 3. Pre-Index Seed PDFs

Before starting the app for a demo, index the seed PDFs once into ChromaDB and the SQLite BM25 keyword index.

The vLLM embedding server on port `8002` must be running first because this command creates embeddings.

From the backend folder:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.preindex_seeds --reset
```

What this does:

- reads PDFs from `backend/seeds/pdfs`
- chunks each PDF
- creates embeddings with `BAAI/bge-small-en-v1.5`
- stores chunks in ChromaDB under `session_id="__seed__"`
- stores the same chunks in SQLite `keyword_chunks` for BM25
- skips repeated per-chat seed indexing

Use `--reset` when seed PDFs changed. Without `--reset`, already-indexed seed PDFs are skipped.

### 4. Start Everything

From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_evidencedocs.ps1
```

This opens three terminals:

- `EvidenceDocs vLLM`
- `EvidenceDocs Backend`
- `EvidenceDocs Frontend`

If you changed backend code, stop the old backend terminal and start again. The backend intentionally does not use auto-reload, so a stale terminal can keep running old code.

Frontend:

```text
http://localhost:3000
```

Backend:

```text
http://localhost:8011/health
```

vLLM through backend:

```text
http://localhost:8011/health/vllm
```

## Manual Backend Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8011
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
http://localhost:8011/health
```

The response should include the current backend build label. If it does not, the browser is still talking to an old backend process.

### Chat shows an old internal error after code changes

Stop the old backend terminal and start it again:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

EvidenceDocs runs FastAPI without auto-reload so it stays stable during demos. That also means code changes are not picked up until the backend is restarted.

The backend startup script now stops any existing process on port `8011` before starting Uvicorn, which prevents stale FastAPI processes from keeping old code alive.

### Backend says "vLLM chat server is not reachable" or "vLLM embedding server is not reachable"

One or both vLLM OpenAI-compatible servers are not running.

Run the chat and embedding servers:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\start_vllm_windows.ps1
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
http://localhost:8011/documents?session_id=YOUR_SESSION_ID
```

### Uploading the same file twice

The backend deletes old chunks for the same filename in the same session before re-indexing the new copy.





