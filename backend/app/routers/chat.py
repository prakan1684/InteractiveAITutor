from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import chat_with_ai
from app.services.multimodel_processor import MultimodelProcessor



router = APIRouter()

from app.core.logger import get_logger

logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        context_to_use = None
        #use multimodal RAG

        if request.use_rag:
            processor = MultimodelProcessor()

            search_results = processor.search_content(query=request.message, top_k=5)

            if search_results['status'] == "success" and search_results['results']:
                context_parts = []
                for result in search_results['results']:
                    content_type = result['content_type']
                    source_info = result['source_info']


                    if content_type == "image":
                        image_info = f"Image: {source_info['file_name']}"
                        context_parts.append(f"{image_info}\n\n{result['content']}")
                    else:
                        context_parts.append(f"{source_info['type']}\n\n{result['content']}")
                
                context_to_use = "\n\n---\n\n".join(context_parts)
                context_to_use = f"Here is the context for the query: '{request.message}': \n\n{context_to_use}"

                #send to ai with context
                ai_response = await chat_with_ai(
                    message=request.message,
                    context=context_to_use
                )
                return ChatResponse(
                    response=ai_response,
                    status="success"
                )
        else:
            #send to ai without context
            ai_response = await chat_with_ai(
                message=request.message,
                context=""
            )
            return ChatResponse(
                response=ai_response,
                status="success"
            )
    except Exception as e:
        return ChatResponse(
            response=str(e),
            status="error"
        )