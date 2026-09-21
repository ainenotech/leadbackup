from langgraph.graph import StateGraph, END

from .state import LeadState
from .agents.composer import compose_email


def compose_node(state: LeadState) -> LeadState:
    subject, body = compose_email(
        name=state.get("name"),
        company=state.get("company"),
        last_activity_date=state.get("last_activity_date"),
        last_deal_stage=state.get("last_deal_stage"),
        tracking_link=state.get("tracking_link"),
    )
    state["subject"] = subject
    state["body"] = body
    return state



def build_graph():
    """Single-node graph today. Kept as a graph (not a plain function call)
    so Phase 2/3 steps — e.g. a compliance/policy check node, or an
    A/B subject-line variant node — can be inserted without restructuring
    the pipeline, matching the reference repo's multi-node pattern.
    """
    graph = StateGraph(LeadState)
    graph.add_node("compose", compose_node)
    graph.set_entry_point("compose")
    graph.add_edge("compose", END)
    return graph.compile()
