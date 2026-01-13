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
