from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.routing import Route, analyze_route


class RouterState(TypedDict):
    message: str
    web_search_mode: bool
    retrieval_confidence: float
    max_query_term_coverage: float
    keyword_match_count: int
    route: str
    confidence: float
    rationale: str
    signals: dict


def route_node(state: RouterState) -> RouterState:
    decision = analyze_route(
        state["message"],
        state["web_search_mode"],
        state["retrieval_confidence"],
        state["max_query_term_coverage"],
        state["keyword_match_count"],
    )
    return {
        **state,
        "route": decision.route.value,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
        "signals": decision.signals,
    }


def build_router_graph():
    graph = StateGraph(RouterState)
    graph.add_node("deterministic_router", route_node)
    graph.set_entry_point("deterministic_router")
    graph.add_edge("deterministic_router", END)
    return graph.compile()


router_graph = build_router_graph()


def choose_route_with_graph(
    message: str,
    web_search_mode: bool,
    retrieval_confidence: float,
    max_query_term_coverage: float = 0,
    keyword_match_count: int = 0,
):
    state = router_graph.invoke(
        {
            "message": message,
            "web_search_mode": web_search_mode,
            "retrieval_confidence": retrieval_confidence,
            "max_query_term_coverage": max_query_term_coverage,
            "keyword_match_count": keyword_match_count,
            "route": Route.CHAT.value,
            "confidence": 0,
            "rationale": "",
            "signals": {},
        }
    )
    return state
