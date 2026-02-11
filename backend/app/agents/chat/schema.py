from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class ChatState:
    student_id: str
    message: str
    conversation_history: List[Dict] = field(default_factory=list)

    intent: Optional[str] = None
    needs_canvas: bool = False

    recent_canvas_analysis: Optional[str] = None

    response: Optional[str] = None
    action: Optional[str] = None