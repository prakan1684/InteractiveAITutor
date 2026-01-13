

from app.agents.schemas import State, PerceptionState, BBoxNorm
from app.services.clustering import cluster_strokes

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



    