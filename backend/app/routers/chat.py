from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.schemas import ChatState
from app.agents.chat_graph import chat_graph



router = APIRouter()

from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatRequest(BaseModel):
    student_id: str
    message: str
    fast_mode: bool = False
    use_rag: bool = True

class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    canvas_context_count: int
    course_context_count: int
    reasoning_steps: list[str]
    follow_up_suggestions: list[str]
    status: str = "success"

@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    chat endpoint using langgraph with azure search rag

    """
    if not request.use_rag:
        return await _simple_chat(request)
    elif request.fast_mode:
        return await _fast_chat(request)
    else:
        return await _full_chat(request)



async def _fast_chat(request: ChatRequest) -> ChatResponse:
    """

    fast mode: skip graph and do direct rag
    """

    from app.services.ai_service import AIService
    from app.services.course_rag_service import CourseRAGService
    
    try: 
        course_service = CourseRAGService()
        results = course_service.search_materials(request.message, top_k=5)

        context = "\n\n".join([r['content'] for r in results])


        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.chat(
            user_message=request.message,
            context=context,
            system_prompt="You are a helpful AI tutor. Answer the student's question using the provided context."
        )

        return ChatResponse(
            response=response,
            intent="fast_mode",
            confidence=1.0,
            canvas_context_count=0,
            course_context_count=len(results),
            reasoning_steps=["Fast mode: direct RAG"],
            follow_up_suggestions=[],
            status="success"
        )
    except Exception as e:
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error"
        )

async def _simple_chat(request: ChatRequest) -> ChatResponse:
    """Simple mode: No RAG, just conversational AI"""
    from app.services.ai_service import AIService
    
    try:
        ai = AIService(default_model="gpt-4o-mini")
        response = await ai.chat(
            user_message=request.message,
            system_prompt="You are a helpful AI tutor. Provide clear, educational explanations."
        )
        
        return ChatResponse(
            response=response,
            intent="simple_chat",
            confidence=1.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=["Simple mode: no RAG"],
            follow_up_suggestions=[],
            status="success"
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
            status="error"
        )

async def _full_chat(request: ChatRequest) -> ChatResponse:
    """Full mode: Use graph with RAG"""
    try:
        initial_state = ChatState(
            student_id = request.student_id,
            user_message = request.message,
            intent = "unknown",
            needs_canvas_context = False,
            needs_course_context = False,
            canvas_context = [],
            course_context = [],
            reasoning_steps = [],
            tool_calls = [],
            final_response = "",
            follow_up_suggestions = [],
            confidence = 0.0,
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
            status="success"
        )

    except Exception as e:
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            confidence=0.0,
            canvas_context_count=0,
            course_context_count=0,
            reasoning_steps=[f"Error: {str(e)}"],
            follow_up_suggestions=[],
            status="error"
        )




