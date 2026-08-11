import argparse
import asyncio
from pathlib import Path

from app.rag import SEED_SESSION_ID, clear_documents, has_seed_document, ingest_document


async def preindex_seed_documents(seed_dir: Path, reset: bool = False) -> list[dict]:
    if reset:
        clear_documents(SEED_SESSION_ID)

    loaded: list[dict] = []
    seed_dir.mkdir(parents=True, exist_ok=True)
    for seed_path in sorted(seed_dir.glob("*.pdf")):
        if has_seed_document(seed_path.name):
            loaded.append({"filename": seed_path.name, "status": "skipped", "chunks": 0})
            continue
        chunks = await ingest_document(seed_path, SEED_SESSION_ID, source_type="seed")
        loaded.append({"filename": seed_path.name, "status": "indexed", "chunks": chunks})
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-index seed PDFs into the shared ChromaDB seed corpus.")
    parser.add_argument("--seed-dir", default="./seeds/pdfs", help="Directory containing seed PDF files.")
    parser.add_argument("--reset", action="store_true", help="Delete existing shared seed chunks before indexing.")
    args = parser.parse_args()

    loaded = asyncio.run(preindex_seed_documents(Path(args.seed_dir), reset=args.reset))
    indexed = sum(1 for row in loaded if row["status"] == "indexed")
    skipped = sum(1 for row in loaded if row["status"] == "skipped")
    chunks = sum(row["chunks"] for row in loaded)

    for row in loaded:
        print(f"{row['status']:>7} {row['filename']} ({row['chunks']} chunks)")
    print(f"Seed pre-index complete: {indexed} indexed, {skipped} skipped, {chunks} new chunks.")


if __name__ == "__main__":
    main()
