"""
This router is for obtaining bounding box regions of handwriting sent
from the ios canvas app

"""

from fastapi import APIRouter, File, UploadFile, Form
from logger import get_logger
from typing import List, Dict
import json
from PIL import Image, ImageDraw
import io
import uuid
from datetime import datetime

from app.agents.graph import build_graph
from app.agents.schemas import State
from app.mcp_servers.perception.schemas import Box, Stroke
from app.services.clustering import cluster_strokes
from app.services.canvas_context import CanvasContext
from app.services.sprite_sheet import build_sprite_sheet_from_ctx

GRAPH = build_graph()

logger = get_logger(__name__)

router = APIRouter()


@router.post("/regions")
async def regions(
    image: UploadFile = File(...),
    regions: str = Form(...),
    image_width: int = Form(...),
    image_height: int = Form(...),
    strokes: str = Form(...)
 ):
    geometry = json.loads(regions)
    strokes = json.loads(strokes)
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes))
    stroke_list = []
    if isinstance(strokes, dict):
        stroke_list = strokes.get("strokes", [])
    elif isinstance(strokes, list):
        stroke_list = strokes

    if not isinstance(stroke_list, list):
        stroke_list = []

    stroke_models: List[Stroke] = []
    for s in stroke_list:
        if not isinstance(s, dict):
            continue
        try:
            stroke_models.append(Stroke(**s))
        except Exception:
            continue

    clusters, symbol_boxes, stroke_boxes = cluster_strokes(stroke_list)

    """
    From this point we have clusters, symbol_boxes, and stroke_boxes

    clusters: List[List[int]]
        - List of indices of strokes that belong to each symbol
    symbol_boxes: List[Box]
        - Merged bounding boxes of strokes in each cluster
    stroke_boxes: List[Box]
        - Bounding boxes of each stroke
    """

    ctx = CanvasContext(
        image_width=image_width,
        image_height=image_height,
        symbol_boxes=symbol_boxes,
        image_bytes=image_bytes,
    )

    #create drawing context
    draw = ImageDraw.Draw(img)



    colors = ["red", "green", "blue", "yellow", "orange", "purple", "pink", "brown", "gray", "black"]
    for i, b in enumerate(stroke_boxes):
        bbox_px = normalized_to_pixel(
            {"x": b.x, "y": b.y, "width": b.w, "height": b.h},
            image_width,
            image_height,
        )
        color = colors[i % len(colors)]
        #draw.rectangle(bbox_px, outline=color, width=2)
        #draw.text((bbox_px[0], bbox_px[1] - 15), f"Stroke {i}", fill=color)

    for i, b in enumerate(symbol_boxes):
        bbox_px = normalized_to_pixel(
            {"x": b.x, "y": b.y, "width": b.w, "height": b.h},
            image_width,
            image_height,
        )
        draw.rectangle(bbox_px, outline="cyan", width=4)
        draw.text((bbox_px[0], bbox_px[1] - 15), f"Symbol {i}", fill="cyan")
    
    sprite_sheet = build_sprite_sheet_from_ctx(ctx)
    sprite_sheet_path = f"/tmp/sprite_sheet_{uuid.uuid4().hex[:8]}.png"
    sprite_sheet.save(sprite_sheet_path)
    logger.info(f"Saved sprite sheet to {sprite_sheet_path}")

    debug_path = f"/tmp/debug_{uuid.uuid4().hex[:8]}.png"
    img.save(debug_path)

    logger.info(f"Saved debug image to {debug_path}")

    try:
        state = State(
            session_id="test_session",
            student_id="test_student",
            img_path=debug_path,
            strokes=stroke_models,
            created_at=datetime.now(),
            sprite_sheet_path=sprite_sheet_path,
        )
        out_state = GRAPH.invoke(state)
    except Exception as e:
        return {
            "status": "error",
            "problem_type": None,
            "context": None,
            "feedback": None,
            "annotations": None,
            "annotation_status": "error",
            "annotation_error": str(e),
            "annotation_metadata": None,
            "error": str(e),
        }

    final_response = out_state.get("final_response")

    return {
        "status": "ok",
        "problem_type": None,
        "context": None,
        "feedback": {
            "problem": "",
            "analysis": final_response or "",
            "hints": [],
            "mistakes": [],
            "next_step": "",
            "encouragement": "",
        },
        "annotations": [],
        "annotation_status": "skipped",
        "annotation_error": None,
        "annotation_metadata": None,
        "error": None,
        "debug": {
            "received_regions": geometry,
            "image_width": image_width,
            "image_height": image_height,
            "clusters": clusters,
            "symbol_boxes": [{"x": b.x, "y": b.y, "width": b.w, "height": b.h} for b in symbol_boxes],
            "stroke_boxes": [{"x": b.x, "y": b.y, "width": b.w, "height": b.h} for b in stroke_boxes],
            "debug_image_path": debug_path,
            "sprite_sheet_path": sprite_sheet_path,
            "agent_flags": out_state.get("flags", {}),
        },
    }

def normalized_to_pixel(
    bbox_norm: Dict[str, float],
    img_width: int,
    img_height: int
) -> List[int]:
    x_px =  int(bbox_norm['x'] * img_width)
    y_px = int(bbox_norm['y'] * img_height)
    w_px = int(bbox_norm['width'] * img_width)
    h_px = int(bbox_norm['height'] * img_height)
    return [x_px, y_px, x_px + w_px, y_px + h_px]




    
    
    

    

