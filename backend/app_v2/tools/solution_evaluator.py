import asyncio
import json
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.ai_service import AIService
from app_v2.contracts.diff_feedback import ChangedStepRef, DiffResult, EvaluationResult
from app_v2.contracts.snapshot import Snapshot
from app_v2.domain.enums import EvaluationVerdict
from app_v2.orchestrator.verification_orchestrator import VerificationOrchestrator
 
logger = get_logger(__name__)

class SolutionEvaluatorTool:
    def __init__(self, model: str = "gpt-4o"):
        self.ai = AIService(default_model=model)
        self.verification = VerificationOrchestrator()

    async def evaluate(
        self,
        snapshot: Snapshot,
        workdiff_result: Optional[DiffResult] = None,
    ) -> EvaluationResult:
        snapshot_summary = self._snapshot_summary(snapshot)
        workdiff_summary = self._workdiff_summary(workdiff_result)
        
        steps_latex = [
            step.normalized_latex or step.raw_myscript
            for step in snapshot.steps
        ]

        #run symbolic verification and llm evaluation in parallel
        verification_task = self.verification.verify(steps_latex)
        llm_task = self._llm_evaluate(snapshot_summary, workdiff_summary, snapshot, workdiff_result)
 
        verification_result, llm_result = await asyncio.gather(
            verification_task, llm_task, return_exceptions=True
        )

        #handle exceptions from parallel calls

        if isinstance(verification_result, Exception):
            logger.error(f"Verification failed: {verification_result}")
            verification_result = None
        
        if isinstance(llm_result, Exception):
            logger.error(f"LLM evaluation failed: {llm_result}")
            return EvaluationResult(
                verdict=EvaluationVerdict.UNCERTAIN,
                confidence=0.0,
                reason_code="evaluator_error",
                summary="I could not confidently evaluate this work yet.",
                target_step=None,
                math_engine_used=False,
            )

        #decision logic: symbolic verification overrides llm when available
        if verification_result is not None and verification_result.is_correct is not None:
            if verification_result.is_correct and llm_result.verdict != EvaluationVerdict.CORRECT:
                logger.warning(
                    "Symbolic verification PASSED but LLM said %s — overriding to CORRECT",
                    llm_result.verdict,
                )
                llm_result.verdict = EvaluationVerdict.CORRECT
                llm_result.confidence = verification_result.confidence
                llm_result.reason_code = "verified_correct"
                llm_result.summary = "Your work is mathematically correct."
                llm_result.math_engine_used = True
 
            elif not verification_result.is_correct and llm_result.verdict == EvaluationVerdict.CORRECT:
                logger.warning(
                    "Symbolic verification FAILED but LLM said CORRECT — overriding to NEEDS_REVISION",
                )
                llm_result.verdict = EvaluationVerdict.NEEDS_REVISION
                llm_result.confidence = verification_result.confidence
                llm_result.reason_code = "arithmetic_error_detected"
                llm_result.summary = (
                    f"There's a math error in your work. "
                    f"The correct answer should be: {verification_result.correct_answer}"
                    if verification_result.correct_answer
                    else "There's a math error in your work. Check your calculations."
                )
                llm_result.math_engine_used = True
        

        return llm_result

    async def _llm_evaluate(
        self,
        snapshot_summary: Dict[str, Any],
        workdiff_summary: Optional[Dict[str, Any]],
        snapshot: Snapshot,
        workdiff_result: Optional[DiffResult],
    ) -> EvaluationResult:
        """Run the LLM-based evaluation."""
        try:
            prompt = self._build_prompt(snapshot_summary, workdiff_summary)
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.content)
            return self._to_evaluation_result(parsed, snapshot, workdiff_result)
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            return EvaluationResult(
                verdict=EvaluationVerdict.UNCERTAIN,
                confidence=0.0,
                reason_code="evaluator_error",
                summary="I could not confidently evaluate this work yet.",
                target_step=None,
                math_engine_used=False,
            )

    def _snapshot_summary(self, snapshot: Snapshot) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        for idx, step in enumerate(snapshot.steps):
            bbox = step.bbox
            steps.append(
                {
                    "idx": idx,
                    "step_id": step.step_id,
                    "line_index": step.line_index,
                    "raw_myscript": step.raw_myscript,
                    "normalized_latex": step.normalized_latex,
                    "bbox": {
                        "x": bbox.x,
                        "y": bbox.y,
                        "width": bbox.width,
                        "height": bbox.height,
                    },
                }
            )

        return {
            "snapshot_id": snapshot.snapshot_id,
            "session_id": snapshot.session_id,
            "step_count": len(snapshot.steps),
            "steps": steps,
        }

    def _workdiff_summary(self, workdiff_result: Optional[DiffResult]) -> Optional[Dict[str, Any]]:
        if workdiff_result is None:
            return None

        return {
            "change_type": workdiff_result.change_type.value,
            "confidence": workdiff_result.confidence,
            "matched_steps": workdiff_result.matched_steps,
            "changed_steps": [
                {
                    "step_id": s.step_id,
                    "line_index": s.line_index,
                    "reason": s.reason,
                }
                for s in workdiff_result.changed_steps
            ],
            "summary": workdiff_result.summary,
        }

    def _build_prompt(
        self,
        snapshot_summary: Dict[str, Any],
        workdiff_summary: Optional[Dict[str, Any]],
    ) -> str:
        workdiff_json = json.dumps(workdiff_summary, ensure_ascii=True) if workdiff_summary is not None else "null"
        return f"""
You are evaluating a student's current math work from structured canvas steps.

Your job is to verify mathematical correctness:
- Check if each step follows logically from the previous one
- Verify arithmetic (combining like terms, distributing, sign errors)
- Allow for different valid approaches and intermediate simplifications
- Students may skip trivial steps (like multiplying by 1) - that's fine

Be balanced:
- If the work appears incomplete, ambiguous, or insufficiently legible/structured, return UNCERTAIN.
- If there is a clear mathematical error (wrong arithmetic, incorrect rule application), return NEEDS_REVISION.
- Return CORRECT when the mathematical reasoning and final answer are correct, even if steps are condensed.
- Don't penalize students for valid algebraic shortcuts or different solution paths.

You may use the optional work-change context to understand what they edited, but evaluate the CURRENT snapshot.

Current snapshot (structured):
{json.dumps(snapshot_summary, ensure_ascii=True)}

Optional workdiff context:
{workdiff_json}

Return strict JSON only:
{{
  "verdict": "CORRECT|NEEDS_REVISION|UNCERTAIN",
  "confidence": 0.0,
  "reason_code": "short_snake_case_code",
  "summary": "short explanation",
  "target_step": {{
    "step_id": "optional step id",
    "line_index": 0,
    "reason": "what step needs attention"
  }}
}}

Rules:
- Use only the allowed verdict strings.
- confidence must be between 0 and 1.
- If no specific step should be targeted, omit target_step or set it to null.
- Prefer UNCERTAIN over guessing.
""".strip()

    def _to_evaluation_result(
        self,
        parsed: Dict[str, Any],
        snapshot: Snapshot,
        workdiff_result: Optional[DiffResult] = None,
    ) -> EvaluationResult:
        verdict = self._coerce_verdict(parsed.get("verdict"))
        confidence = self._coerce_confidence(parsed.get("confidence"))
        reason_code = self._coerce_reason_code(parsed.get("reason_code"))
        summary = self._coerce_summary(parsed.get("summary"), verdict)
        target_step = self._coerce_target_step(parsed.get("target_step"))

        # If diff says a major rewrite or unknown and evaluator claims high confidence,
        # cap confidence slightly to keep routing conservative in V1.
        if workdiff_result is not None and workdiff_result.change_type.value in {"REWRITE", "UNKNOWN"}:
            confidence = min(confidence, 0.8)

        return EvaluationResult(
            verdict=verdict,
            confidence=confidence,
            reason_code=reason_code,
            summary=summary,
            target_step=target_step,
            math_engine_used=False,
        )

    
    
    def _coerce_verdict(self, value: Any) -> EvaluationVerdict:
        raw = str(value or "UNCERTAIN").upper()
        try:
            return EvaluationVerdict(raw)
        except ValueError:
            return EvaluationVerdict.UNCERTAIN

    def _coerce_confidence(self, value: Any) -> float:
        try:
            conf = float(value)
        except Exception:
            conf = 0.0
        return max(0.0, min(1.0, conf))

    def _coerce_reason_code(self, value: Any) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return "unknown"
        # Keep V1 machine-friendly without over-validating.
        return raw.replace(" ", "_")

    def _coerce_summary(self, value: Any, verdict: EvaluationVerdict) -> str:
        raw = str(value or "").strip()
        if raw:
            return raw
        if verdict == EvaluationVerdict.CORRECT:
            return "The current work appears correct."
        if verdict == EvaluationVerdict.NEEDS_REVISION:
            return "The current work likely needs revision."
        return "There is not enough reliable evidence to evaluate this work yet."

    def _coerce_target_step(self, value: Any) -> Optional[ChangedStepRef]:
        if value is None or not isinstance(value, dict):
            return None
        try:
            return ChangedStepRef(**value)
        except Exception:
            return None

