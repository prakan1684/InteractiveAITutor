from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FeedbackGenerateInput(BaseModel):
    user_message: str
    vision_output: Dict[str, Any] = Field(default_factory=dict)
    memory_output: Dict[str, Any] = Field(default_factory=dict)


class FeedbackGenerateData(BaseModel):
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    feedback: str
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)

