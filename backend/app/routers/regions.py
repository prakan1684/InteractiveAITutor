"""
This router is for obtaining bounding box regions of handwriting sent
from the ios canvas app

"""

from fastapi import APIRouter, File, UploadFile, Form
from app.services.azure_blob_storage import azure_blob_storage
from fastapi.encoders import jsonable_encoder
from app.core.logger import get_logger
from typing import List, Dict
import json
from PIL import Image, ImageDraw
import io
import uuid
from app.services.session_manager import session_manager
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
    strokes: str = Form(...),
    session_id: str = Form(...),
    student_id: str = Form(...),
 ):
    logger.info(f"📝 Canvas submission started - session_id={session_id}, student_id={student_id}")
    
    geometry = json.loads(regions)
    strokes = json.loads(strokes)

    canvas_filename= f"canvas_{session_id}.png"

    image_bytes = await image.read()
    logger.info(f"📷 Image received: {len(image_bytes)} bytes")

    canvas_url = azure_blob_storage.upload_canvas_image(
        image_data=image_bytes,
        filename=canvas_filename,
        metadata={
            "session_id": session_id, 
            "student_id": student_id, 
            "timestamp": datetime.now().isoformat()
        }
    )
    logger.info(f"☁️ Canvas uploaded to Azure: {canvas_filename}")



    
    img = Image.open(io.BytesIO(image_bytes))
    image_width, image_height = img.size

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
    
    logger.info(f"✏️ Processed {len(stroke_models)} strokes")

    clusters, symbol_boxes, stroke_boxes = cluster_strokes(stroke_list)
    logger.info(f"🔍 Detected {len(symbol_boxes)} symbols from {len(clusters)} clusters")

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
    
    sprite_buffer = io.BytesIO()
    sprite_sheet.save(sprite_buffer, format="PNG")
    sprite_filename = f"sprite_sheet_{session_id}.png"
    sprite_url = azure_blob_storage.upload_debug_image(
        image_data=sprite_buffer.getvalue(),
        filename=sprite_filename,
        session_id=session_id
    )

    logger.info(f"🖼️ Sprite sheet uploaded: {sprite_filename}")

    #upload debug to azure
    debug_buffer = io.BytesIO()
    img.save(debug_buffer, format='PNG')
    debug_filename = f"debug_{session_id}.png"
    
    debug_url = azure_blob_storage.upload_debug_image(
        image_data=debug_buffer.getvalue(),
        filename=debug_filename,
        session_id=session_id
    )
    logger.info(f"🐛 Debug image uploaded: {debug_filename}")
    
    try:
        state = State(
            session_id=session_id,
            student_id=student_id,
            img_path=canvas_url,
            strokes=stroke_models,
            created_at=datetime.now(),
            sprite_sheet_path=sprite_url,
        )
        logger.info("🤖 Starting AI analysis graph...")
        out_state = GRAPH.invoke(state)
        final_response = out_state.get("final_response")
        logger.info(f"✅ AI analysis complete - response length: {len(final_response) if final_response else 0} chars")

        try:
            symbols = out_state.get("symbols", [])
            flags = out_state.get("flags", {})
            
            logger.info(f"💾 Storing canvas session: {len(symbols)} symbols detected")
            session_manager.store_canvas_session(
                session_id=session_id,
                student_id=student_id,
                final_response=final_response,
                symbols=symbols,
                flags=flags
            )
            logger.info(f"✅ Canvas session stored successfully")
        except Exception as e:
            logger.error(f"❌ Error storing canvas session: {e}")



        annotations = out_state.get("annotations")
        if not isinstance(annotations, list):
            annotations = []
        annotation_status = "ok" if len(annotations) > 0 else "skipped"
        logger.info(f"📌 Annotations: {len(annotations)} generated, status={annotation_status}")
    except Exception as e:
        logger.error(f"❌ Canvas analysis failed: {str(e)}")
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

    
    payload = {
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
        "annotations": annotations,
        "annotation_status": annotation_status,
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
            "debug_image_path": debug_url,
            "canvas_image_path": canvas_url,
            "sprite_sheet_path": sprite_url,
            "agent_flags": dict(out_state.get("flags", {})),
        },
    }
    logger.info(f"🎉 Canvas submission complete - returning response")
    try:
        jsonable_encoder(payload)
    except Exception as e:
        logger.error(f"❌ Response serialization failed: {e}")
        raise
    return payload

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




    
    
    

    

