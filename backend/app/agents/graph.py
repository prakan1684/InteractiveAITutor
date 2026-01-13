from langgraph.graph import StateGraph, END
from app.agents.nodes import ingest, perceive, respond
from app.agents.schemas import State


def build_graph():
    builder = StateGraph(State)
    builder.add_node("ingest", ingest)
    builder.add_node("perceive", perceive)
    builder.add_node("respond", respond)

    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "perceive")
    builder.add_edge("perceive", "respond")
    builder.add_edge("respond", END)

    return builder.compile()