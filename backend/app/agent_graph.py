from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.routing import Route, choose_route


class RouterState(TypedDict):
    message: str
    web_search_mode: bool
    has_relevant_docs: bool
    route: str


def route_node(state: RouterState) -> RouterState:
    route = choose_route(
        state["message"],
        state["web_search_mode"],
        state["has_relevant_docs"],
    )
    return {**state, "route": route.value}


def build_router_graph():
    graph = StateGraph(RouterState)
    graph.add_node("deterministic_router", route_node)
    graph.set_entry_point("deterministic_router")
    graph.add_edge("deterministic_router", END)
    return graph.compile()


router_graph = build_router_graph()


def choose_route_with_graph(message: str, web_search_mode: bool, has_relevant_docs: bool) -> Route:
    state = router_graph.invoke(
        {
            "message": message,
            "web_search_mode": web_search_mode,
            "has_relevant_docs": has_relevant_docs,
            "route": Route.CHAT.value,
        }
    )
    return Route(state["route"])
