from enum import StrEnum


class Route(StrEnum):
    CHAT = "CHAT"
    RAG = "RAG"
    WEB_SEARCH = "WEB_SEARCH"


WEB_TRIGGERS = (
    "search web",
    "search online",
    "latest",
    "current",
    "today",
    "online",
    "look up",
    "web search",
    "recent",
    "news",
)


def wants_web(message: str) -> bool:
    text = message.lower()
    return any(trigger in text for trigger in WEB_TRIGGERS)


def choose_route(message: str, web_search_mode: bool, has_relevant_docs: bool) -> Route:
    if web_search_mode:
        return Route.WEB_SEARCH
    if wants_web(message):
        return Route.WEB_SEARCH
    if has_relevant_docs:
        return Route.RAG
    return Route.CHAT
