from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionMode(str, Enum):
    NORMAL = "NORMAL"
    CORRECTION_ACTIVE = "CORRECTION_ACTIVE"


class SessionAgentState(BaseModel):
    session_id: str = Field(..., min_length=1)
    mode: SessionMode = SessionMode.NORMAL
    active_reason_code: Optional[str] = None
    active_step_id: Optional[str] = None
    active_line_index: Optional[int] = Field(default=None, ge=0)
    original_error_snapshot_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    
