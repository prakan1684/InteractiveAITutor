

from app.agents.schemas import State, PerceptionState, BBoxNorm
from app.services.clustering import cluster_strokes
from app.services.vision import VisionService
from prompts.canvas_prompts import SPRITE_SHEET_OCR_PROMPT
import json

def ingest(state:State) -> dict:

    flags = dict(state.flags)
    flags["needs_annotation"] = False
    flags["has_strokes"] = len(state.strokes) > 0
    return {"flags": flags}


def perceive(state: State) -> dict:
    flags = dict(state.flags)
    stroke_dicts= [s.model_dump() for s in state.strokes]
    clusters, symbol_boxes, stroke_boxes = cluster_strokes(stroke_dicts)
    symbol_bbox_norm = [BBoxNorm(x=s.x, y=s.y, w=s.w, h=s.h) for s in symbol_boxes]
    stroke_bbox_norm = [BBoxNorm(x=s.x, y=s.y, w=s.w, h=s.h) for s in stroke_boxes]
    perception = PerceptionState(
        clusters=clusters,
        symbol_boxes = symbol_bbox_norm,
        stroke_boxes = stroke_bbox_norm,
        num_symbols = len(symbol_boxes)
    )

    flags["num_symbols"] = perception.num_symbols
    flags['needs_annotation'] = perception.num_symbols>0

    return {"perception": perception, "flags": flags}


def respond(state: State) -> dict:
    num_symbols = 0
    needs_annotation = False

    if state.flags:
        num_symbols = int(state.flags.get("num_symbols", 0))
        needs_annotation = bool(state.flags.get("needs_annotation", False))

    msg = f"I detected {num_symbols} symbol groups. needs_annotation={needs_annotation}."
    return {"final_response": msg}



def understand(state: State) -> dict:
    # get the sprite sheet from state, must exist to use OCR, also symbol boxes must exist
    flags = dict(state.flags)
    if not state.perception or not state.perception.symbol_boxes:
        flags['needs_annotation'] = False
        return {
            "understanding":{"symbols":[]},
            "flags": flags
        }
    if not getattr(state, "sprite_sheet_path", None):
        flags['needs_annotation'] = True
        return {
            "understanding":{"symbols":[]},
            "flags": flags
        }
    vision = VisionService()

    result = vision.analyze_image(state.sprite_sheet_path, SPRITE_SHEET_OCR_PROMPT)
    symbols = []
    raw = result.get("analysis") if result.get("success") else None    
    if raw:
        try:
            data = json.loads(raw)
            tiles = data.get("tiles", []) if isinstance(data, dict) else []
        except Exception as e:
            tiles = []
    
    #attach OCR results to symbol boxes by ID
    for i, bbox in enumerate(state.perception.symbol_boxes):
        match = None
        for t in tiles:
            if isinstance(t, dict) and t.get("id") == i:
                match = t
                break
        latex = " "
        conf = 0.0
        if match: 
            latex = str(match.get("latex", ""))
            try:
                conf = float(match.get("confidence", 0.0))
            except ValueError:
                conf = 0.0
        symbols.append({
            "id": i,
            "latex": latex,
            "confidence": conf,
            "bbox": {"x": bbox.x, "y": bbox.y, "w": bbox.w, "h": bbox.h}

        })
    understanding = {
        "symbols": symbols,
        "raw_ocr": {"success": result.get("success"), "raw": raw}
    }
    flags['needs_annotation'] = len(symbols) > 0
    return {"understanding": understanding, "flags": flags}


def annotate(state: State) -> dict:
    flags = dict(state.flags)
    if not state.perception or not state.perception.symbol_boxes:
        return {"annotations": [], "flags": flags}
    needs_annotation = bool(flags.get("needs_annotation", False))
    if not needs_annotation:
        return {"annotations": [], "flags": flags}
    anns = []
    for i, b in enumerate(state.perception.symbol_boxes):
        anns.append({
            "type":"highlight",
            "topLeft": {"x": b.x, "y": b.y},
            "width": b.w,
            "height": b.h,
            "colorHex": "#FFFF00",
            "opacity": 0.25
        })
    return {
        "annotations": anns,
        "flags": flags
    }

    