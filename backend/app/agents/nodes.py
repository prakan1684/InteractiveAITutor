from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from app.agents.orchestrator_agent import orchestrator_node
from app.agents.memory_agent import memory_node
from app.agents.vision_agent import vision_node
from app.agents.feedback_agent import feedback_node
from app.agents.schemas import TutorState, AgenticTrace
from app.core.logger import get_logger
 
logger = get_logger(__name__)

def create_tutor_workflow():
    # LangGraph automatically merges dict updates with existing state
    workflow = StateGraph(dict)


    #add agent nodes

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("vision", vision_node)
    workflow.add_node("feedback", feedback_node)

    #entry point
    workflow.set_entry_point("orchestrator")

    #routing logic
    def route_from_orchestrator(state: Dict[str, Any]) -> str:
        """
        Route to next agent based on Orchestrators decision
        """

        trace = state.get("trace", {})
        next_action = trace.get("next_action", "end")

        logger.info(f"Routing: {next_action}")

        if trace.get("workflow_complete", False):
            return END
        
        if next_action == "end":
            return END
        elif next_action == "memory":
            return "memory"
        elif next_action == "vision":
            return "vision"
        elif next_action == "feedback":
            return "feedback"
        else:
            logger.warning(f"⚠️ Unknown next_action: {next_action}, returning to orchestrator")
            return "orchestrator"
        

    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "memory": "memory",
            "vision": "vision",
            "feedback": "feedback",
            "orchestrator": "orchestrator",
            END: END
        }
    )

    workflow.add_edge("memory", "orchestrator")
    workflow.add_edge("vision", "orchestrator")
    workflow.add_edge("feedback", "orchestrator")


    app = workflow.compile()

    logger.info("Tutor workflow compiled successfully")

    return app

tutor_workflow = create_tutor_workflow()

async def run_canvas_analysis(
    session_id: str,
    student_id: str,
    full_canvas_path: str,
    canvas_dimensions: Dict[str, int],
    steps_metadata: List[Dict],
    step_image_paths: Dict[str, str],
    strokes_data: List[Dict]
) -> Dict[str, Any]:
    """
    Simplified canvas analysis workflow: Vision -> Feedback
    Bypasses Orchestrator and Memory for efficiency.
    """
    
    initial_state = {
        "session_id": session_id,
        "student_id": student_id,
        "full_canvas_path": full_canvas_path,
        "canvas_dimensions": canvas_dimensions,
        "steps_metadata": steps_metadata,
        "step_image_paths": step_image_paths,
        "strokes_data": strokes_data,
        "trace": {
            "intent": "canvas_analysis",
            "workflow_type": "simplified",
            "steps": []
        }
    }
    
    logger.info(f"🎨 Running simplified canvas analysis for session {session_id}")
    
    # Step 1: Vision Analysis
    logger.info("👁️ Step 1: Vision Analysis")
    state_after_vision = await vision_node(initial_state)
    
    # Step 2: Feedback Generation
    logger.info("🎓 Step 2: Feedback Generation")
    final_state = await feedback_node(state_after_vision)
    
    logger.info("✅ Canvas analysis complete")
    
    return final_state


async def run_tutor_workflow(
    session_id: str,
    student_id: str,
    full_canvas_path: str = None,
    canvas_dimensions: Dict[str, int] = None,
    steps_metadata: List[Dict] = None,
    step_image_paths: Dict[str, str] = None,
    strokes_data: List[Dict] = None,
    user_message: str = ""
) -> Dict[str, Any]:

    initial_state = {
        "session_id": session_id,
        "student_id": student_id,
        "full_canvas_path": full_canvas_path,
        "canvas_dimensions": canvas_dimensions or {},
        "steps_metadata": steps_metadata or [],
        "step_image_paths": step_image_paths or {},
        "strokes_data": strokes_data or [],
        "user_message": user_message,
        "trace": {
            "intent": None,
            "execution_plan": [],
            "current_step": 0,
            "next_action": "start",
            "steps": [],
            "agents_completed": [],
            "workflow_complete": False
        }
    }

    try:
        final_state = await tutor_workflow.ainvoke(initial_state)
        logger.info("✅ Workflow complete")
        logger.info(f"📊 Agents: {final_state['trace']['agents_completed']}")
        return final_state

    except Exception as e:
        logger.error(f"Error running tutor workflow: {e}")
        raise
