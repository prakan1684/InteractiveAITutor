from langgraph.graph import StateGraph, END
from app.agents.nodes import ingest, perceive, respond, annotate, analyze_canvas
from app.agents.schemas import State


def build_graph():
    builder = StateGraph(State)
    builder.add_node("ingest", ingest)
    builder.add_node("perceive", perceive)
    builder.add_node("respond", respond)
    builder.add_node("annotate", annotate)
    builder.add_node("analyze_canvas", analyze_canvas)

    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "perceive")
    builder.add_edge("perceive", "analyze_canvas")
    builder.add_edge("analyze_canvas", "annotate")
    builder.add_edge("annotate", "respond")
    builder.add_edge("respond", END)

    return builder.compile()
