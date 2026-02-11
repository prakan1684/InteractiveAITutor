import json
from pathlib import Path
from typing import AsyncGenerator
from app.core.logger import get_logger
from .schema import ChatState
from .intent_agent import IntentAgent
from .response_agent import ResponseAgent
from app.services.canvas_storage import canvas_storage
from app.agents.canvas.vision_agent import VisionAgent
from app.agents.canvas.schema import CanvasState
 
logger = get_logger(__name__)
 

async def run_chat_workflow(
    student_id: str,
    message: str,
    conversation_history: list,
) -> dict:
    """Run the chat workflow"""
    logger.info(f"Chat workflow - student={student_id}, msg='{message[:40]}'")
    
    state = ChatState(
        student_id=student_id,
        message=message,
        conversation_history=conversation_history,
    )

    #classify intent and decide if canvas is needed (single LLM call)
    intent_agent = IntentAgent()
    state = await intent_agent.classify_and_decide(state)
    
    # If canvas is needed, analyze the stored image on-demand
    if state.needs_canvas:
        image_path = canvas_storage.get_image_path(student_id)
        
        if not image_path:
            # No canvas image available yet
            state.needs_canvas = False
            state.response = "I don't see any work on your canvas yet. Please write something on the canvas and try again!"
            return {
                "response": state.response,
                "action": None,
                "intent": state.intent,
                "needs_canvas": False
            }
        
        # Check file actually exists on disk
        if not Path(image_path).exists():
            logger.error(f"Canvas image file missing: {image_path}")
            state.response = "I can't find your canvas image. Please write something on the canvas and try again!"
            return {
                "response": state.response,
                "action": None,
                "intent": state.intent,
                "needs_canvas": False
            }
        
        # Check if we have a cached analysis (image hasn't changed)
        cached = canvas_storage.get_analysis(student_id)
        if cached:
            logger.info("Using cached canvas analysis")
            state.recent_canvas_analysis = cached
        else:
            # Run vision analysis on-demand
            logger.info(f"Running on-demand vision analysis: {image_path}")
            try:
                vision_agent = VisionAgent()
                canvas_state = CanvasState(canvas_path=image_path, student_query=message)
                canvas_state = await vision_agent.analyze_canvas(canvas_state)
                
                if not canvas_state.analysis:
                    logger.error("Vision analysis returned empty")
                    state.response = "I had trouble reading your canvas. Please try again!"
                    return {
                        "response": state.response,
                        "action": None,
                        "intent": state.intent,
                        "needs_canvas": False
                    }
                
                # Extract analysis text
                raw = canvas_state.analysis
                if isinstance(raw, dict):
                    analysis_text = raw.get("analysis", str(raw))
                else:
                    analysis_text = str(raw)
                
                # Cache it
                canvas_storage.store_analysis(student_id, analysis_text)
                state.recent_canvas_analysis = analysis_text
                logger.info("Vision analysis complete and cached")
            except Exception as e:
                logger.error(f"Vision analysis failed: {e}")
                state.response = "I had trouble analyzing your canvas. Please try again!"
                return {
                    "response": state.response,
                    "action": None,
                    "intent": state.intent,
                    "needs_canvas": False
                }
        
        # Now generate response with canvas context
        state.needs_canvas = False
    
    #generate response
    response_agent = ResponseAgent()
    state = await response_agent.generate(state)
    
    logger.info(f"Chat workflow done - intent={state.intent}")

    return {
        "response": state.response,
        "action": None,
        "intent": state.intent,
        "needs_canvas": False
    }


async def run_chat_workflow_stream(
    student_id: str,
    message: str,
    conversation_history: list,
    conversation_id: str = "",
) -> AsyncGenerator[str, None]:
    """Streaming version — yields SSE events as the response generates."""
    logger.info(f"Chat workflow (stream) - student={student_id}, msg='{message[:40]}'")
    
    state = ChatState(
        student_id=student_id,
        message=message,
        conversation_history=conversation_history,
    )

    # Phase 1: classify intent (non-streamed, fast)
    yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...'})}\n\n"
    
    intent_agent = IntentAgent()
    state = await intent_agent.classify_and_decide(state)
    
    # Phase 2: vision analysis if needed (non-streamed)
    if state.needs_canvas:
        image_path = canvas_storage.get_image_path(student_id)
        
        if not image_path:
            state.needs_canvas = False
            msg = "I don't see any work on your canvas yet. Please write something on the canvas and try again!"
            yield f"data: {json.dumps({'type': 'chunk', 'content': msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'intent': state.intent, 'response': msg})}\n\n"
            return
        
        if not Path(image_path).exists():
            logger.error(f"Canvas image file missing: {image_path}")
            msg = "I can't find your canvas image. Please write something on the canvas and try again!"
            yield f"data: {json.dumps({'type': 'chunk', 'content': msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'intent': state.intent, 'response': msg})}\n\n"
            return
        
        # Only show canvas image if it's new/changed since last shown in this conversation
        image_is_new = canvas_storage.is_image_new_for_conversation(student_id, conversation_id)
        if image_is_new:
            image_url = f"/canvas_uploads/{'/'.join(Path(image_path).parts[-3:])}"
            yield f"data: {json.dumps({'type': 'canvas_image', 'image_url': image_url})}\n\n"
            canvas_storage.mark_image_shown(student_id, conversation_id)
        
        cached = canvas_storage.get_analysis(student_id)
        if cached:
            logger.info("Using cached canvas analysis")
            yield f"data: {json.dumps({'type': 'status', 'content': 'Reviewing your canvas...'})}\n\n"
            state.recent_canvas_analysis = cached
        else:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Looking at your canvas...'})}\n\n"
            logger.info(f"Running on-demand vision analysis: {image_path}")
            try:
                vision_agent = VisionAgent()
                canvas_state = CanvasState(canvas_path=image_path, student_query=message)
                canvas_state = await vision_agent.analyze_canvas(canvas_state)
                
                if not canvas_state.analysis:
                    msg = "I had trouble reading your canvas. Please try again!"
                    yield f"data: {json.dumps({'type': 'chunk', 'content': msg})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'intent': state.intent, 'response': msg})}\n\n"
                    return
                
                raw = canvas_state.analysis
                if isinstance(raw, dict):
                    analysis_text = raw.get("analysis", str(raw))
                else:
                    analysis_text = str(raw)
                
                canvas_storage.store_analysis(student_id, analysis_text)
                state.recent_canvas_analysis = analysis_text
                logger.info("Vision analysis complete and cached")
            except Exception as e:
                logger.error(f"Vision analysis failed: {e}")
                msg = "I had trouble analyzing your canvas. Please try again!"
                yield f"data: {json.dumps({'type': 'chunk', 'content': msg})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'intent': state.intent, 'response': msg})}\n\n"
                return
        
        state.needs_canvas = False
    
    # Phase 3: stream the response
    yield f"data: {json.dumps({'type': 'status', 'content': ''})}\n\n"
    
    response_agent = ResponseAgent()
    full_response = ""
    async for chunk in response_agent.generate_stream(state):
        full_response += chunk
        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
    
    logger.info(f"Chat workflow (stream) done - intent={state.intent}")
    yield f"data: {json.dumps({'type': 'done', 'intent': state.intent, 'response': full_response})}\n\n"