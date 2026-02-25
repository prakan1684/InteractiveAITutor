import json
from typing import Any, Dict, List

from app.services.ai_service import AIService
from app_v2.contracts.diff_feedback import ChangedStepRef, DiffResult
from app_v2.contracts.snapshot import Snapshot
from app_v2.domain.enums import ChangeType
from app.core.logger import get_logger

logger = get_logger(__name__)


class WorkDiffTool:
    def __init__(self, model: str = "gpt-4o"):
        self.ai = AIService(default_model=model)

    async def compute_diff(self, before: Snapshot, after: Snapshot) -> DiffResult:

        before_summary = self._snapshot_summary(before)
        after_summary = self._snapshot_summary(after)
        
        prompt = self._build_prompt(before_summary, after_summary)
        try:
            response = await self.ai.complete(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )


            parsed = json.loads(response.content)
            return self._to_diff_result(before, after, parsed)
        except Exception as e:
            logger.error(f"Error computing diff: {e}")
            # Safe fallback: preserve flow, don't crash orchestrator
            return DiffResult(
                session_id=after.session_id,
                snapshot_id_before=before.snapshot_id or "unknown_before",
                snapshot_id_after=after.snapshot_id or "unknown_after",
                change_type=ChangeType.UNKNOWN,
                confidence=0.0,
                step_count_before=len(before.steps),
                step_count_after=len(after.steps),
                step_count_delta=len(after.steps) - len(before.steps),
                matched_steps=0,
                changed_steps=[],
                summary=f"LLM diff failed: {type(e).__name__}",
            )
    
    

    def _snapshot_summary(self, snap: Snapshot) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []

        for idx, step in enumerate(snap.steps):
            bbox = step.bbox
            cx = bbox.x + (bbox.width / 2)
            cy = bbox.y + (bbox.height / 2)
            steps.append({
                "idx": idx,
                "step_id": step.step_id,
                "line_index": step.line_index,
                "text": step.raw_myscript,
                "bbox": {
                    "x": bbox.x,
                    "y": bbox.y,
                    "width": bbox.width,
                    "height": bbox.height,
                },
                "center": {
                    "x": cx,
                    "y": cy,
                },
            })
        return {
            "snapshot_id": snap.snapshot_id,
            "session_id": snap.session_id,
            "step_count": len(snap.steps),
            "steps": steps,
        }

    def _build_prompt(self, before: Dict[str, Any], after: Dict[str, Any]) -> str:
        return f"""
You are classifying how a student's math canvas changed between two snapshots.

Coordinate semantics:
- origin is top-left (0,0)
- bbox format is (x, y, width, height)
- x increases to the right
- y increases downward
- positions are normalized to [0,1]

Task:
Classify the change into ONE of:
- APPEND (student continued same problem by adding new step(s))
- EDIT_IN_PLACE (student edited/replaced an earlier step while staying on same problem)
- REWRITE (major rewrite / content replaced)
- UNKNOWN (cannot tell reliably)

Use step text, line_index, and bbox geometry. Be conservative. If uncertain, return UNKNOWN.

Previous snapshot:
{json.dumps(before, ensure_ascii=True)}

Current snapshot:
{json.dumps(after, ensure_ascii=True)}

Return strict JSON:
{{
  "change_type": "APPEND|EDIT_IN_PLACE|REWRITE|UNKNOWN",
  "confidence": 0.0,
  "matched_steps": 0,
  "changed_steps": [
    {{"step_id": "optional", "line_index": 0, "reason": "text_changed|added|removed|moved"}}
  ],
  "summary": "short explanation"
}}
""".strip()



    def _to_diff_result(self, before: Snapshot, after: Snapshot, parsed: Dict[str, Any]) -> DiffResult:
        """
        Takes in LLM json output and converts it to a DiffResult object.
        """

        raw_change = str(parsed.get("change_type", "UNKNOWN")).upper()
        try:
            change_type = ChangeType(raw_change)
        except ValueError:
            change_type = ChangeType.UNKNOWN
        
        raw_changed_steps = parsed.get("changed_steps", []) or []
        changed_steps: List[ChangedStepRef] = []
        for item in raw_changed_steps:
            if not isinstance(item, dict):
                continue
            try:
                changed_steps.append(ChangedStepRef(**item))
            except Exception:
                continue
        
        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        matched_steps = parsed.get("matched_steps", 0)
        try:
            matched_steps = int(matched_steps)
        except Exception:
            matched_steps = 0
        matched_steps = max(0, matched_steps)

        return DiffResult(
            session_id=after.session_id,
            snapshot_id_before=before.snapshot_id or "unknown_before",
            snapshot_id_after=after.snapshot_id or "unknown_after",
            change_type=change_type,
            confidence=confidence,
            step_count_before=len(before.steps),
            step_count_after=len(after.steps),
            step_count_delta=len(after.steps) - len(before.steps),
            matched_steps=matched_steps,
            changed_steps=changed_steps,
            summary=str(parsed.get("summary", "No summary")),
        )
