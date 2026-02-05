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
from app.services.ai_service import chat_with_ai
import uuid
from pathlib import Path
from fastapi import Request
from app.core.logging_context import request_id_ctx
from app.core.logging_config import setup_logging
from app.core.logger import get_logger
from app.core.config import settings

from .routers import canvas, upload, chat, get_documents, regions, steps

setup_logging(level="INFO")




logger = get_logger(__name__)

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

#app.include_router(canvas.router)
app.include_router(upload.router)
#app.include_router(chat.router)
app.include_router(get_documents.router)
#app.include_router(regions.router)
app.include_router(steps.router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    token = request_id_ctx.set(str(uuid.uuid4()))
    try:
        response = await call_next(request)
        return response
    finally:
        request_id_ctx.reset(token)

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



#root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Interactive AI Tutor!"}

#health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Interactive AI Tutor", "version": "0.0.1"}





        
