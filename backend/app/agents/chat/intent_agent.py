from app.services.ai_service import AIService
from app.core.logger import get_logger
from .schema import ChatState
import json

logger = get_logger(__name__)

def format_conversation(messages: list) -> str:
    """Format conversation history for prompt"""
    if not messages:
        return "No previous conversation"
    
    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)

class IntentAgent:
    def __init__(self):
        self.ai = AIService()
    
    async def classify_and_decide(self, state: ChatState) -> ChatState:
        """Single LLM call to classify intent AND decide if canvas is needed."""
        logger.info(f"Classifying intent for: '{state.message[:50]}'")
        
        recent_messages = state.conversation_history[-10:]

        prompt = f"""You are an AI tutor with access to a student's digital canvas where they work on problems.

Given this student message and conversation history, do TWO things:

1. Classify the message into ONE intent:
   - canvas_review_request: Student wants their work checked/reviewed (e.g. "check my work", "is this right?", "can you help me with this?")
   - question: Student asking about a concept (e.g. "what is the quadratic formula?")
   - hint_request: Student is stuck and needs a hint (e.g. "I'm stuck", "I need help")
   - clarification: Student doesn't understand previous response (e.g. "what do you mean?")
   - general: General conversation (e.g. "hello", "thanks")

2. Decide if we need to look at the student's canvas:
   - YES if: student is asking about their work, is stuck on a problem, wants feedback, or visual context would help
   - NO if: general conceptual question, clarifying previous response, or general conversation

IMPORTANT: When students say "this question", "my work", "this problem", or "can you help me with this?" — they're referring to their canvas.

Recent conversation:
{format_conversation(recent_messages)}

Current message: "{state.message}"

Respond with ONLY valid JSON (no markdown, no explanation):
{{"intent": "<intent_name>", "needs_canvas": true/false}}"""

        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            raw = response.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            result = json.loads(raw)
            state.intent = result.get("intent", "general").strip().lower()
            state.needs_canvas = result.get("needs_canvas", False)
            
            logger.info(f"Intent: {state.intent}, needs_canvas: {state.needs_canvas}")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error in classify_and_decide: {e}")
            state.intent = "general"
            state.needs_canvas = False
        
        return state
