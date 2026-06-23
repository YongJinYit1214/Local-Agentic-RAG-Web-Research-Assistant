from enum import StrEnum
from pydantic import BaseModel


class Route(StrEnum):
    CHAT = "CHAT"
    RAG = "RAG"
    WEB_SEARCH = "WEB_SEARCH"
    RAG_WEB = "RAG_WEB"


class RouteDecision(BaseModel):
    route: Route
    confidence: float
    rationale: str
    signals: dict[str, float | bool]


RAG_THRESHOLD = 0.45
STRONG_RAG_THRESHOLD = 0.75


EXPLICIT_WEB_PHRASES = (
    "search the web",
    "search web",
    "search online",
    "web search",
    "look up online",
    "browse",
    "google",
    "find links",
    "find sources online",
)

FRESHNESS_TERMS = (
    "latest",
    "current",
    "today",
    "this week",
    "this month",
    "recent",
    "newest",
    "now",
    "as of",
    "news",
    "release",
    "announced",
    "price",
    "stock",
    "weather",
    "schedule",
    "regulation",
    "policy update",
)

DOCUMENT_TERMS = (
    "document",
    "pdf",
    "file",
    "uploaded",
    "according to",
    "based on",
    "summarize this",
    "from the report",
    "from the paper",
    "citation",
    "page",
)

ANALYTICAL_TERMS = (
    "compare",
    "evaluate",
    "explain",
    "why",
    "how",
    "pros and cons",
    "tradeoff",
    "strategy",
    "recommend",
    "reason",
)


def _contains_any(message: str, phrases: tuple[str, ...]) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in phrases)


def _density(message: str, phrases: tuple[str, ...]) -> float:
    text = message.lower()
    hits = sum(1 for phrase in phrases if phrase in text)
    return min(1.0, hits / 2)


def analyze_route(
    message: str,
    web_search_mode: bool,
    retrieval_confidence: float = 0,
) -> RouteDecision:
    explicit_web = _contains_any(message, EXPLICIT_WEB_PHRASES)
    freshness_need = _density(message, FRESHNESS_TERMS)
    document_intent = _density(message, DOCUMENT_TERMS)
    analytical_depth = _density(message, ANALYTICAL_TERMS)
    has_strong_docs = retrieval_confidence >= 0.62
    has_possible_docs = retrieval_confidence >= 0.42

    if web_search_mode or explicit_web:
        route = Route.RAG_WEB if retrieval_confidence >= RAG_THRESHOLD else Route.WEB_SEARCH
    elif freshness_need:
        route = Route.RAG_WEB if document_intent and retrieval_confidence >= RAG_THRESHOLD else Route.WEB_SEARCH
    elif document_intent:
        route = Route.RAG if retrieval_confidence >= RAG_THRESHOLD else Route.CHAT
    elif retrieval_confidence >= STRONG_RAG_THRESHOLD:
        route = Route.RAG
    else:
        route = Route.CHAT

    confidence = min(
        0.99,
        max(
            retrieval_confidence,
            0.85 if web_search_mode or explicit_web else 0,
            freshness_need,
            document_intent,
            0.6 if route == Route.CHAT else 0,
        ),
    )

    if route == Route.RAG_WEB:
        rationale = "The request needs both uploaded-document grounding and fresh external context."
    elif route == Route.WEB_SEARCH:
        rationale = "The request needs external or fresh information, or Web Search Mode is enabled."
    elif route == Route.RAG:
        rationale = "Uploaded documents have enough semantic match, and the request benefits from grounded citations."
    else:
        rationale = "No strong web or document-grounding signal was found, so chat history and general reasoning are enough."

    if document_intent and route == Route.CHAT:
        rationale = "The request mentions documents, but retrieval confidence is too low for reliable grounding."
    elif has_possible_docs and route == Route.CHAT:
        rationale = "Document evidence was weak, so the assistant avoids forcing unrelated citations."

    return RouteDecision(
        route=route,
        confidence=round(confidence, 2),
        rationale=rationale,
        signals={
            "web_search_mode": web_search_mode,
            "explicit_web_intent": explicit_web,
            "freshness_need": round(freshness_need, 2),
            "document_intent": round(document_intent, 2),
            "analytical_depth": round(analytical_depth, 2),
            "retrieval_confidence": round(retrieval_confidence, 2),
            "strong_document_match": has_strong_docs,
            "possible_document_match": has_possible_docs,
        },
    )


def choose_route(message: str, web_search_mode: bool, has_relevant_docs: bool) -> Route:
    retrieval_confidence = 0.65 if has_relevant_docs else 0
    return analyze_route(message, web_search_mode, retrieval_confidence).route
