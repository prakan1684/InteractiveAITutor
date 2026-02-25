from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app_v2.domain.enums import ChangeType, CheckStatus

class ChangedStepRef(BaseModel):
    # Keep this simple and flexible for V1
    step_id: Optional[str] = None
    line_index: Optional[int] = Field(default=None, ge=0)
    reason: Optional[str] = None

class DiffResult(BaseModel):
    session_id: str
    snapshot_id_before: str
    snapshot_id_after: str

    change_type: ChangeType
    confidence: float = Field(..., ge=0.0, le=1.0)

    step_count_before: int = Field(..., ge=0)
    step_count_after: int = Field(..., ge=0)
    step_count_delta: int

    matched_steps: int = Field(..., ge=0)
    changed_steps: List[ChangedStepRef] = Field(default_factory=list)

    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiffContextEntry(BaseModel):
    # Context bank can store DiffResult directly, but this wrapper gives room to grow
    diff: DiffResult
    note: Optional[str] = None


class FeedbackResult(BaseModel):
    # Output of your feedback generator for the orchestrator to use
    status: CheckStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    hint: str = Field(..., min_length=1)
    summary: Optional[str] = None