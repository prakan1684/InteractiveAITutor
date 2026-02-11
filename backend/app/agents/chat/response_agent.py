from typing import AsyncGenerator
from app.services.ai_service import AIService
from app.core.logger import get_logger
from .schema import ChatState

logger = get_logger(__name__)

class ResponseAgent:
    def __init__(self):
        self.ai = AIService()
    
    def _build_messages(self, state: ChatState) -> list:
        """Build the message list for the LLM call."""
        system_prompt = """You are an AI tutor with access to a digital canvas where students work on math problems.

Your capabilities:
- Students write their work on a digital canvas (like a whiteboard)
- You can view their canvas at any time to see what they've written
- When students mention "this question", "my work", "this problem", they're referring to what's on their canvas

Your role:
- Help students learn through guidance, not just answers
- When students are stuck, look at their canvas to understand where they need help
- Provide encouraging, clear explanations
- Use hints rather than giving away solutions

CONVERSATION CONTEXT RULES (very important):
1. ALWAYS read the full conversation history before responding. The student's current message is a continuation of the ongoing dialogue.
2. When a student says "this time", "again", "now", "did I get it right?", or "did I fix it?" — they are referring to a RETRY of the same problem discussed earlier in the conversation. Compare their current canvas work to what was discussed before.
3. If the student previously got something wrong and now shows corrected work, CELEBRATE their progress! Say things like "Great job fixing that!" or "You got it right this time!"
4. NEVER interpret casual phrases like "this time" as introducing a new topic (e.g., do NOT interpret "this time" as asking about the concept of time). Always interpret such phrases in the context of the ongoing conversation.
5. If the canvas shows work related to what was previously discussed, connect your feedback to that earlier discussion — don't treat it as a brand new problem.

FORMATTING:
- Use LaTeX formatting for ALL mathematical expressions:
  - Inline math: $expression$
  - Display math: $$expression$$
  - Example: $\\frac{d}{dx} 4x^2 = 8x$

CANVAS FEEDBACK:
- If you have recent canvas analysis in the context below, use it to provide SPECIFIC feedback about their work. Reference what they actually wrote and guide them from there.
- When the student has corrected a previous mistake, acknowledge the correction explicitly."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in state.conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        if state.recent_canvas_analysis:
            messages.append({
                "role": "system",
                "content": f"Recent canvas analysis: {state.recent_canvas_analysis}"
            })
        
        messages.append({
            "role": "user",
            "content": state.message
        })
        
        return messages

    async def generate(self, state: ChatState) -> ChatState:
        """Generate response based on intent (non-streaming)"""
        logger.info(f"Generating response for intent: {state.intent}")
        
        messages = self._build_messages(state)
        
        response = await self.ai.complete(
            messages=messages,
            temperature=0.7
        )
        
        state.response = response.content
        state.action = None
        
        logger.info("Response generated")
        return state

    async def generate_stream(self, state: ChatState) -> AsyncGenerator[str, None]:
        """Generate response as a stream of chunks."""
        logger.info(f"Streaming response for intent: {state.intent}")
        
        messages = self._build_messages(state)
        
        full_response = ""
        async for chunk in self.ai.complete_stream(messages=messages, temperature=0.7):
            full_response += chunk
            yield chunk
        
        state.response = full_response
        state.action = None
        logger.info("Streaming response complete")