import json
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.ai_service import AIService
from app_v2.contracts.agent_goal import AgentGoal
from app_v2.contracts.diff_feedback import DiffResult, EvaluationResult
from app_v2.contracts.feedback import FeedbackOutput
from app_v2.contracts.session_state import SessionAgentState
from app_v2.contracts.snapshot import Snapshot

logger = get_logger(__name__)


class FeedbackGeneratorTool:
    def __init__(self, model: str = "gpt-4o"):
        self.ai = AIService(default_model=model)

    async def generate(
        self,
        *,
        snapshot: Snapshot,
        evaluation_result: EvaluationResult,
        agent_goal: AgentGoal,
        workdiff_result: Optional[DiffResult] = None,
        session_state: Optional[SessionAgentState] = None,
        original_error_snapshot: Optional[Snapshot] = None,
        verification_result: Optional[Any] = None,
    ) -> FeedbackOutput:
        snapshot_summary = self._snapshot_summary(snapshot)
        evaluation_summary = self._evaluation_summary(evaluation_result)
        workdiff_summary = self._workdiff_summary(workdiff_result)
        session_state_summary = self._session_state_summary(session_state)
        goal_summary = self._goal_summary(agent_goal)
        original_error_summary = self._snapshot_summary(original_error_snapshot) if original_error_snapshot else None
        verification_summary = self._verification_summary(verification_result) if verification_result else None
        prompt = self._build_prompt(
            snapshot_summary=snapshot_summary,
            evaluation_summary=evaluation_summary,
            workdiff_summary=workdiff_summary,
            session_state_summary=session_state_summary,
            goal_summary=goal_summary,
            original_error_summary=original_error_summary,
            verification_summary=verification_summary,
        )

        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.content)
            return self._to_feedback_output(parsed, agent_goal)
        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            return self._fallback_feedback(agent_goal)

    def _snapshot_summary(self, snapshot: Snapshot) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        for idx, step in enumerate(snapshot.steps):
            steps.append(
                {
                    "idx": idx,
                    "step_id": step.step_id,
                    "line_index": step.line_index,
                    "raw_myscript": step.raw_myscript,
                    "normalized_latex": step.normalized_latex,
                }
            )

        return {
            "snapshot_id": snapshot.snapshot_id,
            "session_id": snapshot.session_id,
            "step_count": len(snapshot.steps),
            "steps": steps,
        }

    def _evaluation_summary(self, evaluation_result: EvaluationResult) -> Dict[str, Any]:
        return {
            "verdict": evaluation_result.verdict.value,
            "confidence": evaluation_result.confidence,
            "reason_code": evaluation_result.reason_code,
            "summary": evaluation_result.summary,
            "target_step": (
                evaluation_result.target_step.model_dump()
                if evaluation_result.target_step
                else None
            ),
        }

    def _workdiff_summary(self, workdiff_result: Optional[DiffResult]) -> Optional[Dict[str, Any]]:
        if workdiff_result is None:
            return None

        return {
            "change_type": workdiff_result.change_type.value,
            "confidence": workdiff_result.confidence,
            "matched_steps": workdiff_result.matched_steps,
            "changed_steps": [step.model_dump() for step in workdiff_result.changed_steps],
            "summary": workdiff_result.summary,
        }

    def _session_state_summary(
        self,
        session_state: Optional[SessionAgentState],
    ) -> Optional[Dict[str, Any]]:
        if session_state is None:
            return None

        return {
            "mode": session_state.mode.value,
            "active_reason_code": session_state.active_reason_code,
            "active_step_id": session_state.active_step_id,
            "active_line_index": session_state.active_line_index,
        }

    def _goal_summary(self, agent_goal: AgentGoal) -> Dict[str, Any]:
        return {
            "intent": agent_goal.intent.value,
            "title": agent_goal.title,
            "message": agent_goal.message,
            "next_action": agent_goal.next_action,
            "tools_planned": agent_goal.tools_planned,
            "tools_used": agent_goal.tools_used,
        }
    
    def _verification_summary(self, verification_result: Any) -> Optional[Dict[str, Any]]:
        """Extract verification details for more specific feedback"""
        if not verification_result:
            return None
        
        return {
            "is_correct": getattr(verification_result, "is_correct", None),
            "confidence": getattr(verification_result, "confidence", 0.0),
            "method": getattr(verification_result, "method", None),
            "explanation": getattr(verification_result, "explanation", ""),
            "correct_answer": getattr(verification_result, "correct_answer", None),
            "details": getattr(verification_result, "details", {}),
        }

    def _build_prompt(
        self,
        *,
        snapshot_summary: Dict[str, Any],
        evaluation_summary: Dict[str, Any],
        workdiff_summary: Optional[Dict[str, Any]],
        session_state_summary: Optional[Dict[str, Any]],
        goal_summary: Dict[str, Any],
        original_error_summary: Optional[Dict[str, Any]],
        verification_summary: Optional[Dict[str, Any]],
    ) -> str:
        return f"""
You are generating detailed, personalized tutoring feedback for a math tutor app that renders LaTeX.

Write feedback that is:
- SPECIFIC to the exact problem and student's work (include LaTeX expressions)
- Supportive and encouraging (but not cheesy)
- Detailed about what they did right/wrong
- Includes the actual math expressions they worked with

IMPORTANT - INCLUDE LATEX:
- Extract the original problem from the student's first step(s) and include it in problem_latex
- Extract the student's final answer and include it in student_work_latex
- If there's an error, include the correct answer in correct_answer_latex
- If there's a specific error step, include it in error_location_latex
- Use clean LaTeX (remove \\left, \\right, \\dfrac → \\frac)

TONE GUIDELINES:
- Start with what they did RIGHT before pointing out errors
- Use encouraging language ("Good start", "You're on the right track", "Nice work on...")
- Frame corrections as learning opportunities, not failures
- Be SPECIFIC about the math: "You correctly applied the product rule to $(x^2+1)(x+3)$..."
- Reference their actual work: "Your answer of $3x^2+6x+1$ is correct!"

SPECIAL CASE - CORRECTION SUCCESS:
If original_error_snapshot is provided AND the current evaluation is CORRECT, this means the student successfully fixed their mistake!
- Celebrate their correction specifically
- Reference what they fixed (compare original error to current correct work)
- Acknowledge the learning moment ("You caught the sign error and fixed it!")
- Be enthusiastic but genuine

VERIFICATION CONTEXT:
If verification_summary is provided, use it to be more specific:
- If method is "symbolic", mention that their work was verified mathematically
- If correct_answer is provided, include it in your feedback and correct_answer_latex
- Reference the specific problem type (derivative, integral, simplify, etc.)

Current agent goal:
{json.dumps(goal_summary, ensure_ascii=True)}

Evaluation result:
{json.dumps(evaluation_summary, ensure_ascii=True)}

Verification details (symbolic math engine results):
{json.dumps(verification_summary, ensure_ascii=True) if verification_summary else "null"}

Optional workdiff result:
{json.dumps(workdiff_summary, ensure_ascii=True)}

Optional session state:
{json.dumps(session_state_summary, ensure_ascii=True)}

Current snapshot:
{json.dumps(snapshot_summary, ensure_ascii=True)}

Original error snapshot (if student is fixing a mistake):
{json.dumps(original_error_summary, ensure_ascii=True) if original_error_summary else "null"}

Return strict JSON only:
{{
  "title": "short title",
  "message": "2-3 sentence detailed explanation with specific references to their work",
  "hint": "short next-step hint",
  "encouragement": "optional short encouragement",
  "next_action": "string action",
  "focus_step_id": "optional step id",
  "focus_line_index": 0,
  "tone": "supportive",
  "problem_latex": "original problem in clean LaTeX (no \\\\left/\\\\right, use \\\\frac not \\\\dfrac)",
  "student_work_latex": "student's answer in clean LaTeX",
  "correct_answer_latex": "correct answer in clean LaTeX (if applicable)",
  "error_location_latex": "specific error step in clean LaTeX (if applicable)"
}}

Rules:
- Keep title, message, and hint non-empty.
- Keep message to 1-2 short sentences.
- next_action should align with the current agent goal unless there is a strong reason not to.
- Prefer focusing on one step if the evaluation has a target_step.
- Return JSON only.
""".strip()

    def _to_feedback_output(self, parsed: Dict[str, Any], agent_goal: AgentGoal) -> FeedbackOutput:
        title = self._coerce_non_empty(parsed.get("title"), agent_goal.title)
        message = self._coerce_non_empty(parsed.get("message"), agent_goal.message)
        hint = self._coerce_non_empty(parsed.get("hint"), "Try the next step and check again.")
        encouragement = self._coerce_optional_text(parsed.get("encouragement"))
        next_action = self._coerce_non_empty(parsed.get("next_action"), agent_goal.next_action)
        focus_step_id = self._coerce_optional_text(parsed.get("focus_step_id"))
        focus_line_index = self._coerce_optional_line_index(parsed.get("focus_line_index"))
        tone = self._coerce_non_empty(parsed.get("tone"), "supportive")
        
        # Extract LaTeX expressions
        problem_latex = self._coerce_optional_text(parsed.get("problem_latex"))
        student_work_latex = self._coerce_optional_text(parsed.get("student_work_latex"))
        correct_answer_latex = self._coerce_optional_text(parsed.get("correct_answer_latex"))
        error_location_latex = self._coerce_optional_text(parsed.get("error_location_latex"))

        return FeedbackOutput(
            title=title,
            message=message,
            hint=hint,
            encouragement=encouragement,
            next_action=next_action,
            focus_step_id=focus_step_id,
            focus_line_index=focus_line_index,
            tone=tone,
            problem_latex=problem_latex,
            student_work_latex=student_work_latex,
            correct_answer_latex=correct_answer_latex,
            error_location_latex=error_location_latex,
        )

    def _fallback_feedback(self, agent_goal: AgentGoal) -> FeedbackOutput:
        return FeedbackOutput(
            title=agent_goal.title,
            message=agent_goal.message,
            hint="Try the next step and check again.",
            encouragement=None,
            next_action=agent_goal.next_action,
            focus_step_id=agent_goal.focus_step_id,
            focus_line_index=agent_goal.focus_line_index,
            tone="supportive",
        )

    def _coerce_non_empty(self, value: Any, fallback: str) -> str:
        raw = str(value or "").strip()
        return raw or fallback

    def _coerce_optional_text(self, value: Any) -> Optional[str]:
        raw = str(value or "").strip()
        return raw or None

    def _coerce_optional_line_index(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            line_index = int(value)
        except Exception:
            return None
        return line_index if line_index >= 0 else None
