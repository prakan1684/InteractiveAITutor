from app.agents.schemas import ChatState
from app.services.ai_service import AIService
from app.services.session_manager import session_manager
from app.services.course_rag_service import CourseRAGService
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
        state.needs_canvas_context = result.get("needs_canvas_context", False)
        state.needs_course_context = result.get("needs_course_context", False)
        state.confidence = result.get("confidence", 0.0)
        state.reasoning_steps.append(f"Intent: {state.intent} (confidence: {state.confidence:.2f})")
        
        logger.info(f"✅ Intent classified: {state.intent} (confidence: {state.confidence:.2f}, canvas: {state.needs_canvas_context}, course: {state.needs_course_context})")

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
    logger.info(f"📚 Retrieving context - canvas: {state.needs_canvas_context}, course: {state.needs_course_context}")

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
            logger.info("ℹ️ No canvas context found")
        else:
            logger.info(f"✅ Canvas context retrieved: {len(canvas_context)} items")
        

        state.canvas_context = canvas_context
        state.reasoning_steps.append(f"Canvas Context retrieved {len(canvas_context)} items")

    if state.needs_course_context:
        course_service = CourseRAGService()
        course_context = course_service.search_materials(state.user_message, top_k=5)
        state.course_context = course_context
        state.reasoning_steps.append(f"Course Context retrieved {len(course_context)} items")
        logger.info(f"✅ Course context retrieved: {len(course_context)} items")
    
    logger.info(f"📚 Context retrieval complete - canvas: {len(state.canvas_context)}, course: {len(state.course_context)}")
    return state


async def reason(state: ChatState) -> ChatState:
    """
    Reasons about the users question and retrieved context
    """

    #build context summary
    context_summary = []

    if state.canvas_context:
        context_summary.append(f"Context from Canvas: {len(state.canvas_context)} items")
    if state.course_context:
        context_summary.append(f"Context from Course: {len(state.course_context)} items")
    

    reasoning_prompt = f"""You are an AI tutor. Analyze this student question and available context.

Student Question: {state.user_message}

Available Context:
{chr(10).join(context_summary)}

Canvas Context:
{state.canvas_context[:2] if state.canvas_context else "None"}

Course Materials:
{[c['content'][:200] for c in state.course_context[:2]] if state.course_context else "None"}

Respond with a JSON object in this exact format:
{{
  "key_concepts": ["concept1", "concept2"],
  "knowledge_level": "beginner",
  "approach": "brief description of best teaching approach",
  "confidence": 0.85
}}
"""
    try:
        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.complete(
            messages = [{"role": "user", "content": reasoning_prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        import json
        reasoning = json.loads(response.content)

        state.reasoning_steps.append(f"Reasoning: {reasoning.get('key_concepts', 'N/A')}")
        state.confidence = reasoning.get('confidence', 0.0)
    except Exception as e:
        logger.error("Error reasoning: %s", e)
        state.reasoning_steps.append(f"Reasoning failed: {str(e)}")
        state.confidence = 0.0
    
    return state


async def respond(state: ChatState) -> ChatState:
    """
    Generate final response to student 
    """
    logger.info(f"💭 Generating AI response with {len(state.canvas_context)} canvas + {len(state.course_context)} course contexts")

    response_prompt = f"""You are a helpful AI tutor. Answer the student's question using the provided context.

Student Question: {state.user_message}

Canvas History:
{state.canvas_context if state.canvas_context else "No recent work"}

Course Materials:
{[c['content'] for c in state.course_context[:3]] if state.course_context else "No materials found"}

Reasoning:
{chr(10).join(state.reasoning_steps)}

Provide a clear, educational response. If referencing their past work, be specific.

IMPORTANT: When including mathematical equations:
- Use $...$ for inline math (e.g., $x^2 + y^2 = z^2$)
- Use $$...$$ for display math on its own line
- Use proper LaTeX syntax within the delimiters
- Example: The quadratic formula is $x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}$
"""
    
    try:
        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.complete(
            messages=[{"role": "user", "content": response_prompt}],
            temperature=0.7,
        )

        state.final_response = response.content
        logger.info(f"✅ AI response generated: {len(response.content)} chars")

        state.follow_up_suggestions = [
            "Would you like me to explain any concept in more detail?",
            "Do you want to see similar problems?",
            "Should I review your previous work?"
        ]

    except Exception as e:
        logger.error("Error responding: %s", e)
        state.final_response = "I'm sorry, I was unable to generate a response. Please try again."
        state.follow_up_suggestions = []
    
    return state




    
