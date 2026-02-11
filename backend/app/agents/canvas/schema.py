from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class CanvasState:
    canvas_path: str
    session_id: Optional[str] = None
    student_query: Optional[str] = None

    analysis: Optional[str] = None
    feedback: Optional[str] = None


    class Config:
        arbitrary_types_allowed = True
