from app.services.ai_service import AIService
from app.core.logger import get_logger
from .schema import CanvasState

logger = get_logger(__name__)

class FeedbackAgent:
    def __init__(self):
        self.ai = AIService()

    
    async def generate(self, state: CanvasState) -> CanvasState:
        """Generate feedback from analysis - that's it"""
        logger.info("Generating feedback")
        
        prompt = f"""Based on this analysis of student work:
{state.analysis}
 
Generate encouraging feedback for the student. Keep it simple and helpful.

IMPORTANT: Preserve any LaTeX math notation from the analysis. Use LaTeX formatting for all mathematical expressions:
- Inline math: $expression$
- Display math: $$expression$$
- For example: $\\frac{{d}}{{dx}} 4x^2 = 8x$"""
        
        response = await self.ai.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        state.feedback = response.content
        logger.info("Feedback generated")
        
        return state