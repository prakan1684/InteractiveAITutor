from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app_v2.domain.enums import CheckStatus, ChangeType, ToolCallStatus, TraceEventType, Verdict


class TraceEvent(BaseModel):
    event_type: TraceEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str

    #summary payload 
    details: Dict[str, Any] = Field(default_factory=dict)



class ToolCallTrace(BaseModel):
    tool_name: str
    status: ToolCallStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    latency_ms: Optional[int] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Tool-specific summary fields (not full raw output)
    verdict: Optional[Verdict] = None
    reason_code: Optional[str] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: Optional[bool] = None

    summary: Optional[str] = None


class CheckTrace(BaseModel):
    trace_id: str
    session_id: str
    snapshot_id_before: Optional[str] = None
    snapshot_id_after: Optional[str] = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_latency_ms: Optional[int] = Field(default=None, ge=0)

    # Orchestrator decisions
    change_type: Optional[ChangeType] = None
    final_status: Optional[CheckStatus] = None
    final_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    tool_calls: List[ToolCallTrace] = Field(default_factory=list)
    events: List[TraceEvent] = Field(default_factory=list)

    
    