"""
Perception MCP Server - Schemas

Pydantic models for the Perception MCP server.
These schemas are used by both MCP tools and the orchestrator.
"""

from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field
from dataclasses import dataclass


class Region(BaseModel):
    """
    Represents a rectangular block on the canvas.
    """
    id: str
    type: Literal["math_expression", "text", "diagram", "unknown"] = "unknown"
    bbox_norm: Tuple[float, float, float, float]  # [x1, y1, x2, y2] in 0–1 coords
    bbox_px: Optional[Tuple[int, int, int, int]] = None  # same order, in pixels
    confidence: float = 1.0


class Expression(BaseModel):
    """
    Represents recognized text or math inside a region.
    """
    id: str
    region_id: str
    modality: Literal["math", "text"] = "math"
    raw_text: str
    latex: Optional[str] = None
    confidence: float = 1.0


class Step(BaseModel):
    """
    Represents a logical step the student took.
    """
    index: int
    expression_id: str
    role: Literal["problem_statement", "student_step", "scratch", "unknown"] = "student_step"
    bbox_norm: Tuple[float, float, float, float]


class AnalyzeCanvasOptions(BaseModel):
    """
    Options for the high-level analyze_canvas_image tool.
    """
    infer_steps: bool = True
    max_regions: int = 50


class AnalyzeCanvasInput(BaseModel):
    """
    Input payload for analyze_canvas_image.
    """
    image_url: str
    options: AnalyzeCanvasOptions = Field(default_factory=AnalyzeCanvasOptions)


class AnalyzeCanvasOutput(BaseModel):
    """
    Output payload for analyze_canvas_image.
    """
    image_size_px: Tuple[int, int]  # (width, height)
    regions: List[Region]
    expressions: List[Expression]
    steps: List[Step]
    problem_type_guess: Optional[str] = None
    global_confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class StrokePoint(BaseModel):
    x: float
    y: float
    t: float
    pressure: Optional[float] = None

class Stroke(BaseModel):
    id: str
    tool: Optional[str] = None
    colorHex: Optional[str] = None
    width: Optional[float] = None
    opacity: Optional[float] = None
    startedAt: Optional[float] = None
    endedAt: Optional[float] = None
    points: List[StrokePoint]

@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property    
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def width(self) -> float:
        return self.w

    @property
    def height(self) -> float:
        return self.h
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)





