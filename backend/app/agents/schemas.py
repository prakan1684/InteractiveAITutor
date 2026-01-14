from typing import List, Tuple, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.mcp_servers.perception.schemas import Stroke


class RagChunk(BaseModel):
    source: str
    text: str
    score: float = Field(default=1.0, ge=0.0)


class BBoxNorm(BaseModel):
    x: float
    y: float
    w: float
    h: float


class PerceptionState(BaseModel):
    clusters: List[List[int]] = Field(default_factory=list)
    symbol_boxes: List[BBoxNorm] = Field(default_factory=list)
    stroke_boxes: List[BBoxNorm] = Field(default_factory=list)
    num_symbols: int = 0


class State(BaseModel):
    session_id: str
    student_id: str
    img_path: str
    strokes: List[Stroke]
    created_at: datetime = Field(default_factory=datetime.now)
    sprite_sheet_path: Optional[str] = None

    rag_context: List[RagChunk] = Field(default_factory=list)
    flags: Dict[str, Any] = Field(default_factory=dict)

    perception: Optional[PerceptionState] = None
    understanding: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    final_response: Optional[str] = None


class ChatState(BaseModel):
    #input 
    user_message: str
    student_id: Optional[str] = None
    conversation_history: List[Dict] = Field(default_factory=list)

    # Intent classification
    intent: Optional[str] = None  # "canvas_review", "concept_question", "problem_solving", "general"
    needs_canvas_context: bool = False
    needs_course_context: bool = False
    needs_tools: bool = False
    
    # Retrieved context
    canvas_context: List[Dict] = Field(default_factory=list)  # Recent + historical canvas work
    course_context: List[Dict] = Field(default_factory=list)  # RAG results from docs
    
    # Reasoning
    reasoning_steps: List[str] = Field(default_factory=list)  # Track agent's thinking
    confidence: Optional[float] = None  # How confident is the agent?
    
    # Tool use
    tools_used: List[Dict] = Field(default_factory=list)  # Track tool invocations
    tool_results: Dict = Field(default_factory=dict)
    
    # Output
    final_response: Optional[str] = None
    follow_up_suggestions: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    total_tokens: int = 0


