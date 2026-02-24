from typing import Optional, List


from app_v2.contracts.check_api import CheckRequest
from app_v2.contracts.snapshot import BBox, ClientMeta, Snapshot, StepSnapshot
from app_v2.contracts.ios_payload import IOSAnalyzePayload, IOSProvisionalStep

def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))



def _normalize_bbox(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    canvas_width: float,
    canvas_height: float
) -> BBox:
    """
    Convert MyScript editor coordinates to normalized [0, 1] bbox.

    Notes:
    - iOS payload may contain negative y in MyScript coordinate space.
    - Internal app_v2 snapshot contract expects normalized values in [0,1].
    - We clamp to [0,1] for V1 robustness.
    """
    

    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError("canvas_width and canvas_height must be positive")
    
    # Convert to normalized coordinates
    norm_x = x / canvas_width
    norm_y = y / canvas_height
    norm_width = width / canvas_width
    norm_height = height / canvas_height
    
    # Clamp to [0, 1]
    norm_x = _clamp_01(norm_x)
    norm_y = _clamp_01(norm_y)
    norm_width = _clamp_01(norm_width)
    norm_height = _clamp_01(norm_height)
    
    return BBox(x=norm_x, y=norm_y, width=norm_width, height=norm_height)


def _map_step(
    step: IOSProvisionalStep,
    payload: IOSAnalyzePayload
) -> Optional[StepSnapshot]:
    """
    Map an IOSProvisionalStep to a StepSnapshot.
    """
    text = step.text.strip()
    if not text:
        return None

    if step.bbox is None:
        return None
    cm = payload.clientMeta
    

    bbox = _normalize_bbox(
        x=step.bbox.x,
        y=step.bbox.y,
        width=step.bbox.width,
        height=step.bbox.height,
        canvas_width=cm.canvasWidth,
        canvas_height=cm.canvasHeight,
    )


    # Store iOS-specific extras in structured_repr for now to avoid schema churn.
    structured_repr = {
        "source": "ios_provisional_step",
        "element_type": step.elementType,
        "word_locations_present": step.wordLocations is not None,
    }

    return StepSnapshot(
        step_id=step.stepId,
        raw_myscript=text,
        bbox=bbox,
        stroke_ids=step.strokeIds or [],
        line_index=step.lineIndex,
        structured_repr=structured_repr,
    )


def _map_client_meta(payload: IOSAnalyzePayload) -> ClientMeta:
    cm = payload.clientMeta
    return ClientMeta(
        device=cm.device,
        app_version=cm.appVersion,
        canvas_width=cm.canvasWidth,
        canvas_height=cm.canvasHeight,
        zoom_scale=cm.viewScale,
        content_offset_x=cm.viewOffsetX,
        content_offset_y=cm.viewOffsetY,
    )

def ios_payload_to_check_request(
    payload: IOSAnalyzePayload,
    *,
    last_snapshot_id: Optional[str] = None,
    include_correction: bool = False,
    include_debug_trace: bool = False,
) -> CheckRequest:
    """
    Adapter Boundary: ios analyze payload -> check request

    this mf should be the only place that knows ios transport shape

    """
    provisional_steps = payload.recognition.provisionalSteps or []

    mapped_steps: List[StepSnapshot] = []
    for step in provisional_steps:
        mapped = _map_step(step, payload)
        if mapped is not None:
            mapped_steps.append(mapped)
    
    if not mapped_steps:
        raise ValueError("No valid steps found in provisionalSteps")

    snapshot = Snapshot(
        # snapshot_id is assigned by backend store later
        session_id=payload.sessionId,
        user_id=None,
        steps=mapped_steps,
        client_meta=_map_client_meta(payload),
        # TODO: Preserve rawJiix/transcriptionText in a debug artifact store or trace
    )

    return CheckRequest(
        session_id=payload.sessionId,
        snapshot=snapshot,
        last_snapshot_id=last_snapshot_id,
        client_meta=_map_client_meta(payload),
        include_correction=include_correction,
        include_debug_trace=include_debug_trace,
    )

    