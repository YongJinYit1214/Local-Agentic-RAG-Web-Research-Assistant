from enum import StrEnum
from pydantic import BaseModel


class Route(StrEnum):
    CHAT = "CHAT"
    RAG = "RAG"
    WEB_SEARCH = "WEB_SEARCH"
    HYBRID_RAG_WEB = "HYBRID_RAG_WEB"


class RouteDecision(BaseModel):
    route: Route
    confidence: float
    rationale: str
    signals: dict[str, float | bool]


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

    web_score = 0.0
    if web_search_mode:
        web_score += 1.0
    if explicit_web:
        web_score += 0.85
    web_score += freshness_need * 0.7
    if document_intent:
        web_score -= document_intent * 0.4

    rag_score = 0.0
    rag_score += retrieval_confidence
    rag_score += document_intent * 0.55
    if explicit_web or web_search_mode:
        rag_score -= 0.5
    if freshness_need >= 0.5 and not document_intent:
        rag_score -= 0.25

    chat_score = 0.35 + analytical_depth * 0.2
    if not explicit_web and freshness_need == 0 and not has_possible_docs:
        chat_score += 0.25

    hybrid_score = 0.0
    if has_possible_docs and (web_search_mode or explicit_web or freshness_need >= 0.5):
        hybrid_score = retrieval_confidence + freshness_need * 0.55 + document_intent * 0.45
    if web_search_mode and has_possible_docs and document_intent:
        hybrid_score += 0.35

    scores = {
        Route.WEB_SEARCH: max(0.0, web_score),
        Route.RAG: max(0.0, rag_score),
        Route.HYBRID_RAG_WEB: max(0.0, hybrid_score),
        Route.CHAT: max(0.0, chat_score),
    }
    route = max(scores, key=scores.get)
    confidence = min(0.99, max(scores.values()))

    if route == Route.HYBRID_RAG_WEB:
        rationale = "The request needs both uploaded-document grounding and fresh external context."
    elif route == Route.WEB_SEARCH:
        rationale = "The request needs external or fresh information, or Web Search Mode is enabled."
    elif route == Route.RAG:
        rationale = "Uploaded documents have enough semantic match, and the request benefits from grounded citations."
    else:
        rationale = "No strong web or document-grounding signal was found, so chat history and general reasoning are enough."

    if has_possible_docs and route == Route.CHAT:
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
        },
    )


def choose_route(message: str, web_search_mode: bool, has_relevant_docs: bool) -> Route:
    retrieval_confidence = 0.65 if has_relevant_docs else 0
    return analyze_route(message, web_search_mode, retrieval_confidence).route
