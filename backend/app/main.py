import json
import asyncio
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import db
from app.db import delete_session, get_messages, list_sessions, save_message
from app.memory import (
    MemoryContext,
    delete_session_memory_vector,
    is_follow_up_message,
    load_memory_context,
    rewrite_query_for_retrieval,
    update_memory_after_turn,
)
from app.prompts import build_messages
from app.preindex_seeds import preindex_seed_documents
from app.rag import clear_documents, clear_legacy_documents, delete_document, ingest_document, list_indexed_documents, retrieve
from app.agent_graph import choose_route_with_graph
from app.schemas import ChatStreamRequest
from app.services.structured_llm import verify_grounded_answer
from app.vllm_client import VllmUnavailableError, check_vllm, stream_chat
from app.web_search import web_search

APP_BUILD = "memory-system-2026-08-11"

app = FastAPI(title="EvidenceDocs API")

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
    Path("./seeds/pdfs").mkdir(parents=True, exist_ok=True)
    clear_legacy_documents()


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def document_like_request(message: str) -> bool:
    text = message.lower()
    return any(term in text for term in ("pdf", "document", "file", "uploaded", "source", "citation", "page"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "build": APP_BUILD}


@app.get("/health/vllm")
async def vllm_health():
    return await check_vllm()


@app.get("/sessions")
def sessions():
    return list_sessions()


@app.get("/sessions/{session_id}/messages")
def messages(session_id: str):
    return get_messages(session_id, limit=100)


@app.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    delete_session(session_id)
    delete_session_memory_vector(session_id)
    return {"deleted": session_id}


@app.get("/memory")
def list_memory(user_id: str = Query(default="local_user")):
    return db.list_user_memories(user_id)


@app.delete("/memory")
def clear_memory(user_id: str = Query(default="local_user")):
    return {"deleted": db.clear_user_memories(user_id)}


@app.delete("/memory/{memory_id}")
def remove_memory(memory_id: int, user_id: str = Query(default="local_user")):
    deleted = db.delete_user_memory(memory_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"deleted": memory_id}


@app.get("/documents")
async def documents(session_id: str | None = Query(default=None)):
    return list_indexed_documents(session_id)


@app.delete("/documents")
def remove_all_documents(session_id: str | None = Query(default=None)):
    deleted_chunks = clear_documents(session_id)
    return {"deleted_chunks": deleted_chunks}


@app.delete("/documents/{document_name}")
def remove_document(document_name: str, session_id: str | None = Query(default=None)):
    deleted_chunks = delete_document(document_name, session_id)
    return {"document": document_name, "deleted_chunks": deleted_chunks}


@app.post("/documents/upload")
async def upload_document(session_id: str = Form(...), file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Only PDF, TXT, and MD files are supported.")

    upload_dir = Path("./data/uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / Path(file.filename or "document").name
    content = await file.read()
    delete_document(upload_path.name, session_id)
    upload_path.write_bytes(content)
    chunks = await ingest_document(upload_path, session_id, source_type="upload")
    return {"filename": upload_path.name, "chunks": chunks}


@app.post("/documents/seed")
async def load_seed_documents(reset: bool = Form(default=False)):
    loaded = await preindex_seed_documents(Path("./seeds/pdfs"), reset=reset)
    return {"documents": loaded}


@app.post("/chat/stream")
async def chat_stream(payload: ChatStreamRequest):
    async def generate() -> AsyncIterator[str]:
        assistant_text = ""
        try:
            history = get_messages(payload.session_id)
            memory_context = await load_memory_context(payload.session_id, payload.message)
            if is_follow_up_message(payload.message) and not any(row["role"] == "assistant" for row in history):
                memory_context = MemoryContext(session_summary="", related_summaries=[], memories=[])
            memory_text = memory_context.render()
            save_message(payload.session_id, "user", payload.message)
            explicit_web_request = "web search" in payload.message.lower()
            should_search_documents = (
                not payload.web_search_mode and not explicit_web_request
            ) or document_like_request(payload.message)
            if not should_search_documents:
                retrieval_message = payload.message
                contexts = []
                rag_sources = []
                route_state = choose_route_with_graph(payload.message, payload.web_search_mode, 0, 0, 0)
            else:
                retrieval_message = await rewrite_query_for_retrieval(payload.message, history, memory_context)
                yield sse("status", {"message": "Searching documents..."})
                contexts, rag_sources, retrieval_signals = await retrieve(retrieval_message, payload.session_id)
                route_state = choose_route_with_graph(
                    retrieval_message,
                    payload.web_search_mode,
                    retrieval_signals.confidence,
                    retrieval_signals.max_query_term_coverage,
                    retrieval_signals.keyword_match_count,
                )
            route = route_state["route"]

            context: list[str] | str | None = contexts
            sources = rag_sources
            if route == "RAG_WEB":
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
                yield sse("status", {"message": "No grounded document answer found."})

            yield sse(
                "route",
                {
                    "route": route,
                    "confidence": route_state["confidence"],
                    "rationale": route_state["rationale"],
                    "signals": route_state["signals"],
                },
            )
            if route == "CHAT":
                assistant_text = (
                    "I can't answer that from the uploaded or seeded PDFs in this chat. "
                    "Upload a relevant PDF or enable Web Search Mode if you want me to use online information."
                )
                yield sse("token", {"token": assistant_text})
                save_message(payload.session_id, "assistant", assistant_text)
                asyncio.create_task(
                    update_memory_after_turn(
                        session_id=payload.session_id,
                        user_message=payload.message,
                        assistant_answer=assistant_text,
                        history=history,
                    )
                )
                yield sse("sources", {"sources": []})
                yield sse("done", {"message": "complete"})
                return

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
            asyncio.create_task(
                update_memory_after_turn(
                    session_id=payload.session_id,
                    user_message=payload.message,
                    assistant_answer=assistant_text,
                    history=history,
                )
            )

            yield sse("status", {"message": "Verifying groundedness with structured JSON..."})
            verification = await verify_grounded_answer(
                question=payload.message,
                answer=assistant_text,
                context=context,
                sources=sources,
                memory_context=memory_text,
            )
            yield sse("verification", {"verification": verification.model_dump()})

            yield sse("sources", {"sources": [source.model_dump() for source in sources]})
            yield sse("done", {"message": "complete"})
        except VllmUnavailableError as exc:
            yield sse("error", {"message": str(exc)})
        except Exception as exc:
            yield sse("error", {"message": str(exc)})

    return StreamingResponse(generate(), media_type="text/event-stream")
