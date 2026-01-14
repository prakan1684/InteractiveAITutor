
from fastapi import APIRouter
from fastapi import File, UploadFile
from pathlib import Path
import uuid
from app.core.logger import get_logger 
from app.services.multimodel_processor import MultimodelProcessor

logger = get_logger(__name__)







router = APIRouter()


@router.post("/upload")
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