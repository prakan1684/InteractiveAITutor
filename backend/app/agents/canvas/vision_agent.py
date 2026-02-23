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
 
Look at their canvas and analyze what they've written. Follow these rules:
 
READING ACCURACY (critical):
- Read EVERY character precisely — pay special attention to negative signs, minus signs, decimal points, and superscripts
- If you see a dash/minus before a number, it IS a negative sign. Report it as negative.
- Distinguish between: minus sign (subtraction operator), negative sign (before a number), and dashes
- Report fractions exactly as written (e.g., 8/3, not "eight thirds")
- If any character is ambiguous, state what it most likely is AND note the ambiguity
 
ANALYSIS:
1. Transcribe exactly what the student wrote — every line, every symbol, preserving their layout
2. Mathematically verify each step of their work (actually compute it yourself)
3. If their final answer is wrong, identify the EXACT step where the error occurred
4. Note what steps they completed correctly
 
IMPORTANT: Do NOT assume the student's work is correct. Always verify by computing the answer yourself independently."""
        else:
            prompt = """Analyze this student's canvas work:
 
READING ACCURACY (critical):
- Read EVERY character precisely — pay special attention to negative signs, minus signs, decimal points, and superscripts
- If you see a dash/minus before a number, it IS a negative sign. Report it as negative.
- Report fractions exactly as written
 
ANALYSIS:
1. Transcribe exactly what the student wrote — every line, every symbol
2. Mathematically verify each step (compute the answer yourself)
3. If their answer is wrong, identify the EXACT step where the error occurred
4. Note what steps they completed correctly"""

        analysis = self.vision.analyze_image(state.canvas_path, prompt)
        logger.info(f"Vision analysis complete - success={analysis.get('success', False)}")
        state.analysis = analysis
        return state