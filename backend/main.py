"""
Entry point for the FastAPI application.



1. Initialize the FastAPI application.
2. CORS middleware to allow cross-origin requests.
3. Basic Health Check endpoint.
4. root endpoint
"""



from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ai_service import chat_with_ai
from canvas_analyzer import CanvasAnalyzer
from typing import Dict, Optional
import uuid
import os
from pathlib import Path

class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True


class ChatResponse(BaseModel):
    response: str
    status: str = "success"


app = FastAPI(
    title = "Interactive AI Tutor",
    description = "An AI-powered tutoring system that helps students learn from their textbooks and study materials through interactive conversations.",
    version = "0.0.1"
)


# Adding cors middleware
# CORS allows frontend on port 3000 to talk to backend on port 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080", 
        "http://[::]:8080",        # Add IPv6 support
        "http://[::1]:8080",       # Add IPv6 localhost
        "*"  # Allow all origins for local development
    ],      
    allow_credentials=True,
    allow_methods=["*"], # Allows all HTTP methods like GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Allows all headers
)

# Creating Endpoint


#root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Interactive AI Tutor!"}

#health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Interactive AI Tutor", "version": "0.0.1"}


#chat endpoint
@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        context_to_use = None
        #use multimodal RAG

        if request.use_rag:
            from multimodel_processor import MultimodelProcessor

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

                



@app.get("/documents")
async def get_documents():
    #get list of documents from processed directory
    try:
        from document_processor import get_available_documents
        documents = get_available_documents()

        #collection info for debugging purposes
        from document_processor import chroma_client
        collections = chroma_client.list_collections()
        collection_info = []
        for collection in collections:
            info = {
                "name":collection.name,
                "id": collection.id if hasattr(collection, "id") else None,
                "metadata": collection.metadata if hasattr(collection, "metadata") else {},
            }

            try:
                count = collection.count()
                info["document_count"] = count
            except:
                info["document_count"] = "Unknown"

            collection_info.append(info)

        return {
            "documents": documents,
            "collections": collection_info,
            "status": "success"
        }       
    except Exception as e:
        return {
            "error":str(e),
            "status":"error"
        }
    


@app.post("/upload")
async def upload_document(file: UploadFile=File(...)):
    """
    Upload a document for processing.
    """
    try:
        #checking file extenstion
        file_extension = Path(file.filename).suffix.lower()
        supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

        if file_extension not in supported_extensions:
            return {"error": "Unsupported file type. Only PDF, JPG, JPEG, PNG, GIF, BMP, and WEBP files are allowed.", "status": "error"}
            
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok = True)
        #save uploaded file 

        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        #process using multimodal processor
        from multimodel_processor import MultimodelProcessor
        processor = MultimodelProcessor()
        processing_result = processor.process_any_document(str(file_path))

        if processing_result['status'] != "success":
            return {"error": processing_result['error'], "status": "error"}
        return {
            "message": f"File {file.filename} uploaded and processed successfully.",
            "filename": file.filename,
            "file_path": str(file_path),
            "file_type": "image" if file_extension != ".pdf" else "document",
            "processing_result": processing_result,
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@app.post("/analyze-canvas")
async def analyze_canvas(
    image: UploadFile = File(...),
):
    """
    Analyze a students canvas drawing and provide real-time feedback

    Automatically detects problem type and context
    Args:
        image (UploadFile): The image to analyze
        context (Optional[str]): The context of the problem
        problem_type (Optional[str]): The type of the problem
        auto_detect (bool): Whether to automatically detect problem type and context

    Returns:
        Dict: The analysis results
    """


    try:
        #create a dir for canvas uploads

        canvas_dir = Path("canvas_uploads")
        canvas_dir.mkdir(exist_ok=True)

        #save uploaded file to canvas dir
        file_extention = Path(image.filename).suffix
        unique_filename = f"canvas_{uuid.uuid4()}{file_extention}"
        file_path = canvas_dir / (unique_filename)


        #open file
        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        

        print(f"Canvas image saved to {file_path}")

        #analyze canvas with automatic detection
        analyzer = CanvasAnalyzer()


        analysis_result = analyzer.analyze_student_work(str(file_path))
        annotations_result = analyzer.annotate_student_work(str(file_path))


        #remove the uplaoded file
        file_path.unlink()

        return {
            # analysis
            "status": analysis_result.get("status", "error"),
            "feedback": analysis_result.get("feedback"),
            "context": analysis_result.get("context"),
            "problem_type": analysis_result.get("problem_type"),
            # annotations
            "annotations": annotations_result.get("annotations", [])
                if annotations_result.get("status") == "success" else [],
            "annotation_metadata": annotations_result.get("metadata", {})
                if annotations_result.get("status") == "success" else {},
            "annotation_status": annotations_result.get("status"),
            "annotation_error": annotations_result.get("error")
                if annotations_result.get("status") != "success" else None,
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

        
