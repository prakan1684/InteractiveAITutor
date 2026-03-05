from langgraph.graph import END, StateGraph


from app_v2.graph.nodes import (
    evaluate_solution_node,
    finalize_response_node,
    generate_feedback_node,
    load_context_node,
    route_decision_node,
)
from app_v2.graph.state import TutorGraphState



def create_tutor_graph():

    workflow = StateGraph(TutorGraphState)

    workflow.add_node("load_context", load_context_node)
    workflow.add_node("evaluate_solution", evaluate_solution_node)
    workflow.add_node("route_decision", route_decision_node)
    workflow.add_node("generate_feedback", generate_feedback_node)
    workflow.add_node("finalize_response", finalize_response_node)

    workflow.set_entry_point("load_context")

    workflow.add_edge("load_context", "evaluate_solution")
    workflow.add_edge("evaluate_solution", "route_decision")
    workflow.add_edge("route_decision", "generate_feedback")
    workflow.add_edge("generate_feedback", "finalize_response")
    workflow.add_edge("finalize_response", END)

    return workflow.compile()


tutor_graph = create_tutor_graph()
