import json
from typing import Any, Dict, List

from app.core.logger import get_logger
from app.services.ai_service import AIService
from app_v2.contracts.practice_problem import PracticeProblemResult
from app_v2.contracts.snapshot import Snapshot

logger = get_logger(__name__)


class PracticeProblemGeneratorTool:
    def __init__(self, model: str = "gpt-4o"):
        self.ai = AIService(default_model=model)

    async def generate(self, snapshot: Snapshot) -> PracticeProblemResult:
        snapshot_summary = self._snapshot_summary(snapshot)
        prompt = self._build_prompt(snapshot_summary)

        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.content)
            return self._to_practice_problem_result(parsed, snapshot)
        except Exception as e:
            logger.error(f"Error generating practice problem: {e}")
            return PracticeProblemResult(
                problem_text="Solve for x: 4x + 6 = 18",
                topic="linear_equation",
                difficulty="easy",
                hints=["Subtract 6 from both sides."],
                source_snapshot_id=snapshot.snapshot_id,
            )

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

    def _build_prompt(self, snapshot_summary: Dict[str, Any]) -> str:
        return f"""
You are generating the next practice problem for a math tutor app.

The student has just correctly solved a problem shown in the snapshot below.
Generate ONE new practice problem of a similar topic and difficulty.

Requirements:
- Keep it appropriate for iPad handwritten solving.
- Do not repeat the exact same problem.
- Keep it concise.
- Prefer algebra problems similar in style when the snapshot shows algebraic solving.
- Return strict JSON only.

Solved snapshot:
{json.dumps(snapshot_summary, ensure_ascii=True)}

Return JSON:
{{
  "problem_text": "text of the new problem",
  "topic": "short topic label",
  "difficulty": "easy|medium|hard",
  "hints": ["optional hint 1"]
}}
""".strip()

    def _to_practice_problem_result(
        self,
        parsed: Dict[str, Any],
        snapshot: Snapshot,
    ) -> PracticeProblemResult:
        problem_text = self._coerce_non_empty(
            parsed.get("problem_text"),
            "Solve for x: 4x + 6 = 18",
        )
        topic = self._coerce_non_empty(parsed.get("topic"), "linear_equation")
        difficulty = self._coerce_non_empty(parsed.get("difficulty"), "easy")

        raw_hints = parsed.get("hints", [])
        hints: List[str] = []
        if isinstance(raw_hints, list):
            for item in raw_hints:
                text = str(item).strip()
                if text:
                    hints.append(text)

        return PracticeProblemResult(
            problem_text=problem_text,
            topic=topic,
            difficulty=difficulty,
            hints=hints,
            source_snapshot_id=snapshot.snapshot_id,
        )

    def _coerce_non_empty(self, value: Any, fallback: str) -> str:
        raw = str(value or "").strip()
        return raw or fallback
