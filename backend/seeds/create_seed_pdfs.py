from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


OUTPUT_DIR = Path(__file__).with_name("pdfs")


SEED_DOCS = {
    "ai_internship_requirements.pdf": [
        (
            "AI Internship Requirements",
            [
                "The AI internship is designed for candidates who can build practical machine learning features in a full-stack product environment.",
                "Required programming skills include Python, TypeScript, basic SQL, and the ability to read API documentation independently.",
                "Required Python libraries include NumPy, Pandas, Scikit-learn, FastAPI, and basic testing tools such as pytest.",
                "Candidates should understand supervised learning, embeddings, vector search, retrieval augmented generation, model evaluation, and data preprocessing.",
            ],
        ),
        (
            "Tooling and Project Expectations",
            [
                "The intern is expected to build a small AI assistant that uses a local model, document retrieval, chat memory, and optional web search.",
                "The preferred stack is Next.js for the frontend, FastAPI for the backend, Ollama for local LLM inference, ChromaDB for vector search, and SQLite for chat persistence.",
                "The project should include streaming responses, citation display, deterministic routing, and clear error handling when a source cannot answer the question.",
            ],
        ),
        (
            "Conclusion",
            [
                "A successful AI intern should demonstrate practical engineering judgement, not only model prompting.",
                "The strongest submission combines full-stack implementation, hybrid retrieval, reliable source citation, deterministic tool routing, and evaluation metrics.",
                "The project should prove that the candidate can build a controllable AI workflow that answers only from trusted evidence unless web search is explicitly enabled.",
            ],
        ),
    ],
    "hybrid_rag_design_notes.pdf": [
        (
            "Hybrid Retrieval Design",
            [
                "Hybrid RAG combines semantic retrieval and keyword retrieval to improve evidence selection.",
                "Semantic retrieval uses embeddings to find chunks that are related in meaning, even when exact words do not match.",
                "BM25 keyword retrieval uses exact term matching and inverse document frequency to capture names, tools, technical terms, and codes.",
                "Reciprocal Rank Fusion merges both result lists without requiring scores to share the same scale.",
            ],
        ),
        (
            "Reranking and Confidence",
            [
                "After RRF, candidates should be reranked before answer generation.",
                "A lightweight local reranker can score query term coverage, semantic rank, keyword rank, and whether both retrieval methods agree.",
                "Retrieval confidence can combine normalized RRF score, reranker score, query term coverage, and source diversity.",
                "High confidence means the document evidence is strong enough for grounded answering.",
            ],
        ),
        (
            "Grounded Answer Rule",
            [
                "When web search is disabled, the assistant must answer only from uploaded or seeded documents.",
                "If the documents do not contain enough evidence, the assistant should say it cannot answer from the available PDFs.",
                "This rule makes the system more predictable, testable, and suitable for demos where source control matters.",
            ],
        ),
    ],
    "evaluation_rubric.pdf": [
        (
            "Evaluation Overview",
            [
                "The project should be evaluated with chat-only, document-grounded, web-grounded, and mixed document-web questions.",
                "Routing accuracy measures whether the router selected CHAT, RAG, WEB_SEARCH, or RAG_WEB correctly.",
                "Retrieval quality can be measured with Recall@5, MRR, and nDCG@5.",
            ],
        ),
        (
            "Answer Quality Metrics",
            [
                "Faithfulness measures whether the answer is supported by retrieved evidence.",
                "Citation accuracy measures whether cited sources actually contain the facts being claimed.",
                "Answer completeness measures whether the response covers the important parts of the question.",
                "Latency measures the trade-off introduced by reranking and verification.",
            ],
        ),
        (
            "Conclusion",
            [
                "A strong AI engineering portfolio project should not only work interactively, but should also explain how decisions are made.",
                "The strongest evidence is a comparison showing that hybrid retrieval performs better than semantic-only or keyword-only retrieval.",
                "The final system should be controllable, measurable, and grounded in explicit sources.",
            ],
        ),
    ],
}


def build_pdf(filename: str, sections: list[tuple[str, list[str]]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT_DIR / filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for index, (heading, paragraphs) in enumerate(sections):
        story.append(Paragraph(heading, styles["Title"]))
        story.append(Spacer(1, 16))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 10))
        if index < len(sections) - 1:
            story.append(PageBreak())

    doc.build(story)


def main() -> None:
    for filename, sections in SEED_DOCS.items():
        build_pdf(filename, sections)
    print(f"Created {len(SEED_DOCS)} seed PDFs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
