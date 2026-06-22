import asyncio
import time

from duckduckgo_search import DDGS
import httpx

from app.config import get_settings
from app.schemas import Source


class WebSearchUnavailableError(RuntimeError):
    pass


RATE_LIMIT_HINTS = ("ratelimit", "rate limit", "202", "too many requests")


def _is_rate_limit(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(hint in message for hint in RATE_LIMIT_HINTS)


def _search_sync(query: str, limit: int, backend: str) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, backend=backend, max_results=limit))


def _search_with_retries(query: str, limit: int) -> list[dict]:
    errors: list[str] = []
    # DuckDuckGo sometimes rate-limits one endpoint while another still works.
    # Keep this conservative so demo searches do not hammer the free service.
    attempts = [
        ("html", 0.0),
        ("lite", 1.0),
        ("auto", 2.0),
    ]
    for backend, delay in attempts:
        if delay:
            time.sleep(delay)
        try:
            rows = _search_sync(query, limit, backend)
            if rows:
                return rows
        except Exception as exc:
            errors.append(f"{backend}: {exc}")
            if not _is_rate_limit(exc):
                continue
    raise WebSearchUnavailableError("; ".join(errors) or "No search results returned.")


async def _search_tavily(query: str, limit: int, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": limit,
                "include_answer": False,
            },
        )
        response.raise_for_status()
        return [
            {
                "title": row.get("title"),
                "href": row.get("url"),
                "body": row.get("content"),
            }
            for row in response.json().get("results", [])
        ]


async def _search_brave(query: str, limit: int, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
        )
        response.raise_for_status()
        return [
            {
                "title": row.get("title"),
                "href": row.get("url"),
                "body": row.get("description"),
            }
            for row in response.json().get("web", {}).get("results", [])
        ]


async def _search_configured_provider(query: str, limit: int) -> tuple[list[dict], str]:
    settings = get_settings()
    provider = settings.search_provider.lower()
    errors: list[str] = []

    if provider in {"auto", "tavily"} and settings.tavily_api_key:
        try:
            return await _search_tavily(query, limit, settings.tavily_api_key), "Tavily"
        except Exception as exc:
            errors.append(f"Tavily: {exc}")
            if provider == "tavily":
                raise WebSearchUnavailableError("; ".join(errors)) from exc

    if provider in {"auto", "brave"} and settings.brave_api_key:
        try:
            return await _search_brave(query, limit, settings.brave_api_key), "Brave Search"
        except Exception as exc:
            errors.append(f"Brave Search: {exc}")
            if provider == "brave":
                raise WebSearchUnavailableError("; ".join(errors)) from exc

    if provider in {"auto", "duckduckgo"}:
        try:
            return await asyncio.to_thread(_search_with_retries, query, limit), "DuckDuckGo"
        except Exception as exc:
            errors.append(f"DuckDuckGo: {exc}")

    raise WebSearchUnavailableError("; ".join(errors) or "No configured search provider worked.")


async def web_search(query: str) -> tuple[str, list[Source]]:
    settings = get_settings()
    try:
        rows, provider_name = await _search_configured_provider(query, settings.web_top_k)
    except WebSearchUnavailableError as exc:
        return (
            "Web search is temporarily unavailable because no configured search provider returned results. "
            "For consistent web search, configure TAVILY_API_KEY or BRAVE_API_KEY; DuckDuckGo is only a best-effort fallback. "
            f"Technical detail: {exc}",
            [],
        )

    sources: list[Source] = []
    snippets: list[str] = []
    for index, row in enumerate(rows, start=1):
        title = row.get("title") or "Untitled result"
        url = row.get("href")
        body = row.get("body") or ""
        snippets.append(f"[{index}] {title}\nProvider: {provider_name}\nURL: {url}\nSnippet: {body}")
        sources.append(Source(title=title, url=url, snippet=body[:240]))
    return "\n\n".join(snippets), sources
