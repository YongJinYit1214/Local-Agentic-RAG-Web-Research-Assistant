import re
import uuid
from collections import Counter
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader

from app.config import get_settings
from app.ollama_client import embed
from app.schemas import Source


COLLECTION_NAME = "localmind_documents"
RRF_K = 60


def _client():
    settings = get_settings()
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _collection():
    return _client().get_or_create_collection(COLLECTION_NAME)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        if chunk:
            chunks.append(chunk)
        start = max(end - overlap, end) if end == len(words) else end - overlap
    return chunks


def extract_pages(path: Path) -> list[tuple[int, str]]:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return [
            (index + 1, _clean_text(page.extract_text() or ""))
            for index, page in enumerate(reader.pages)
        ]
    return [(1, _clean_text(path.read_text(encoding="utf-8", errors="ignore")))]


async def ingest_document(path: Path, session_id: str) -> int:
    collection = _collection()
    added = 0
    for page, text in extract_pages(path):
        for chunk_index, chunk in enumerate(chunk_text(text)):
            vector = await embed(chunk)
            collection.add(
                ids=[str(uuid.uuid4())],
                embeddings=[vector],
                documents=[chunk],
                metadatas=[
                    {
                        "document": path.name,
                        "page": page,
                        "chunk": chunk_index,
                        "session_id": session_id,
                    }
                ],
            )
            added += 1
    return added


def _where_session(session_id: str | None):
    return {"session_id": session_id} if session_id else None


def list_indexed_documents(session_id: str | None = None) -> list[dict]:
    collection = _collection()
    if collection.count() == 0:
        return []
    rows = collection.get(where=_where_session(session_id), include=["metadatas"])
    documents: dict[str, int] = {}
    for metadata in rows.get("metadatas") or []:
        name = metadata.get("document", "Unknown")
        documents[name] = documents.get(name, 0) + 1
    return [{"document": name, "chunks": chunks} for name, chunks in sorted(documents.items())]


def delete_document(document_name: str, session_id: str | None = None) -> int:
    collection = _collection()
    if collection.count() == 0:
        return 0
    where = {"document": document_name}
    if session_id:
        where = {"$and": [{"document": document_name}, {"session_id": session_id}]}
    rows = collection.get(where=where)
    ids = rows.get("ids", [])
    if ids:
        collection.delete(ids=ids)

    upload_path = Path("./data/uploads") / (session_id or "_global") / Path(document_name).name
    if upload_path.exists():
        upload_path.unlink()
    return len(ids)


def clear_documents(session_id: str | None = None) -> int:
    collection = _collection()
    rows = collection.get(where=_where_session(session_id)) if session_id else collection.get()
    ids = rows.get("ids", [])
    count = len(ids)
    if count:
        if ids:
            collection.delete(ids=ids)

    uploads_dir = Path("./data/uploads") / session_id if session_id else Path("./data/uploads")
    if uploads_dir.exists():
        for path in uploads_dir.rglob("*"):
            if path.is_file():
                path.unlink()
    return count


def clear_legacy_documents() -> int:
    collection = _collection()
    if collection.count() == 0:
        return 0
    rows = collection.get(include=["metadatas"])
    ids_to_delete = [
        doc_id
        for doc_id, metadata in zip(rows.get("ids", []), rows.get("metadatas", []), strict=False)
        if not metadata.get("session_id")
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def _semantic_results(collection, query_vector: list[float], limit: int, session_id: str) -> list[dict]:
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=limit,
        where={"session_id": session_id},
        include=["documents", "metadatas", "distances"],
    )
    rows: list[dict] = []
    for doc_id, doc, metadata, distance in zip(
        results.get("ids", [[]])[0],
        results.get("documents", [[]])[0],
        results.get("metadatas", [[]])[0],
        results.get("distances", [[]])[0],
        strict=False,
    ):
        rows.append(
            {
                "id": doc_id,
                "document": doc,
                "metadata": metadata,
                "distance": distance,
            }
        )
    return rows


def _keyword_score(query_terms: list[str], document: str) -> float:
    doc_terms = _tokens(document)
    if not query_terms or not doc_terms:
        return 0.0
    counts = Counter(doc_terms)
    doc_length = len(doc_terms)
    score = 0.0
    for term in query_terms:
        term_frequency = counts.get(term, 0)
        if term_frequency:
            score += term_frequency / (term_frequency + 1.5 + 0.75 * doc_length / 120)
    return score


def _keyword_results(collection, query: str, limit: int, session_id: str) -> list[dict]:
    rows = collection.get(where={"session_id": session_id}, include=["documents", "metadatas"])
    query_terms = _tokens(query)
    scored: list[dict] = []
    for doc_id, doc, metadata in zip(
        rows.get("ids", []),
        rows.get("documents", []),
        rows.get("metadatas", []),
        strict=False,
    ):
        score = _keyword_score(query_terms, doc)
        if score > 0:
            scored.append(
                {
                    "id": doc_id,
                    "document": doc,
                    "metadata": metadata,
                    "keyword_score": score,
                }
            )
    return sorted(scored, key=lambda row: row["keyword_score"], reverse=True)[:limit]


def _merge_with_rrf(semantic_rows: list[dict], keyword_rows: list[dict], limit: int) -> list[dict]:
    merged: dict[str, dict] = {}

    for rank, row in enumerate(semantic_rows, start=1):
        item = merged.setdefault(row["id"], {**row, "rrf_score": 0.0, "semantic_rank": None, "keyword_rank": None})
        item.update(row)
        item["semantic_rank"] = rank
        item["rrf_score"] += 1 / (RRF_K + rank)

    for rank, row in enumerate(keyword_rows, start=1):
        item = merged.setdefault(row["id"], {**row, "rrf_score": 0.0, "semantic_rank": None, "keyword_rank": None})
        item.update(row)
        item["keyword_rank"] = rank
        item["rrf_score"] += 1 / (RRF_K + rank)

    return sorted(merged.values(), key=lambda row: row["rrf_score"], reverse=True)[:limit]


async def retrieve(message: str, session_id: str, top_k: int | None = None) -> tuple[list[str], list[Source], float]:
    settings = get_settings()
    collection = _collection()
    session_rows = collection.get(where={"session_id": session_id})
    session_count = len(session_rows.get("ids", []))
    if session_count == 0:
        return [], [], 0

    top_k = top_k or settings.rag_top_k
    vector = await embed(message)
    candidate_limit = min(max(top_k * 4, 10), session_count)
    semantic_rows = _semantic_results(collection, vector, candidate_limit, session_id)
    keyword_rows = _keyword_results(collection, message, candidate_limit, session_id)
    final_rows = _merge_with_rrf(semantic_rows, keyword_rows, top_k)

    contexts: list[str] = []
    sources: list[Source] = []
    for row in final_rows:
        doc = row["document"]
        metadata = row["metadata"]
        contexts.append(doc)
        retrieval_detail = (
            f"RRF: {row.get('rrf_score', 0):.4f}; "
            f"semantic rank: {row.get('semantic_rank') or 'none'}; "
            f"keyword rank: {row.get('keyword_rank') or 'none'}"
        )
        sources.append(
            Source(
                title=f"{metadata.get('document')} page {metadata.get('page')}",
                document=metadata.get("document"),
                page=metadata.get("page"),
                snippet=f"{retrieval_detail}. {doc[:220]}",
            )
        )
    retrieval_confidence = min(0.95, 0.55 + (0.08 * len(contexts))) if contexts else 0.0
    return contexts, sources, retrieval_confidence
