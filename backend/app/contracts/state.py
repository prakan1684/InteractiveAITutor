from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    agent_name: str
    action: str
    thought: Optional[str] = None
    observation: Optional[str] = None
    latency_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    tool_name: str
    status: Literal["success", "error", "timeout"]
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TraceState(BaseModel):
    run_id: str
    intent: Optional[str] = None
    execution_plan: List[str] = Field(default_factory=list)
    current_step: int = 0
    next_action: str = "start"
    steps: List[TraceStep] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    agents_completed: List[str] = Field(default_factory=list)
    workflow_complete: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_tokens_used: int = 0


class TutorStateContract(BaseModel):
    state_version: Literal["1.0"] = "1.0"
    session_id: str
    student_id: str

    user_message: Optional[str] = None
    full_canvas_path: Optional[str] = None
    canvas_dimensions: Dict[str, int] = Field(default_factory=dict)
    steps_metadata: List[Dict[str, Any]] = Field(default_factory=list)
    step_image_paths: Dict[str, str] = Field(default_factory=dict)
    strokes_data: List[Dict[str, Any]] = Field(default_factory=list)

    memory_output: Optional[Dict[str, Any]] = None
    vision_output: Optional[Dict[str, Any]] = None
    feedback_output: Optional[Dict[str, Any]] = None

    final_response: Optional[str] = None
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    flags: Dict[str, Any] = Field(default_factory=dict)

    trace: TraceState

