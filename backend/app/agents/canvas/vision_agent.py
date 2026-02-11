from app.services.vision import VisionService
from app.agents.canvas.schema import CanvasState

from app.core.logger import get_logger

logger = get_logger(__name__)

class VisionAgent:
    def __init__(self):
        self.vision = VisionService()
    
    async def analyze_canvas(self, state:CanvasState) -> CanvasState:
        logger.info(f"Analyzing canvas: {state.canvas_path}")

        # Build context-aware prompt based on student's question
        if state.student_query:
            prompt = f"""A student is asking: "{state.student_query}"

Look at their canvas and analyze what they've written. Specifically:
1. Describe exactly what the student wrote (equations, expressions, work shown)
2. Evaluate their work in the context of their question
3. Identify any errors or misconceptions
4. Note what steps they completed correctly

Be precise about what you see — reference specific numbers, symbols, and expressions."""
        else:
            prompt = """Analyze this student's canvas work:
1. Describe exactly what the student wrote (equations, expressions, work shown)
2. Is their work correct? If not, identify specific errors
3. Note what steps they completed correctly"""

        analysis = self.vision.analyze_image(state.canvas_path, prompt)
        logger.info(f"Vision analysis complete - success={analysis.get('success', False)}")
        state.analysis = analysis
        return state