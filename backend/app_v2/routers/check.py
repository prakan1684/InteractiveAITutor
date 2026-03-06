from uuid import uuid4
import base64
from pathlib import Path
import re
from typing import Optional


from app_v2.orchestrator.check_orchestrator import CheckOrchestrator
from fastapi import APIRouter, HTTPException

from app.core.logger import get_logger




from app_v2.contracts.check_api import CheckRequest, CheckResponse
from app_v2.contracts.ios_payload import IOSAnalyzePayload
from app_v2.contracts.ios_to_check import ios_payload_to_check_request
from app_v2.domain.enums import CheckStatus
from app_v2.stores.snapshot_store import SnapshotStore
from app_v2.stores.trace_store import TraceStore
from app_v2.stores.session_state_store import SessionStateStore



logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["check"])
MAX_CANVAS_IMAGE_BASE64_CHARS = 8_000_000
MAX_CANVAS_IMAGE_BYTES = 6_000_000
snapshot_store = SnapshotStore()
trace_store = TraceStore()
session_state_store = SessionStateStore()
orchestrator = CheckOrchestrator(snapshot_store, trace_store, session_state_store)



def _stub_check_response(new_snapshot_id: Optional[str] = None) -> CheckResponse:
    return CheckResponse(
        status=CheckStatus.NEED_MORE_CONTEXT,
        confidence=1.0,
        highlights=[],
        hint="Baseline saved. Add one more step, then press Check again.",
        correction=None,
        new_snapshot_id=new_snapshot_id or f"snap_{uuid4().hex}",
        trace_id=f"trace_{uuid4().hex}",
        debug_trace_summary=None,
    )

def _log_ios_payload_summary(payload: IOSAnalyzePayload) -> None:
    recognition = payload.recognition
    client_meta = payload.clientMeta
    steps = recognition.provisionalSteps or []
    canvas_image = payload.canvasImage

    logger.info(
        "iOS /check payload received: requestId=%s sessionId=%s timestampMs=%s partType=%s "
        "provisionalSteps=%d rawJiix_present=%s rawJiix_len=%d transcription_present=%s "
        "canvas=(%.1f x %.1f) coord_space=%s canvasImage_present=%s canvasImage_dims=%s x %s",
        payload.requestId,
        payload.sessionId,
        payload.timestampMs,
        payload.document.partType,
        len(steps),
        recognition.rawJiix is not None,
        len(recognition.rawJiix) if recognition.rawJiix else 0,
        recognition.transcriptionText is not None,
        client_meta.canvasWidth,
        client_meta.canvasHeight,
        client_meta.coordinateSpace,
        canvas_image is not None,
        canvas_image.width if canvas_image else None,
        canvas_image.height if canvas_image else None,
    )

    # Log the first few steps for debugging shape/mapping (avoid huge logs)
    for idx, step in enumerate(steps[:5]):
        logger.info(
            "step[%d]: stepId=%s elementType=%s lineIndex=%d has_bbox=%s text=%r",
            idx,
            step.stepId,
            step.elementType,
            step.lineIndex,
            step.bbox is not None,
            step.text[:120],  # cap log length
        )

DEBUG_IMAGE_DIR = Path("analysis_results/app_v2_canvas_images")
DEBUG_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

def _safe_ext(file_extension: str) -> str:
    ext = (file_extension or "").strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return ext if ext in {".png", ".jpg", ".jpeg", ".webp"} else ".bin"


def _safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", value or "")
    return cleaned[:128] or "unknown"




def _dump_canvas_image(payload: IOSAnalyzePayload) -> Optional[Path]:
    """Dump a base64-encoded canvas image to DEBUG_IMAGE_DIR with a unique filename."""
    canvas_image = payload.canvasImage

    if canvas_image is None:
        return None

    if len(canvas_image.dataBase64) > MAX_CANVAS_IMAGE_BASE64_CHARS:
        raise ValueError("canvasImage.dataBase64 too large for debug dump")

    raw_bytes = base64.b64decode(canvas_image.dataBase64, validate=True)
    if len(raw_bytes) > MAX_CANVAS_IMAGE_BYTES:
        raise ValueError("Decoded canvas image too large for debug dump")

    ext = _safe_ext(canvas_image.fileExtension)
    safe_session_id = _safe_filename_part(payload.sessionId)
    safe_request_id = _safe_filename_part(payload.requestId)

    file_path = DEBUG_IMAGE_DIR / f"{safe_session_id}_{safe_request_id}{ext}"
    file_path.write_bytes(raw_bytes)
    return file_path







@router.post("/check", response_model=CheckResponse)
async def check_work(request: CheckRequest) -> CheckResponse:
    return await orchestrator.run_check(request)


@router.post("/check/ios", response_model=CheckResponse)
async def check_work_ios(payload: IOSAnalyzePayload) -> CheckResponse:
    _log_ios_payload_summary(payload)

    image_path = None
    try:
        image_path = _dump_canvas_image(payload)
    except Exception as e:
        logger.warning(
            "Failed to save canvasImage debug artifact: error=%s canvasImage_present=%s base64_len=%s",
            type(e).__name__,
            payload.canvasImage is not None,
            len(payload.canvasImage.dataBase64) if payload.canvasImage else None,
        )

    if image_path:
        logger.info("Saved canvas image debug artifact to %s (%d bytes)", image_path, image_path.stat().st_size)
    try:
        canonical_request = ios_payload_to_check_request(
            payload,
            include_correction=False,
            include_debug_trace=True,
        )
    except ValueError as e:
        logger.warning("Adapter rejected iOS payload: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info(
        "Adapter success: canonical session_id=%s mapped_steps=%d",
        canonical_request.session_id,
        len(canonical_request.snapshot.steps),
    )
    return await orchestrator.run_check(canonical_request)

