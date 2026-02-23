from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PerceptionOptions(BaseModel):
    infer_steps: bool = True
    max_regions: int = 50


class PerceptionAnalyzeCanvasInput(BaseModel):
    image_path: str
    steps_metadata: List[Dict[str, Any]] = Field(default_factory=list)
    step_image_paths: Dict[str, str] = Field(default_factory=dict)
    options: PerceptionOptions = Field(default_factory=PerceptionOptions)


class PerceptionAnalyzeCanvasData(BaseModel):
    problem_type: Optional[str] = None
    subject: Optional[str] = None
    overall_correctness: Optional[str] = None
    summary: Optional[str] = None
    steps_overview: List[Dict[str, Any]] = Field(default_factory=list)
    steps_needing_analysis: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)

