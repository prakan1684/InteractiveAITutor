from typing import Dict, List
from app.core.logger import get_logger
from app.services.session_manager import SessionManager

logger = get_logger(__name__)


def store_session(
    session_id: str,
    student_id: str,
    final_response: str,
    canvas_analysis: Dict,
    flags: Dict,
    canvas_image_url: str
) -> bool:
    """
    Store a canvas session in memory for later retrieval.
    """
    logger.info(f"🔧 Tool: store_session")
    logger.info(f"   Session: {session_id}, Student: {student_id}")
    
    session_manager = SessionManager()
    success = session_manager.store_canvas_session(
        session_id=session_id,
        student_id=student_id,
        final_response=final_response,
        canvas_analysis=canvas_analysis,
        flags=flags,
        canvas_image_url=canvas_image_url
    )
    
    logger.info(f"   Stored: {success}")
    return success


def get_recent_work(student_id: str) -> Dict:
    """
    Retrieve recent canvas work for a student.
    """
    logger.info(f"🔧 Tool: get_recent_work")
    logger.info(f"   Student: {student_id}")
    
    session_manager = SessionManager()
    recent_work = session_manager.get_recent_context(student_id)
    
    if recent_work:
        logger.info(f"   Retrieved: {len(recent_work)} sessions")
    else:
        logger.info(f"   Retrieved: 0 sessions")
    
    return recent_work or {}

def search_canvas_history(student_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """
    Search canvas history for relevant past work.
    """
    logger.info(f"🔧 Tool: search_canvas_history")
    logger.info(f"   Student: {student_id}, Query: {query}")
    
    session_manager = SessionManager()
    results = session_manager.search_canvas_history(student_id, query, top_k)
    
    logger.info(f"   Found: {len(results)} results")
    return results




 

