from langgraph.graph import StateGraph, END
from app.agents.schemas import ChatState
from app.agents.chat_nodes import classify_intent, retrieve_context, reason, respond


def create_chat_graph():
    """
    Creates chat agent graph
    """


    workflow = StateGraph(ChatState)


    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("reason", reason)
    workflow.add_node("respond", respond)
    
    # Define edges (flow)
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "retrieve_context")
    workflow.add_edge("retrieve_context", "reason")
    workflow.add_edge("reason", "respond")
    workflow.add_edge("respond", END)
    
    return workflow.compile()


chat_graph = create_chat_graph()