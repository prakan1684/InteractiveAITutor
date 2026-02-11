"""
Canvas storage — stores the latest canvas image path per student.
Analysis is done on-demand when the chat agent needs it.
"""

from typing import Dict, Optional
from datetime import datetime
from app.core.logger import get_logger

logger = get_logger(__name__)

class CanvasStorage:
    """In-memory storage for canvas image paths and cached analyses"""
    
    def __init__(self):
        # {student_id: {image_path, timestamp}}
        self._images: Dict[str, Dict] = {}
        # {student_id: {analysis, timestamp}} — cached after on-demand vision call
        self._analysis_cache: Dict[str, Dict] = {}
        # {conversation_id: image_path} — last canvas image shown in each conversation
        self._last_shown: Dict[str, str] = {}
    
    def store_image(self, student_id: str, image_path: str) -> None:
        """Store latest canvas image path (called by /steps on every iPad update)"""
        self._images[student_id] = {
            "image_path": image_path,
            "timestamp": datetime.now()
        }
        # Invalidate cached analysis since canvas changed
        self._analysis_cache.pop(student_id, None)
        logger.info(f"Canvas image updated for student {student_id}: {image_path}")
    
    def get_image_path(self, student_id: str) -> Optional[str]:
        """Get the latest canvas image path for a student"""
        data = self._images.get(student_id)
        return data["image_path"] if data else None
    
    def store_analysis(self, student_id: str, analysis: str) -> None:
        """Cache analysis result after on-demand vision call"""
        self._analysis_cache[student_id] = {
            "analysis": analysis,
            "timestamp": datetime.now()
        }
        logger.info(f"Analysis cached for student {student_id}")
    
    def get_analysis(self, student_id: str) -> Optional[str]:
        """Get cached analysis if it exists and image hasn't changed since"""
        cache = self._analysis_cache.get(student_id)
        if not cache:
            return None
        
        # Check if image was updated after analysis was cached
        image_data = self._images.get(student_id)
        if image_data and image_data["timestamp"] > cache["timestamp"]:
            # Image is newer than cached analysis — stale
            return None
        
        return cache["analysis"]
    
    def has_canvas(self, student_id: str) -> bool:
        """Check if student has any canvas image stored"""
        return student_id in self._images
    
    def is_image_new_for_conversation(self, student_id: str, conversation_id: str) -> bool:
        """Check if the current canvas image is different from what was last shown in this conversation."""
        current_path = self.get_image_path(student_id)
        if not current_path:
            return False
        last_shown = self._last_shown.get(conversation_id)
        if not last_shown:
            return True  # never shown in this conversation
        # Check if image was updated since it was last shown
        image_data = self._images.get(student_id)
        return image_data and image_data["timestamp"] > last_shown["timestamp"]
    
    def mark_image_shown(self, student_id: str, conversation_id: str) -> None:
        """Record that the current canvas image was shown in this conversation."""
        self._last_shown[conversation_id] = {
            "image_path": self.get_image_path(student_id),
            "timestamp": datetime.now()
        }


# Global instance
canvas_storage = CanvasStorage()
