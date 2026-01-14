from langgraph.graph import StateGraph, END
from app.agents.nodes import ingest, perceive, respond, understand, annotate
from app.agents.schemas import State


def build_graph():
    builder = StateGraph(State)
    builder.add_node("ingest", ingest)
    builder.add_node("perceive", perceive)
    builder.add_node("respond", respond)
    builder.add_node("understand", understand)
    builder.add_node("annotate", annotate)

    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "perceive")
    builder.add_edge("perceive", "understand")
    builder.add_edge("understand", "annotate")
    builder.add_edge("annotate", "respond")
    builder.add_edge("respond", END)

    return builder.compile()