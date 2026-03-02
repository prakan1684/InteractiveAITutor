from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app_v2.contracts.snapshot import BBox, ClientMeta, Snapshot
from app_v2.domain.enums import CheckStatus, HighlightType
from app_v2.contracts.agent_goal import AgentGoal



class CorrectionPayload(BaseModel):
    corrected_latex: Optional[str]=None
    corrected_text: Optional[str] = None
    explanation: Optional[str] = None



class Highlight(BaseModel):
    bbox: BBox
    type: HighlightType
    label: Optional[str] = None


class CheckRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    snapshot: Snapshot
    last_snapshot_id: Optional[str] = None

    # duplicated for convenience at api layer
    client_meta: Optional[ClientMeta] = None


    include_correction: bool = False

    include_debug_trace: bool = False

class DebugTraceSummary(BaseModel):
    # Small, safe summary for local debugging
    change_type: Optional[str] = None
    tools_called: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class CheckResponse(BaseModel):
    status: CheckStatus
    confidence: float = Field(..., ge=0.0, le=1.0)

    highlights: List[Highlight] = Field(default_factory=list)
    hint: Optional[str] = None

    # Agent goal for UI guidance
    agent_goal: Optional[AgentGoal] = None

    # Null unless requested / available
    correction: Optional[CorrectionPayload] = None

    new_snapshot_id: str
    trace_id: str

    # Optional dev/debug data
    debug_trace_summary: Optional[DebugTraceSummary] = None



class CorrectionRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)


class CorrectionResponse(BaseModel):
    correction: Optional[CorrectionPayload] = None
    trace_id: str
