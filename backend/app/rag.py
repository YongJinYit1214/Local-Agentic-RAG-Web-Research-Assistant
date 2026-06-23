import re
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.ollama_client import embed
from app.schemas import Source


COLLECTION_NAME = "localmind_documents"
RRF_K = 60
PARENT_CHUNK_TOKENS = 1200
CHILD_CHUNK_TOKENS = 420
CHILD_OVERLAP_TOKENS = 80


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


def chunk_text(text: str, size: int = CHILD_CHUNK_TOKENS, overlap: int = CHILD_OVERLAP_TOKENS) -> list[str]:
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


def parent_child_chunks(text: str) -> list[tuple[int, str, int, str]]:
    words = text.split()
    chunks: list[tuple[int, str, int, str]] = []
    if not words:
        return chunks

    parent_index = 0
    for parent_start in range(0, len(words), PARENT_CHUNK_TOKENS):
        parent_words = words[parent_start : parent_start + PARENT_CHUNK_TOKENS]
        parent_text = " ".join(parent_words)
        child_index = 0
        child_start = 0
        while child_start < len(parent_words):
            child_end = min(child_start + CHILD_CHUNK_TOKENS, len(parent_words))
            child_text = " ".join(parent_words[child_start:child_end])
            if child_text:
                chunks.append((parent_index, parent_text, child_index, child_text))
            if child_end == len(parent_words):
                break
            child_start = max(0, child_end - CHILD_OVERLAP_TOKENS)
            child_index += 1
        parent_index += 1
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
        for parent_index, parent_text, child_index, child_text in parent_child_chunks(text):
            vector = await embed(child_text)
            collection.add(
                ids=[str(uuid.uuid4())],
                embeddings=[vector],
                documents=[child_text],
                metadatas=[
                    {
                        "document": path.name,
                        "page": page,
                        "parent": parent_index,
                        "chunk": child_index,
                        "parent_text": parent_text,
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


def preprocess_query(query: str) -> str:
    cleaned = _clean_text(query)
    if not get_settings().enable_query_rewrite:
        return cleaned

    text = cleaned.lower()
    expansions: list[str] = []
    if any(term in text for term in ("skill", "requirement", "qualification")):
        expansions.append("skills tools programming libraries qualifications requirements")
    if any(term in text for term in ("intern", "internship", "job")):
        expansions.append("internship role responsibilities experience")
    if any(term in text for term in ("conclusion", "summary", "summarize")):
        expansions.append("conclusion summary final section key points")
    if any(term in text for term in ("file", "document", "pdf", "uploaded")):
        expansions.append("uploaded document file content")
    return " ".join([cleaned, *expansions]).strip()


def _keyword_results(collection, query: str, limit: int, session_id: str) -> list[dict]:
    rows = collection.get(where={"session_id": session_id}, include=["documents", "metadatas"])
    query_terms = _tokens(query)
    documents = rows.get("documents", [])
    if not query_terms or not documents:
        return []
    tokenized_documents = [_tokens(document) for document in documents]
    bm25 = BM25Okapi(tokenized_documents)
    scores = bm25.get_scores(query_terms)
    scored: list[dict] = []
    for doc_id, doc, metadata, score in zip(
        rows.get("ids", []),
        documents,
        rows.get("metadatas", []),
        scores,
        strict=False,
    ):
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


def _query_term_coverage(query: str, text: str) -> float:
    query_terms = set(_tokens(query))
    if not query_terms:
        return 0.0
    text_terms = set(_tokens(text))
    return len(query_terms & text_terms) / len(query_terms)


def _rerank_score(query: str, row: dict) -> tuple[float, str]:
    child_text = row["document"]
    parent_text = row.get("metadata", {}).get("parent_text") or child_text
    coverage = _query_term_coverage(query, child_text)
    parent_coverage = _query_term_coverage(query, parent_text)
    semantic_bonus = 1.0 if row.get("semantic_rank") else 0.0
    keyword_bonus = 1.0 if row.get("keyword_rank") else 0.0
    dual_bonus = 0.5 if row.get("semantic_rank") and row.get("keyword_rank") else 0.0
    score = min(5.0, (coverage * 2.0) + (parent_coverage * 1.0) + semantic_bonus + keyword_bonus + dual_bonus)
    reason = f"coverage={coverage:.2f}, parent_coverage={parent_coverage:.2f}"
    return score, reason


def _rerank(query: str, rows: list[dict], limit: int) -> list[dict]:
    reranked: list[dict] = []
    for row in rows:
        score, reason = _rerank_score(query, row)
        reranked.append({**row, "rerank_score": score, "rerank_reason": reason})
    reranked.sort(key=lambda row: (row["rerank_score"], row.get("rrf_score", 0)), reverse=True)
    threshold = get_settings().rerank_min_score
    filtered = [row for row in reranked if row["rerank_score"] >= threshold]
    return (filtered or reranked)[:limit]


def _retrieval_confidence(query: str, rows: list[dict]) -> float:
    if not rows:
        return 0.0
    max_rrf = max(row.get("rrf_score", 0.0) for row in rows) or 1.0
    rrf_score_norm = min(1.0, rows[0].get("rrf_score", 0.0) / max_rrf)
    rerank_score_norm = min(1.0, (sum(row.get("rerank_score", 0.0) for row in rows) / len(rows)) / 5.0)
    query_term_coverage = max(_query_term_coverage(query, row["document"]) for row in rows)
    unique_sources = {row.get("metadata", {}).get("document") for row in rows}
    source_diversity = min(1.0, len(unique_sources) / max(1, len(rows)))
    return round(
        (0.4 * rrf_score_norm)
        + (0.3 * rerank_score_norm)
        + (0.2 * query_term_coverage)
        + (0.1 * source_diversity),
        2,
    )


async def retrieve(message: str, session_id: str, top_k: int | None = None) -> tuple[list[str], list[Source], float]:
    settings = get_settings()
    collection = _collection()
    session_rows = collection.get(where={"session_id": session_id})
    session_count = len(session_rows.get("ids", []))
    if session_count == 0:
        return [], [], 0

    top_k = top_k or settings.rag_top_k
    retrieval_query = preprocess_query(message)
    vector = await embed(retrieval_query)
    candidate_limit = min(max(top_k * 4, 10), session_count)
    semantic_rows = _semantic_results(collection, vector, candidate_limit, session_id)
    keyword_rows = _keyword_results(collection, retrieval_query, candidate_limit, session_id)
    fused_rows = _merge_with_rrf(semantic_rows, keyword_rows, min(candidate_limit, 10))
    final_rows = _rerank(retrieval_query, fused_rows, top_k)

    contexts: list[str] = []
    sources: list[Source] = []
    for row in final_rows:
        doc = row.get("metadata", {}).get("parent_text") or row["document"]
        metadata = row["metadata"]
        contexts.append(doc)
        retrieval_detail = (
            f"RRF: {row.get('rrf_score', 0):.4f}; "
            f"semantic rank: {row.get('semantic_rank') or 'none'}; "
            f"keyword rank: {row.get('keyword_rank') or 'none'}; "
            f"rerank: {row.get('rerank_score', 0):.1f}/5"
        )
        sources.append(
            Source(
                title=f"{metadata.get('document')} page {metadata.get('page')}",
                document=metadata.get("document"),
                page=metadata.get("page"),
                snippet=f"{retrieval_detail}. {doc[:220]}",
            )
        )
    retrieval_confidence = _retrieval_confidence(retrieval_query, final_rows)
    return contexts, sources, retrieval_confidence
