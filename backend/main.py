"""
Entry point for the FastAPI application.



1. Initialize the FastAPI application.
2. CORS middleware to allow cross-origin requests.
3. Basic Health Check endpoint.
4. root endpoint
"""



from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ai_service import chat_with_ai
import os
from pathlib import Path

class ChatRequest(BaseModel):
    message: str
    document_name: str = None 
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

        #use RAG is document specified
        if request.use_rag and request.document_name:
            from document_processor import retrieve_relevant_chunks

            relevant_chunks = retrieve_relevant_chunks(
                query = request.message,
                document_name = request.document_name,
                top_k=3
            )

            if relevant_chunks:
                #combine chunk texts as context
                chunks_text = [chunk['text'] for chunk in relevant_chunks]
                context_to_use = "\n\n---\n\n".join(chunks_text)

                context_to_use = f"Here is the context for the query: '{request.message}': \n\n{context_to_use}"
        #send to AI with context
        ai_response = await chat_with_ai(request.message, context_to_use)

        return ChatResponse(response=ai_response, status="success")
            
    except Exception as e:
        return ChatResponse(response=str(e), status="error")



@app.get("/documents")
async def get_documents():
    #get list of documents from processed directory
    from document_processor import get_available_documents
    documents = get_available_documents()
    return {
        "documents": documents,
        "count": len(documents),
        "status": "success"
    }


@app.post("/upload")
async def upload_document(file: UploadFile=File(...)):
    """
    Upload a document for processing.
    """
    try:
        if not file.filename.endswith(".pdf"):
            return {"error": "Only PDF files are allowed."}

        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        #save uploaded file
        file_path = upload_dir / file.filename #combines upload_dir and file.filename
        with open(file_path, "wb") as buffer: #writing in binary mode to save the file
            content = await file.read()
            buffer.write(content)

        
        #process document immediately
        from document_processor import process_document
        processing_result = process_document(str(file_path))

        

        return {
            "message": f"File {file.filename} uploaded successfully. File saved as {file_path}",
            "filename": file.filename,
            "file_path": str(file_path),
            "processing_result": processing_result,
            "status": "success"
        }

    except Exception as e:
        return {"error": str(e), "status": "error"}

