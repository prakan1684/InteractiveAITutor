from fastapi import APIRouter
from fastapi import File, UploadFile
from canvas_analyzer import CanvasAnalyzer
from pathlib import Path
import uuid
from app.core.logger import get_logger
from app.services.session_manager import session_manager

logger = get_logger(__name__)

router = APIRouter()



@router.post("/analyze-canvas")
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

        logger.info("canvas upload received: filenames=%s", image.filename)

        #create a dir for canvas uploads

        canvas_dir = Path("canvas_uploads")
        canvas_dir.mkdir(exist_ok=True)

        #save uploaded file to canvas dir
        file_extention = Path(image.filename).suffix


        unique_filename = f"canvas_{uuid.uuid4()}{file_extention}"
        file_path = canvas_dir / (unique_filename)

        logger.info("canvas file saved to %s", file_path)


        #open file
        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        #analyze canvas with automatic detection
        analyzer = CanvasAnalyzer()


        analysis_result = analyzer.analyze_student_work(str(file_path))
        logger.info("canvas analysis started")
        logger.info("canvas analysis result: %s", analysis_result.get("status"))
        annotations_result = analyzer.annotate_student_work(str(file_path))
        logger.info("canvas annotation started")
        logger.info("canvas annotation result: %s, count=%s", annotations_result.get("status"), len(annotations_result.get("annotations", [])))

        #remove the uplaoded file
        file_path.unlink()
        logger.info("canvas file removed")

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
        logger.error("canvas analysis failed: %s", str(e))
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/canvas-sessions/{student_id}")
async def get_canvas_sessions(student_id: str):
    """
    Get recent canvas sessions for a student
    
    Args:
        student_id: The student's ID
    
    Returns:
        List of canvas sessions with metadata
    """
    try:
        logger.info(f"📋 Fetching canvas sessions for student: {student_id}")
        
        # Get from in-memory cache
        sessions = session_manager.recent_sessions.get(student_id, [])
        
        # Format for frontend
        formatted_sessions = []
        for session in sessions:
            formatted_sessions.append({
                "session_id": session.get("session_id"),
                "timestamp": session.get("timestamp").isoformat() if session.get("timestamp") else None,
                "latex_expressions": session.get("latex_expressions", []),
                "symbol_count": session.get("symbol_count", 0),
                "canvas_image_url": session.get("canvas_image_url"),
                "agent_feedback": session.get("agent_feedback", "")
            })
        
        logger.info(f"✅ Found {len(formatted_sessions)} canvas sessions")
        return {
            "status": "success",
            "sessions": formatted_sessions,
            "count": len(formatted_sessions)
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching canvas sessions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "sessions": []
        }