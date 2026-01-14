from app.agents.schemas import ChatState
from app.services.ai_service import AIService
from app.services.session_manager import session_manager
import asyncio
from app.core.logger import get_logger

logger = get_logger(__name__)

"""
Langgraph nodes for chat

"""


async def classify_intent(state: ChatState) -> ChatState:
    """
    Classifies the intent of the user message
    Decides what context and tools to use


    Responsibilities:
    - Analyze user message
    - Set intent field
    - set needs_* flags for downstream nodes
    """

    logger.info("Classifying intent for message: %s", state.user_message[:50])

    # Build classification prompt
    classification_prompt = f"""Analyze this student message and classify the intent.
Message: "{state.user_message}"
Respond in JSON format:
{{
    "intent": "canvas_review" | "concept_question" | "problem_solving" | "general",
    "needs_canvas_context": true/false,
    "needs_course_context": true/false,
    "needs_tools": true/false,
    "reasoning": "brief explanation of classification"
}}
Intent definitions:
- canvas_review: Student asking about their recent canvas work ("Can you check my work?", "Is this right?", "Did I make a mistake?")
- concept_question: Asking to explain a concept ("What is...", "Explain...", "Why does...")
- problem_solving: Asking for help solving a problem ("How do I solve...", "Help me with...")
- general: Greetings, thanks, off-topic, chitchat
Context needs:
- needs_canvas_context: true if student references "my work", "what I drew", "my answer", etc.
- needs_course_context: true if question is about concepts, formulas, or problem-solving
- needs_tools: true if question involves calculation, code execution, or needs computation
"""
    try:
        ai = AIService(default_model="gpt-4o-mini")
        result = await ai.classify(
            text = state.user_message,
            classification_prompt=classification_prompt
        )

        state.intent = result['intent']
        state.needs_canvas_context = result['needs_canvas_context']
        state.needs_course_context = result['needs_course_context']
        state.needs_tools = result['needs_tools']

        state.reasoning_steps.append(
            f"Intent: {result['intent']} | Canvas: {result['needs_canvas_context']} | "
            f"Course: {result['needs_course_context']} | Tools: {result['needs_tools']} | "
            f"Reason: {result['reasoning']}"
        )

        logger.info("Intent classified: %s", state.intent)

        return state
    except Exception as e:
        logger.error("Error classifying intent: %s", e)
        #fallbacks
        state.intent = "concept_question"
        state.needs_canvas_context = False
        state.needs_course_context = True
        state.needs_tools = False
        state.reasoning_steps.append(f"Classification failed, using fallback: {str(e)}")
        
        return state

async def retrieve_context(state: ChatState) -> ChatState:
    """
    Retrieves context for the given intent
    
    Responsibilities:
    - Retrieve canvas context if needed
    - Retrieve course context if needed
    - populate context fields in state

    """

    if state.needs_canvas_context:
        canvas_context= []
        recent = session_manager.get_recent_context(state.student_id)
        if recent:
            canvas_context.append({
                "source": "recent_session",
                "age": "<30 min",
                "data": recent
            })
        
        #strat 2, historical canvas sessions
        historical = session_manager.search_canvas_history(
            student_id=state.student_id,
            query=state.user_message,
            top_k=5
        )

        for session in historical:
            canvas_context.append({
                "source": "historical_session",
                "score": session.get("score", 0.0),
                "data": session
            })
        
        if len(canvas_context) == 0:
            state.reasoning_steps.append("No Canvas Context found")
        

        state.canvas_context = canvas_context
    


    
