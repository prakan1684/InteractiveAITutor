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

    # Extract canvas work details
    canvas_details = "No canvas work available"
    if state.canvas_context:
        canvas_items = []
        for ctx in state.canvas_context:
            data = ctx.get("data", {})

            problem = data.get("problem_summary", "")
            expressions = data.get("expressions", [])
            is_correct = data.get("is_correct")
        
            # Fallback to old format (latex_expressions) for historical sessions
            if not expressions:
                expressions = data.get("latex_expressions", [])
        
            if problem:
                canvas_items.append(f"Problem: {problem}")
            if expressions:
                canvas_items.append(f"Expressions: {', '.join(expressions)}")
            if is_correct is not None:
                canvas_items.append(f"Correct: {is_correct}")
    
        if canvas_items:
            canvas_details = "; ".join(canvas_items)




    # Extract course material topics
    course_topics = "No course materials"
    if state.course_context:
        topics = [c.get('content', '')[:150] for c in state.course_context[:2]]
        course_topics = "; ".join(topics)

    reasoning_prompt = f"""You are an AI tutor. Analyze this student question and available context.

Student Question: {state.user_message}

Canvas Work: {canvas_details}

Course Materials: {course_topics}

Analyze and respond with a JSON object:
{{
  "key_concepts": ["list of 1-3 key concepts involved"],
  "knowledge_level": "beginner" | "intermediate" | "advanced",
  "approach": "how to best help this student (e.g., 'review their work', 'explain concept', 'provide practice')",
  "confidence": 0.0-1.0
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

        key_concepts = reasoning.get('key_concepts', [])
        approach = reasoning.get('approach', 'general guidance')
        state.reasoning_steps.append(f"Key concepts: {', '.join(key_concepts)}")
        state.reasoning_steps.append(f"Teaching approach: {approach}")
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

    # Format canvas context to show extracted work clearly
    canvas_summary = "No recent canvas work available."
    if state.canvas_context:
        canvas_parts = []
        for ctx in state.canvas_context:
            data = ctx.get("data", {})
            latex_expressions = data.get("latex_expressions", [])
            symbol_count = data.get("symbol_count", 0)
            session_id = data.get("session_id", "unknown")
            
            if latex_expressions:
                expressions_str = ", ".join(latex_expressions)
                canvas_parts.append(f"- Student wrote: {expressions_str} ({symbol_count} symbols)")
            else:
                canvas_parts.append(f"- Student submitted canvas work (session {session_id[:8]}...) but symbols were not fully recognized")
        
        canvas_summary = "\n".join(canvas_parts)
    
    # Format course materials
    course_summary = "No course materials found."
    if state.course_context:
        course_parts = [c.get('content', '')[:300] for c in state.course_context[:3]]
        course_summary = "\n\n".join(course_parts)

    response_prompt = f"""You are Pocket Professor, a warm and supportive AI tutor helping a student learn.

Student Question: "{state.user_message}"

=== STUDENT'S RECENT CANVAS WORK ===
{canvas_summary}

=== RELEVANT COURSE MATERIALS ===
{course_summary}

=== REASONING CONTEXT ===
{chr(10).join(state.reasoning_steps)}

INSTRUCTIONS:
1. If the student wrote mathematical expressions on their canvas, reference them specifically
2. Evaluate correctness: If they wrote something like "3 + 3", acknowledge it and gently guide them
3. Be encouraging and specific - avoid generic responses
4. If asking about their work, provide actionable feedback
5. Keep responses concise but educational (2-4 paragraphs max)
6. Use a warm, supportive tone appropriate for students

MATH FORMATTING:
- Use $...$ for inline math (e.g., $3 + 3 = 6$)
- Use $$...$$ for display equations on their own line
- Example: The sum is $3 + 3 = 6$

Provide your response now:
"""
    
    try:
        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.complete(
            messages=[{"role": "user", "content": response_prompt}],
            temperature=0.7,
        )

        state.final_response = response.content
        logger.info(f"✅ AI response generated: {len(response.content)} chars")

        # Generate contextual follow-up suggestions
        suggestions = []
        
        if state.canvas_context:
            # Student has canvas work - suggest practice or next steps
            suggestions.append("Would you like to try a similar problem?")
            suggestions.append("Should I explain any part in more detail?")
        else:
            # No canvas work - suggest general help
            suggestions.append("Would you like me to explain this concept?")
            suggestions.append("Do you want to see an example problem?")
        
        # Always offer to review previous work if available
        if state.canvas_context or state.course_context:
            suggestions.append("Want to review related material?")
        
        state.follow_up_suggestions = suggestions[:3]  # Keep max 3 suggestions

    except Exception as e:
        logger.error("Error responding: %s", e)
        state.final_response = "I'm sorry, I was unable to generate a response. Please try again."
        state.follow_up_suggestions = []
    
    return state




    
