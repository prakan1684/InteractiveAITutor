
from fastapi import APIRouter
from fastapi import File, UploadFile
from pathlib import Path
import uuid
from app.core.logger import get_logger 
from app.services.course_rag_service import CourseRAGService
from app.services.vision import VisionService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile=File(...)):
    """
    Upload a document for processing and indexing to Azure Search.
    Supports PDFs (course materials) and images (vision analysis).
    """
    try:
        file_extension = Path(file.filename).suffix.lower()
        supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

        if file_extension not in supported_extensions:
            return {
                "error": "Unsupported file type. Only PDF, JPG, JPEG, PNG, GIF, BMP, and WEBP files are allowed.", 
                "status": "error"
            }
            
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"Processing {file.filename} ({file_extension})")

        if file_extension == '.pdf':
            course_service = CourseRAGService()
            result = course_service.upload_pdf(str(file_path))
            
            return {
                "message": f"PDF {file.filename} uploaded to Azure Search successfully.",
                "filename": file.filename,
                "file_path": str(file_path),
                "file_type": "document",
                "chunks_uploaded": result.get("chunks_uploaded", 0),
                "status": "success"
            }
        else:
            vision_service = VisionService()
            analysis = vision_service.analyze_image(str(file_path))
            
            return {
                "message": f"Image {file.filename} analyzed successfully.",
                "filename": file.filename,
                "file_path": str(file_path),
                "file_type": "image",
                "analysis": analysis,
                "status": "success"
            }
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {
            "error": str(e),
            "status": "error"
        }