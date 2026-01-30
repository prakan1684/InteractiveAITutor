

from app.agents.schemas import State, PerceptionState, BBoxNorm
from app.services.clustering import cluster_strokes
from app.services.vision import VisionService
from prompts.canvas_prompts import SIMPLE_CANVAS_ANALYSIS_PROMPT, SPRITE_SHEET_OCR_PROMPT
import json
from app.core.logger import get_logger

logger = get_logger(__name__)

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
    """
    Generate feedback based on canvas analysis.
    Simple: if we have analysis, use it. Otherwise, generic message.
    """
    
    if state.canvas_analysis:
        analysis = state.canvas_analysis
        
        # Build response from analysis
        parts = []
        
        # What they're working on
        problem = analysis.get("problem_summary", "")
        if problem:
            parts.append(f"I can see you're working on: {problem}")
        
        # What they wrote
        expressions = analysis.get("expressions_found", [])
        if expressions:
            expr_str = ", ".join(f"${e}$" for e in expressions)
            parts.append(f"\nYou wrote: {expr_str}")
        
        # Correctness check
        is_correct = analysis.get("is_correct")
        if is_correct is True:
            parts.append(f"\n✓ That's correct! {analysis.get('expected_answer', '')}")
        elif is_correct is False:
            parts.append(f"\n✗ Not quite. The correct answer is {analysis.get('expected_answer', 'unknown')}.")
        elif analysis.get("expected_answer"):
            parts.append(f"\nThe answer to this problem is {analysis.get('expected_answer')}.")
        
        # Feedback
        feedback = analysis.get("feedback", {})
        if feedback.get("positive"):
            parts.append(f"\n\n👍 {feedback['positive']}")
        if feedback.get("improvement"):
            parts.append(f"\n💡 {feedback['improvement']}")
        if feedback.get("next_step"):
            parts.append(f"\n📚 {feedback['next_step']}")
        
        final_response = "\n".join(parts) if parts else "Great work on your canvas!"
    
    else:
        # Fallback
        num_symbols = state.flags.get("num_symbols", 0) if state.flags else 0
        if num_symbols > 0:
            final_response = "Canvas received! I can see your work. Ask me about it in chat for detailed feedback."
        else:
            final_response = "Canvas received! Start writing your work and I'll help you."
    
    return {"final_response": final_response}







# NOT BEING USED
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

    logger.info(f"🔍 OCR: Analyzing sprite sheet - {state.sprite_sheet_path}")
    result = vision.analyze_image(state.sprite_sheet_path, SPRITE_SHEET_OCR_PROMPT)
    logger.info(f"📊 OCR result: success={result.get('success')}, has_analysis={bool(result.get('analysis'))}")
    
    symbols = []
    raw = result.get("analysis") if result.get("success") else None    
    tiles = []
    if raw:
        logger.info(f"📝 OCR raw response length: {len(raw)} chars")
        try:
            data = json.loads(raw)
            tiles = data.get("tiles", []) if isinstance(data, dict) else []
            logger.info(f"✅ OCR parsed: {len(tiles)} tiles extracted")
        except Exception as e:
            logger.error(f"❌ OCR JSON parse failed: {e}")
            tiles = []
    else:
        logger.warning("⚠️ OCR returned no raw analysis data")
    
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
    
    logger.info(f"📐 Final symbols extracted: {len(symbols)} symbols, {sum(1 for s in symbols if s['latex'].strip())} with LaTeX")
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



def analyze_canvas(state: State) -> dict:
    from prompts.canvas_prompts import FULL_CANVAS_ANALYSIS_PROMPT


    flags = dict(state.flags)
    if not state.img_path:
        logger.warning("canvas analysis failed: missing img_path")
        return {"canvas_analysis": None, "flags": flags}
    
    num_regions= 0
    if state.perception and state.perception.symbol_boxes:
        num_regions = len(state.perception.symbol_boxes)

    
    context_hint = f"\n\nNote: Detected {num_regions} separate regions of handwriting." if num_regions > 0 else ""
    

    prompt = SIMPLE_CANVAS_ANALYSIS_PROMPT.format(context_hint=context_hint)
    
    logger.info(f"🎨 Analyzing full canvas with {num_regions} regions")
    vision = VisionService()
    result = vision.analyze_image(state.img_path, prompt)
    
    if not result.get("success"):
        logger.error(f"❌ Canvas analysis failed: {result.get('error')}")
        return {"canvas_analysis": None, "flags": flags}
    
    analysis_data = None
    # Parse the JSON response
    try:
        raw_analysis = result.get("analysis", "")
        logger.info(f"📝 Canvas analysis response length: {len(raw_analysis)} chars")
        analysis_data = json.loads(raw_analysis)    
        logger.info(f"✅ Canvas analysis parsed successfully")
        

        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse canvas analysis JSON: {e}")
        logger.error(f"Raw response: {raw_analysis[:200]}...")
        return {"canvas_analysis": None, "flags": flags}
    
    return {
        "canvas_analysis": analysis_data,
        "flags": flags
    }




    


    