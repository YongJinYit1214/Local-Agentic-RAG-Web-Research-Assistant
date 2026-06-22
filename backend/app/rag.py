import re
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pypdf import PdfReader

from app.config import get_settings
from app.ollama_client import embed
from app.schemas import Source


COLLECTION_NAME = "localmind_documents"


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


async def ingest_document(path: Path) -> int:
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
                    }
                ],
            )
            added += 1
    return added


async def retrieve(message: str, top_k: int | None = None) -> tuple[list[str], list[Source], float]:
    settings = get_settings()
    collection = _collection()
    if collection.count() == 0:
        return [], [], 0

    vector = await embed(message)
    results = collection.query(
        query_embeddings=[vector],
        n_results=top_k or settings.rag_top_k,
        include=["documents", "metadatas", "distances"],
    )
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    contexts: list[str] = []
    sources: list[Source] = []
    best_confidence = 0.0
    for doc, metadata, distance in zip(docs, metadatas, distances, strict=False):
        confidence = max(0.0, min(1.0, 1.0 - float(distance or 0)))
        best_confidence = max(best_confidence, confidence)
        if distance is not None and distance > 1.25:
            continue
        contexts.append(doc)
        sources.append(
            Source(
                title=f"{metadata.get('document')} page {metadata.get('page')}",
                document=metadata.get("document"),
                page=metadata.get("page"),
                snippet=doc[:240],
            )
        )
    return contexts, sources, best_confidence
