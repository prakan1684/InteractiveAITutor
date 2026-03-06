import json
from typing import Any, Dict, List, Optional
import re

from app.core.logger import get_logger
from app.services.ai_service import AIService
from app_v2.contracts.diff_feedback import ChangedStepRef, DiffResult, EvaluationResult
from app_v2.contracts.snapshot import Snapshot
from app_v2.domain.enums import EvaluationVerdict

logger = get_logger(__name__)

try:
    from sympy import simplify, sympify, latex
    from sympy.parsing.latex import parse_latex
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    logger.warning("SymPy not available - symbolic verification disabled")

logger = get_logger(__name__)


class SolutionEvaluatorTool:
    def __init__(self, model: str = "gpt-4o"):
        self.ai = AIService(default_model=model)

    async def evaluate(
        self,
        snapshot: Snapshot,
        workdiff_result: Optional[DiffResult] = None,
    ) -> EvaluationResult:
        snapshot_summary = self._snapshot_summary(snapshot)
        workdiff_summary = self._workdiff_summary(workdiff_result)
        prompt = self._build_prompt(snapshot_summary, workdiff_summary)

        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.content)
            result = self._to_evaluation_result(parsed, snapshot, workdiff_result)
            
            # Symbolic verification sanity check - run for all verdicts
            if SYMPY_AVAILABLE:
                symbolic_check = self._verify_with_sympy(snapshot)
                
                # Override LLM if symbolic verification disagrees
                if symbolic_check is True and result.verdict == EvaluationVerdict.NEEDS_REVISION:
                    # LLM said wrong, but SymPy says correct - trust SymPy
                    logger.warning(
                        "SymPy verification PASSED but LLM said NEEDS_REVISION for snapshot %s - overriding to CORRECT",
                        snapshot.snapshot_id
                    )
                    result.verdict = EvaluationVerdict.CORRECT
                    result.confidence = 0.95
                    result.reason_code = "verified_correct"
                    result.summary = "Your work is correct."
                    result.math_engine_used = True
                    
                elif symbolic_check is False and result.verdict == EvaluationVerdict.CORRECT:
                    # LLM said correct, but SymPy says wrong - trust SymPy
                    logger.warning(
                        "SymPy verification FAILED but LLM said CORRECT for snapshot %s - overriding to NEEDS_REVISION",
                        snapshot.snapshot_id
                    )
                    result.verdict = EvaluationVerdict.NEEDS_REVISION
                    result.confidence = 0.95
                    result.reason_code = "arithmetic_error_detected"
                    result.summary = "There's an arithmetic error in your work. Check your calculations."
                    result.math_engine_used = True
            
            return result
        except Exception as e:
            logger.error(f"Error evaluating solution: {e}")
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

CRITICAL: You must VERIFY THE MATH, not just check if it looks reasonable.
- Work through each algebraic step yourself
- Check arithmetic carefully (especially combining like terms, distributing negatives, sign errors)
- Verify that each step follows logically from the previous one
- Check that final answers are actually correct

Be conservative:
- If the work appears incomplete, ambiguous, or insufficiently legible/structured, return UNCERTAIN.
- If the student made ANY arithmetic or algebraic error, return NEEDS_REVISION.
- Return CORRECT only when you have VERIFIED the math is actually correct.

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

    def _verify_with_sympy(self, snapshot: Snapshot) -> Optional[bool]:
        """
        Attempt symbolic verification of algebraic work.
        Returns:
            True if verification passes
            False if verification fails (arithmetic error detected)
            None if verification cannot be performed
        """
        if not SYMPY_AVAILABLE or len(snapshot.steps) < 2:
            return None
        
        try:
            # Look for simplification problems: expression = result
            # Common pattern: "(3x^2 - 2x^2 + 4) - (4x^2 - 3) =" followed by "= -x^2 + 7"
            
            first_step_text = snapshot.steps[0].normalized_latex or snapshot.steps[0].raw_myscript
            last_step_text = snapshot.steps[-1].normalized_latex or snapshot.steps[-1].raw_myscript
            
            # Extract left side of first equation (before =)
            first_match = re.search(r'^(.+?)=', first_step_text)
            if not first_match:
                return None
            
            original_expr = first_match.group(1).strip()
            
            # Extract right side of last equation (after =)
            last_match = re.search(r'=(.+?)$', last_step_text)
            if not last_match:
                return None
            
            final_result = last_match.group(1).strip()
            
            # Parse and simplify both expressions
            original_sympy = parse_latex(original_expr)
            result_sympy = parse_latex(final_result)
            
            # Simplify the original and compare to claimed result
            simplified_original = simplify(original_sympy)
            simplified_result = simplify(result_sympy)
            
            # Check if they're equivalent
            difference = simplify(simplified_original - simplified_result)
            
            if difference == 0:
                logger.info(
                    "SymPy verification PASSED for snapshot %s: %s simplifies to %s",
                    snapshot.snapshot_id,
                    original_expr,
                    final_result
                )
                return True
            else:
                logger.warning(
                    "SymPy verification FAILED for snapshot %s: %s should be %s, not %s",
                    snapshot.snapshot_id,
                    original_expr,
                    simplified_original,
                    final_result
                )
                return False
                
        except Exception as e:
            logger.debug("SymPy verification could not be performed: %s", e)
            return None
    
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

