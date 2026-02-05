from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.schemas import ChatState

from app.services.conversation_manager import conversation_manager
from typing import Optional, Dict
import uuid
from app.services.ai_service import AIService
from app.services.course_rag_service import CourseRAGService



router = APIRouter()

from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatRequest(BaseModel):
    student_id: str
    message: str
    fast_mode: bool = False
    use_rag: bool = True
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    canvas_context_count: int
    course_context_count: int
    reasoning_steps: list[str]
    follow_up_suggestions: list[str]
    status: str = "success"
    conversation_id: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with mode selection"""
    logger.info(f"💬 Chat request - student_id={request.student_id}, mode={'full' if not request.fast_mode else 'fast' if request.use_rag else 'simple'}, conv_id={request.conversation_id}")
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Get conversation history
        history = conversation_manager.get_conversation_history(conversation_id, limit=10)
        
        # Store user message
        logger.info(f"💾 Storing user message...")
        conversation_manager.store_message(
            conversation_id=conversation_id,
            student_id=request.student_id,
            role="user",
            content=request.message,
            mode="simple" if not request.use_rag else ("fast" if request.fast_mode else "full"),
            metadata={
                "intent": "unknown",
                "confidence": 0.0,
                "course_context_count": 0,
                "canvas_context_count": 0
            }
        )
        logger.info(f"✅ User message stored - conversation_id={conversation_id}")
        
        # Route to appropriate chat mode
        if not request.use_rag:
            response_obj = await _simple_chat(request, history)
        elif request.fast_mode:
            response_obj = await _fast_chat(request, history)
        else:
            response_obj = await _full_chat(request, history)
        
        # Store assistant response
        logger.info(f"💾 Storing assistant response...")
        conversation_manager.store_message(
            conversation_id=conversation_id,
            student_id=request.student_id,
            role="assistant",
            content=response_obj.response,
            mode="simple" if not request.use_rag else ("fast" if request.fast_mode else "full"),
            metadata={
                "intent": response_obj.intent,
                "confidence": response_obj.confidence,
                "course_context_count": response_obj.course_context_count,
                "canvas_context_count": response_obj.canvas_context_count
            }
        )
        logger.info(f"✅ Assistant response stored - conversation_id={conversation_id}")
        
        # Set conversation_id and return
        response_obj.conversation_id = conversation_id
        logger.info(f"🎉 Chat response complete - {len(response_obj.response)} chars")
        return response_obj
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error",
            conversation_id=request.conversation_id or "error"
        )


async def _fast_chat(request: ChatRequest, history:list[Dict]) -> ChatResponse:
    """Fast mode: skip graph and do direct RAG"""

    
    try: 

        messages = []
        for msg in history[-5:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        course_service = CourseRAGService()
        results = course_service.search_materials(request.message, top_k=5)
        context = "\n\n".join([r['content'] for r in results])
        
        # Add system message with context
        messages.insert(0, {
            "role": "system",
            "content": f"""You are a helpful AI tutor. Answer the student's question using the provided context:

{context}

IMPORTANT: When including mathematical equations:
- Use $...$ for inline math (e.g., $x^2 + y^2 = z^2$)
- Use $$...$$ for display math on its own line
- Use proper LaTeX syntax within the delimiters
- Example: The integral is $\\int_{{a}}^{{b}} f(x) dx$"""
        })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })

        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.complete(
            messages=messages,
            temperature=0.7
        )

        return ChatResponse(
            response=response.content,
            intent="fast_mode",
            confidence=1.0,
            canvas_context_count=0,
            course_context_count=len(results),
            reasoning_steps=["Fast mode: direct RAG"],
            follow_up_suggestions=[],
            status="success",
            conversation_id=None
        )
    except Exception as e:
        logger.error(f"Fast chat error: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error",
            conversation_id=None
        )

async def _simple_chat(request: ChatRequest, history: list[Dict]) -> ChatResponse:
    """Simple mode: No RAG, just conversational AI"""
    from app.services.ai_service import AIService
    
    try:

        messages = []
        for msg in history[-5:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        # Add system message for simple chat
        messages.insert(0, {
            "role": "system",
            "content": """You are a helpful AI tutor. Provide clear, educational explanations.

IMPORTANT: When including mathematical equations:
- Use $...$ for inline math (e.g., $x^2 + y^2 = z^2$)
- Use $$...$$ for display math on its own line
- Use proper LaTeX syntax within the delimiters
- Example: The quadratic formula is $x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}$"""
        })
        
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.complete(
            messages=messages,
            temperature=0.7
        )
        
        return ChatResponse(
            response=response.content,
            intent="simple_chat",
            confidence=1.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=["Simple mode: no RAG"],
            follow_up_suggestions=[],
            status="success",
            conversation_id=None
        )
    except Exception as e:
        logger.error(f"Simple chat error: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error",
            conversation_id = None
        )

async def _full_chat(request: ChatRequest, history: list[Dict]) -> ChatResponse:
    """Full mode: Use graph with RAG"""
    try:
        messages = []
        for msg in history[-5:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({
            "role": "user",
            "content": request.message
        })

        initial_state = ChatState(
            student_id=request.student_id,
            conversation_history=history,
            user_message=request.message,
            intent="unknown",
            needs_canvas_context=False,
            needs_course_context=False,
            canvas_context=[],
            course_context=[],
            reasoning_steps=[],
            tool_calls=[],
            final_response="",
            follow_up_suggestions=[],
            confidence=0.0,
        )

        final_state = await chat_graph.ainvoke(initial_state)
        
        return ChatResponse(
            response=final_state['final_response'],
            intent=final_state['intent'],
            confidence=final_state['confidence'],
            canvas_context_count=len(final_state['canvas_context']),
            course_context_count=len(final_state['course_context']),
            reasoning_steps=final_state['reasoning_steps'],
            follow_up_suggestions=final_state['follow_up_suggestions'],
            status="success",
            conversation_id=None
        )

    except Exception as e:
        logger.error(f"Full chat error: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error",
            conversation_id=None
        )

@router.get("/conversations/{student_id}")
async def get_conversations(student_id: str):
    """Get list of conversations for a student"""
    conversations = conversation_manager.get_student_conversations(student_id)
    return {"conversations": conversations, "status": "success"}

@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history"""
    messages = conversation_manager.get_conversation_history(conversation_id)
    return {"messages": messages, "status": "success"}

@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = conversation_manager.delete_conversation(conversation_id)
    return {"success": success, "status": "success" if success else "error"}


@router.post("/analyze-canvas-chat")
async def analyze_canvas_chat(request: ChatRequest):
    logger.info(f"🎨 Canvas analysis chat requested - student_id={request.student_id}")
    from app.services.session_manager import session_manager

    recent_canvas = session_manager.get_recent_context(
        request.student_id,
        
    )
    logger.info(f"🔍 Recent canvas search result: {'Found' if recent_canvas else 'Not found'}")

    if not recent_canvas:
        logger.warning(f"⚠️ No recent canvas found for student_id={request.student_id}")
        return ChatResponse(
            response="I couldn't find any recent canvas work. Please submit your work from the iOS app first.",
            intent="no_canvas_found",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=["No canvas found"],
            follow_up_suggestions=["Try submitting your work from the iOS app"],
            status="error",
            conversation_id=None
        )

    canvas_summary = f"Session: {recent_canvas.get('session_id')}, Symbols: {recent_canvas.get('symbol_count')}"
    logger.info(f"✅ Canvas found - {canvas_summary}")
    
    request.message = f"analyze my recent canvas work: {recent_canvas}"
    request.use_rag = True
    request.fast_mode = False
    
    logger.info(f"➡️ Forwarding to chat endpoint with canvas context")
    return await chat(request)




