import json
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.conversation_manager import conversation_manager
from typing import Optional

router = APIRouter()

from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatRequest(BaseModel):
    student_id: str
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    action: Optional[str] = None
    intent: str
    conversation_id: str
    status: str = "success"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Simplified chat endpoint using chat workflow"""
    logger.info(f"Chat request - student={request.student_id}, msg='{request.message[:50]}', conv={request.conversation_id}")
    try:
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # Get conversation history
        history = conversation_manager.get_conversation_history(conversation_id, limit=10)
        
        # Store user message
        conversation_manager.store_message(
            conversation_id=conversation_id,
            student_id=request.student_id,
            role="user",
            content=request.message,
            mode="simple",
            metadata={}
        )
        
        # Run chat workflow (handles canvas analysis on-demand internally)
        from app.agents.chat.workflow import run_chat_workflow
        
        result = await run_chat_workflow(
            student_id=request.student_id,
            message=request.message,
            conversation_history=history,
        )
        
        # Store assistant response
        conversation_manager.store_message(
            conversation_id=conversation_id,
            student_id=request.student_id,
            role="assistant",
            content=result["response"],
            mode="simple",
            metadata={"intent": result["intent"]}
        )
        
        logger.info(f"Chat complete - intent={result['intent']}, action={result['action']}, conv={conversation_id}")
        
        return ChatResponse(
            response=result["response"],
            action=result["action"],
            intent=result["intent"],
            conversation_id=conversation_id,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error. Please try again.",
            intent="error",
            action=None,
            conversation_id=request.conversation_id or "error",
            status="error"
        )




@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint — returns SSE events."""
    logger.info(f"Chat stream request - student={request.student_id}, msg='{request.message[:50]}', conv={request.conversation_id}")
    
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    history = conversation_manager.get_conversation_history(conversation_id, limit=10)
    
    conversation_manager.store_message(
        conversation_id=conversation_id,
        student_id=request.student_id,
        role="user",
        content=request.message,
        mode="simple",
        metadata={}
    )
    
    from app.agents.chat.workflow import run_chat_workflow_stream
    
    async def event_generator():
        # Send conversation_id first so frontend has it immediately
        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conversation_id})}\n\n"
        
        full_response = ""
        intent = "general"
        
        async for event in run_chat_workflow_stream(
            student_id=request.student_id,
            message=request.message,
            conversation_history=history,
            conversation_id=conversation_id,
        ):
            yield event
            
            # Parse the done event to capture final response for storage
            if event.startswith("data: "):
                try:
                    payload = json.loads(event[6:].strip())
                    if payload.get("type") == "done":
                        full_response = payload.get("response", "")
                        intent = payload.get("intent", "general")
                except json.JSONDecodeError:
                    pass
        
        # Store assistant response after streaming completes
        if full_response:
            conversation_manager.store_message(
                conversation_id=conversation_id,
                student_id=request.student_id,
                role="assistant",
                content=full_response,
                mode="simple",
                metadata={"intent": intent}
            )
            logger.info(f"Chat stream complete - intent={intent}, conv={conversation_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
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







