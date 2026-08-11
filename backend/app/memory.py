import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import chromadb
from chromadb.config import Settings as ChromaSettings

from app import db
from app.config import get_settings
from app.vllm_client import VllmUnavailableError, chat_json, embed


LOCAL_USER_ID = "local_user"
MEMORY_COLLECTION_NAME = "evidencedocs_memory_summaries"
MAX_MEMORY_CONTEXT_CHARS = 1200
FOLLOW_UP_TERMS = {
    "it",
    "that",
    "this",
    "they",
    "them",
    "those",
    "again",
    "briefly",
    "shorter",
    "simpler",
}
SENSITIVE_TOPICS = {
    "health",
    "medical",
    "diagnosis",
    "relationship",
    "religion",
    "identity",
    "politics",
    "salary",
    "finance",
    "bank",
    "address",
    "phone",
}
MEMORY_STOPWORDS = {
    "about",
    "again",
    "and",
    "are",
    "can",
    "for",
    "from",
    "how",
    "more",
    "the",
    "this",
    "that",
    "then",
    "what",
    "with",
    "you",
}


class MemoryFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_type: Literal["stable_fact", "preference", "project", "goal", "transient_state"]
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=600)
    confidence: float = Field(default=0.7, ge=0, le=1)
    sensitivity: Literal["normal", "sensitive"] = "normal"
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class MemoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_summary: str = Field(default="", max_length=1600)
    memories: list[MemoryFact] = Field(default_factory=list, max_length=5)


class StandaloneQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    used_memory: bool = False


@dataclass(frozen=True)
class MemoryContext:
    session_summary: str
    related_summaries: list[str]
    memories: list[dict]

    def render(self) -> str:
        parts: list[str] = []
        if self.session_summary:
            parts.append(f"Session summary: {self.session_summary}")
        if self.related_summaries:
            parts.append("Related past session summaries:")
            for summary in self.related_summaries:
                parts.append(f"- {summary}")
        if self.memories:
            parts.append("Relevant user memories:")
            for memory in self.memories:
                parts.append(
                    f"- {memory['memory_type']}: {memory['memory_key']} = {memory['memory_value']}"
                )
        return "\n".join(parts)[:MAX_MEMORY_CONTEXT_CHARS]


def _memory_collection():
    settings = get_settings()
    return chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    ).get_or_create_collection(MEMORY_COLLECTION_NAME)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _terms(text: str) -> set[str]:
    terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return {term for term in terms if term not in MEMORY_STOPWORDS}


def _is_follow_up(message: str) -> bool:
    text = message.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in FOLLOW_UP_TERMS)


def is_follow_up_message(message: str) -> bool:
    return _is_follow_up(message)


def _mentions_sensitive_topic(message: str) -> bool:
    text = message.lower()
    return any(topic in text for topic in SENSITIVE_TOPICS)


def _memory_score(message_terms: set[str], memory: dict) -> float:
    memory_text = f"{memory['memory_type']} {memory['memory_key']} {memory['memory_value']}"
    memory_terms = _terms(memory_text)
    if not memory_terms:
        return 0.0
    overlap = len(message_terms & memory_terms) / max(1, len(message_terms))
    type_bonus = 0.12 if memory["memory_type"] in {"project", "preference", "goal"} else 0.0
    confidence_bonus = min(0.1, float(memory.get("confidence", 0.0)) / 10)
    return overlap + type_bonus + confidence_bonus


def _structured_memory_context(message: str, user_id: str, limit: int) -> list[dict]:
    message_terms = _terms(message)
    sensitive_allowed = _mentions_sensitive_topic(message)

    scored: list[tuple[float, dict]] = []
    for memory in db.list_user_memories(user_id):
        if memory["sensitivity"] == "sensitive" and not sensitive_allowed:
            continue
        score = _memory_score(message_terms, memory)
        if score > 0.12:
            scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]


async def _semantic_summary_context(session_id: str, message: str, user_id: str, limit: int = 2) -> list[str]:
    if not _is_follow_up(message) or not _terms(message):
        return []
    try:
        vector = await embed(message)
        results = _memory_collection().query(
            query_embeddings=[vector],
            n_results=limit + 1,
            where={"user_id": user_id},
            include=["documents", "metadatas"],
        )
    except Exception:
        return []

    summaries: list[str] = []
    for summary, metadata in zip(
        results.get("documents", [[]])[0],
        results.get("metadatas", [[]])[0],
        strict=False,
    ):
        if metadata.get("session_id") == session_id:
            continue
        if summary and summary not in summaries:
            summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


async def load_memory_context(session_id: str, message: str, user_id: str = LOCAL_USER_ID, limit: int = 5) -> MemoryContext:
    session_memory = db.get_session_memory(session_id)
    session_summary = session_memory["summary"] if session_memory else ""
    return MemoryContext(
        session_summary=session_summary,
        related_summaries=await _semantic_summary_context(session_id, message, user_id),
        memories=_structured_memory_context(message, user_id, limit),
    )


async def upsert_session_memory_vector(session_id: str, summary: str, user_id: str = LOCAL_USER_ID) -> None:
    cleaned = summary.strip()
    if not cleaned:
        return
    try:
        vector = await embed(cleaned)
        _memory_collection().upsert(
            ids=[f"session:{session_id}"],
            embeddings=[vector],
            documents=[cleaned[:1600]],
            metadatas=[{"session_id": session_id, "user_id": user_id}],
        )
    except Exception:
        return


def delete_session_memory_vector(session_id: str) -> None:
    try:
        _memory_collection().delete(ids=[f"session:{session_id}"])
    except Exception:
        return


async def rewrite_query_for_retrieval(
    message: str,
    history: list[dict],
    memory_context: MemoryContext,
) -> str:
    rendered_memory = memory_context.render()
    if not rendered_memory or not _is_follow_up(message):
        return message
    if not any(row["role"] == "assistant" for row in history):
        return message

    recent_history = "\n".join(f"{row['role']}: {row['content'][:400]}" for row in history[-6:])
    schema = StandaloneQuery.model_json_schema()
    system_prompt = (
        "Rewrite follow-up questions into standalone retrieval queries. "
        "Use memory only to resolve references like it, that, those PDFs, or explain again. "
        "Do not add facts that are not present in memory or recent chat. Return only JSON."
    )
    user_prompt = (
        f"Current user message:\n{message}\n\n"
        f"Recent chat:\n{recent_history or 'No recent chat.'}\n\n"
        f"Memory context:\n{rendered_memory}\n\n"
        "Return JSON with query and used_memory."
    )
    try:
        content = await chat_json(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            schema,
        )
        rewritten = StandaloneQuery.model_validate(_extract_json(content))
        return rewritten.query
    except (VllmUnavailableError, json.JSONDecodeError, ValidationError, KeyError, TypeError):
        last_assistant = next((row["content"] for row in reversed(history) if row["role"] == "assistant"), "")
        if last_assistant:
            return f"{message}\nPrevious assistant answer: {last_assistant[:500]}"
        return message


def _fallback_session_summary(history: list[dict], message: str, answer: str) -> str:
    previous_questions = " ".join(row["content"] for row in history[-4:] if row["role"] == "user")
    text = f"Recent user questions: {previous_questions}. Latest user question: {message}."
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:1000]


def _expires_at(days: int | None) -> str | None:
    if not days:
        return None
    return (datetime.now(UTC) + timedelta(days=days)).replace(microsecond=0).isoformat()


async def update_memory_after_turn(
    *,
    session_id: str,
    user_message: str,
    assistant_answer: str,
    history: list[dict],
    user_id: str = LOCAL_USER_ID,
) -> None:
    current_memory = db.get_session_memory(session_id)
    schema = MemoryUpdate.model_json_schema()
    recent_history = "\n".join(f"{row['role']}: {row['content'][:500]}" for row in history[-8:])
    system_prompt = (
        "You update memory for an AI chat assistant. Return only JSON. "
        "Memory is for continuity, not evidence. Keep summaries compact. "
        "Extract only durable facts, preferences, projects, goals, or short-lived states. "
        "Do not store sensitive facts unless the user explicitly asks the assistant to remember them. "
        "Do not store facts copied from PDFs/web sources as user memory."
    )
    user_prompt = (
        f"Existing session summary:\n{current_memory['summary'] if current_memory else 'None'}\n\n"
        f"Recent chat before this turn:\n{recent_history or 'No recent chat.'}\n\n"
        f"Latest user message:\n{user_message}\n\n"
        f"Latest assistant answer:\n{assistant_answer[:2000]}\n\n"
        "Return JSON with session_summary and up to 5 memories."
    )

    try:
        content = await chat_json(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            schema,
        )
        update = MemoryUpdate.model_validate(_extract_json(content))
    except (VllmUnavailableError, json.JSONDecodeError, ValidationError, KeyError, TypeError):
        update = MemoryUpdate(
            session_summary=_fallback_session_summary(history, user_message, assistant_answer),
            memories=[],
        )

    if update.session_summary.strip():
        db.upsert_session_memory(session_id, update.session_summary)
        await upsert_session_memory_vector(session_id, update.session_summary, user_id)

    for memory in update.memories:
        db.upsert_user_memory(
            user_id=user_id,
            memory_type=memory.memory_type,
            memory_key=memory.key,
            memory_value=memory.value,
            confidence=memory.confidence,
            sensitivity=memory.sensitivity,
            expires_at=_expires_at(memory.expires_in_days),
        )
