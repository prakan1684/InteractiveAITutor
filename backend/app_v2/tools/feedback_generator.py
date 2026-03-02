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
    ) -> FeedbackOutput:
        snapshot_summary = self._snapshot_summary(snapshot)
        evaluation_summary = self._evaluation_summary(evaluation_result)
        workdiff_summary = self._workdiff_summary(workdiff_result)
        session_state_summary = self._session_state_summary(session_state)
        goal_summary = self._goal_summary(agent_goal)
        prompt = self._build_prompt(
            snapshot_summary=snapshot_summary,
            evaluation_summary=evaluation_summary,
            workdiff_summary=workdiff_summary,
            session_state_summary=session_state_summary,
            goal_summary=goal_summary,
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

    def _build_prompt(
        self,
        *,
        snapshot_summary: Dict[str, Any],
        evaluation_summary: Dict[str, Any],
        workdiff_summary: Optional[Dict[str, Any]],
        session_state_summary: Optional[Dict[str, Any]],
        goal_summary: Dict[str, Any],
    ) -> str:
        return f"""
You are generating short, student-facing tutoring feedback for a math tutor app.

Write feedback that is:
- concise
- specific to the student's work
- supportive, but not cheesy
- focused on exactly one next step
- personalized to what changed, when workdiff context is available

If the student made progress, acknowledge it briefly.
If the student changed the wrong part, redirect gently.
If the solution looks correct, celebrate specifically and move forward.
If the work is uncertain or incomplete, explain what more to show.

Current agent goal:
{json.dumps(goal_summary, ensure_ascii=True)}

Evaluation result:
{json.dumps(evaluation_summary, ensure_ascii=True)}

Optional workdiff result:
{json.dumps(workdiff_summary, ensure_ascii=True)}

Optional session state:
{json.dumps(session_state_summary, ensure_ascii=True)}

Current snapshot:
{json.dumps(snapshot_summary, ensure_ascii=True)}

Return strict JSON only:
{{
  "title": "short title",
  "message": "1-2 sentence student-facing explanation",
  "hint": "short next-step hint",
  "encouragement": "optional short encouragement",
  "next_action": "string action",
  "focus_step_id": "optional step id",
  "focus_line_index": 0,
  "tone": "supportive"
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

        return FeedbackOutput(
            title=title,
            message=message,
            hint=hint,
            encouragement=encouragement,
            next_action=next_action,
            focus_step_id=focus_step_id,
            focus_line_index=focus_line_index,
            tone=tone,
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
