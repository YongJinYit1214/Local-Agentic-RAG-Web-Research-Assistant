from app.schemas import Source


SYSTEM_PROMPT = """You are EvidenceDocs, a seeded PDF research assistant.
Answer clearly and cite provided sources when they are available.
If the provided document context does not answer the question, say so instead of inventing details.
When Web Search is not active, answer only from uploaded or seeded PDF/document context.
For web results, summarize only what the search snippets support and include links in sources.
"""


def build_messages(
    user_message: str,
    history: list[dict],
    route: str,
    context: list[str] | str | None = None,
    sources: list[Source] | None = None,
) -> list[dict[str, str]]:
    source_block = ""
    if sources:
        source_block = "\n".join(
            f"[{i}] {source.title} {source.url or source.document or ''}".strip()
            for i, source in enumerate(sources, start=1)
        )

    context_text = "\n\n".join(context) if isinstance(context, list) else context or ""
    route_instruction = {
        "CHAT": "Do not answer from general knowledge. Say the PDFs do not contain enough evidence.",
        "RAG": "Use the hybrid RAG document context as the primary evidence and cite source numbers.",
        "WEB_SEARCH": "Use the web search snippets as the primary evidence and cite source numbers.",
        "RAG_WEB": "Compare and synthesize document context with web search snippets. Be explicit about which claims come from uploaded documents and which come from online results.",
    }[route]

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": row["role"], "content": row["content"]} for row in history[-12:])
    messages.append(
        {
            "role": "user",
            "content": (
                f"Route: {route}\n"
                f"Instruction: {route_instruction}\n\n"
                f"Context:\n{context_text or 'No external context.'}\n\n"
                f"Sources:\n{source_block or 'No sources.'}\n\n"
                f"Question: {user_message}"
            ),
        }
    )
    return messages
