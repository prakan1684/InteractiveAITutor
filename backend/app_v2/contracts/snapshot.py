from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field



class BBox(BaseModel):
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)



class CanvasImageRef(BaseModel):
    # Keep this simple in V1
    mime_type: Optional[str] = None
    path: Optional[str] = None
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)


class StepSnapshot(BaseModel):
    step_id: Optional[str] = None

    #source of truth for checking
    raw_myscript: str = Field(..., min_length=1)


    #optional derived fields
    normalized_latex: Optional[str] = None
    structured_repr: Optional[Dict[str, Any]] = None
    parse_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    #ui localization
    bbox: BBox


    #optional linkage back to strokes 
    stroke_ids: List[str] = Field(default_factory=list)
    line_index: Optional[int] = Field(default=None, ge=0)



class ClientMeta(BaseModel):
    device: Optional[str] = None
    app_version: Optional[str] = None
    canvas_width: Optional[int] = Field(default=None, gt=0)
    canvas_height: Optional[int] = Field(default=None, gt=0)
    zoom_scale: Optional[float] = Field(default=None, gt=0)
    content_offset_x: Optional[float] = None
    content_offset_y: Optional[float] = None



class Snapshot(BaseModel):
    # Server may assign this after storing; allow missing on request
    snapshot_id: Optional[str] = None

    session_id: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None

    # Required in V1: this is what enables diff + latest-step checks
    steps: List[StepSnapshot] = Field(..., min_length=1)

    # Optional image fallback for replay/debug
    canvas_image: Optional[CanvasImageRef] = None

    # Raw client metadata travels with the snapshot
    client_meta: Optional[ClientMeta] = None
