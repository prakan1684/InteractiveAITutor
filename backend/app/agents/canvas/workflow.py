from app.core.logger import get_logger
from .schema import CanvasState
from .vision_agent import VisionAgent
from .feedback_agent import FeedbackAgent
 
logger = get_logger(__name__)
 


async def run_canvas_workflow(session_id: str, canvas_path: str) -> dict:
    logger.info("Starting canvas workflow")


    state = CanvasState(
        session_id=session_id,
        canvas_path=canvas_path
    )

    vision_agent = VisionAgent()
    state = await vision_agent.analyze_canvas(state)
    feedback_agent = FeedbackAgent()
    state = await feedback_agent.generate(state)

    logger.info("Workflow complete")
    
    return {
        "session_id": state.session_id,
        "analysis": state.analysis,
        "feedback": state.feedback
    }

