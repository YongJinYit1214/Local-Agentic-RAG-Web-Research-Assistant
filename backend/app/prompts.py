from app.schemas import Source


MAX_CONTEXT_CHARS = 9000
MAX_SOURCE_CHARS = 3000
MAX_HISTORY_CHARS = 300


SYSTEM_PROMPT = """You are EvidenceDocs, a seeded PDF research assistant.
Answer clearly and cite provided sources when they are available.
If the provided document context does not answer the question, say so instead of inventing details.
When a guarantee or policy is not mentioned, say it is not specified; do not claim it does not exist.
When Web Search is not active, answer only from uploaded or seeded PDF/document context.
Memory context may help interpret follow-up wording, but memory is not factual evidence.
For web results, summarize only what the search snippets support and include links in sources.
"""


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[trimmed]"


def build_messages(
    user_message: str,
    history: list[dict],
    route: str,
    context: list[str] | str | None = None,
    sources: list[Source] | None = None,
    memory_context: str | None = None,
) -> list[dict[str, str]]:
    source_block = ""
    if sources:
        source_block = "\n".join(
            f"[{i}] {source.title} {source.url or source.document or ''}".strip()
            for i, source in enumerate(sources, start=1)
        )

    if isinstance(context, list):
        context_text = "\n\n".join(
            f"[{index}] {sources[index - 1].title if sources and index <= len(sources) else 'Context'}:\n"
            f"{_trim(item, MAX_SOURCE_CHARS)}"
            for index, item in enumerate(context, start=1)
        )
    else:
        context_text = context or ""
    context_text = _trim(context_text, MAX_CONTEXT_CHARS)
    route_instruction = {
        "CHAT": "Do not answer from general knowledge. Say the PDFs do not contain enough evidence.",
        "RAG": "Use the hybrid RAG document context as the primary evidence and cite source numbers.",
        "WEB_SEARCH": "Use the web search snippets as the primary evidence and cite source numbers.",
        "RAG_WEB": "Compare and synthesize document context with web search snippets. Be explicit about which claims come from uploaded documents and which come from online results.",
    }[route]

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(
        {"role": row["role"], "content": _trim(row["content"], MAX_HISTORY_CHARS)}
        for row in history[-2:]
    )
    messages.append(
        {
            "role": "user",
            "content": (
                f"Route: {route}\n"
                f"Instruction: {route_instruction}\n\n"
                f"Memory context for continuity only, not evidence:\n{memory_context or 'No relevant memory.'}\n\n"
                f"Context:\n{context_text or 'No external context.'}\n\n"
                f"Sources:\n{source_block or 'No sources.'}\n\n"
                f"Question: {user_message}"
            ),
        }
    )
    return messages
