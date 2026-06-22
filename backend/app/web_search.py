import asyncio

from duckduckgo_search import DDGS

from app.config import get_settings
from app.schemas import Source


def _search_sync(query: str, limit: int) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=limit))


async def web_search(query: str) -> tuple[str, list[Source]]:
    settings = get_settings()
    rows = await asyncio.to_thread(_search_sync, query, settings.web_top_k)
    sources: list[Source] = []
    snippets: list[str] = []
    for index, row in enumerate(rows, start=1):
        title = row.get("title") or "Untitled result"
        url = row.get("href")
        body = row.get("body") or ""
        snippets.append(f"[{index}] {title}\nURL: {url}\nSnippet: {body}")
        sources.append(Source(title=title, url=url, snippet=body[:240]))
    return "\n\n".join(snippets), sources
