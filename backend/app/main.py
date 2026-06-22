import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import db
from app.db import get_messages, list_sessions, save_message
from app.ollama_client import OllamaUnavailableError, check_ollama, stream_chat
from app.prompts import build_messages
from app.rag import ingest_document, retrieve
from app.agent_graph import choose_route_with_graph
from app.schemas import ChatStreamRequest
from app.web_search import web_search

app = FastAPI(title="LocalMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.init_db()
    Path("./data/uploads").mkdir(parents=True, exist_ok=True)


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ollama")
async def ollama_health():
    return await check_ollama()


@app.get("/sessions")
def sessions():
    return list_sessions()


@app.get("/sessions/{session_id}/messages")
def messages(session_id: str):
    return get_messages(session_id, limit=100)


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and MD files are supported.")

    upload_path = Path("./data/uploads") / Path(file.filename or "document").name
    upload_path.write_bytes(await file.read())
    chunks = await ingest_document(upload_path)
    return {"filename": upload_path.name, "chunks": chunks}


@app.post("/chat/stream")
async def chat_stream(payload: ChatStreamRequest):
    async def generate() -> AsyncIterator[str]:
        assistant_text = ""
        try:
            save_message(payload.session_id, "user", payload.message)
            history = get_messages(payload.session_id)

            yield sse("status", {"message": "Searching documents..."})
            contexts, rag_sources, retrieval_confidence = await retrieve(payload.message)
            route_state = choose_route_with_graph(
                payload.message,
                payload.web_search_mode,
                retrieval_confidence,
            )
            route = route_state["route"]

            context: list[str] | str | None = contexts
            sources = rag_sources
            if route == "HYBRID_RAG_WEB":
                yield sse("status", {"message": "Searching web and documents..."})
                web_context, web_sources = await web_search(payload.message)
                context = [
                    "Uploaded document context:",
                    *contexts,
                    "Web search context:",
                    web_context,
                ]
                sources = [*rag_sources, *web_sources]
            elif route == "WEB_SEARCH":
                yield sse("status", {"message": "Searching web..."})
                context, sources = await web_search(payload.message)
            elif route == "RAG":
                yield sse("status", {"message": "Using uploaded documents..."})
            else:
                yield sse("status", {"message": "Generating answer..."})

            yield sse(
                "route",
                {
                    "route": route,
                    "confidence": route_state["confidence"],
                    "rationale": route_state["rationale"],
                    "signals": route_state["signals"],
                },
            )
            messages_for_llm = build_messages(
                payload.message,
                history,
                route=route,
                context=context,
                sources=sources,
            )

            async for token in stream_chat(messages_for_llm):
                assistant_text += token
                yield sse("token", {"token": token})

            save_message(payload.session_id, "assistant", assistant_text)
            yield sse("sources", {"sources": [source.model_dump() for source in sources]})
            yield sse("done", {"message": "complete"})
        except OllamaUnavailableError as exc:
            yield sse("error", {"message": str(exc)})
        except Exception as exc:
            yield sse("error", {"message": str(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")
