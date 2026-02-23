from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MemoryGetRecentInput(BaseModel):
    student_id: str
    limit: int = 5


class MemoryGetRecentData(BaseModel):
    sessions: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    source: str = "cache_or_index"


class MemoryStoreSessionInput(BaseModel):
    session_id: str
    student_id: str
    summary: str
    misconceptions: List[str] = Field(default_factory=list)
    canvas_analysis: Dict[str, Any] = Field(default_factory=dict)
    final_response: str


class MemoryStoreSessionData(BaseModel):
    stored: bool

