import json
from typing import List
 
from app.core.logger import get_logger
from app.services.ai_service import AIService
from app_v2.contracts.verification import ClassificationResult
from app_v2.domain.enums import ProblemType
 
logger = get_logger(__name__)
 


class MathClassifierTool:
    """
    Uses lightweight LLM call to classify problem type and extract expressions needed for verification.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.ai = AIService(default_model=model)
    
    async def classify(self, steps_latex: List[str]) -> ClassificationResult:
        if not steps_latex:
            # Return default classification for empty steps
            return ClassificationResult()
        
        steps_formatted = "\n".join(
            f"Step {i}: {step}" for i, step in enumerate(steps_latex)
        )
        prompt = self._build_prompt(steps_formatted)

        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            parsed = json.loads(response.content)
            return self._parse_response(parsed)
        except Exception as e:
            logger.error(f"Math classifier failed: {e}")
            return ClassificationResult()
        
    def _build_prompt(self, steps_formatted: str) -> str:
        return f"""
You are a math problem classifier. Given a student's work (all steps), identify:
1. The PRIMARY problem type (what the problem is ultimately asking)
2. The original expression to verify against
3. The student's final answer
 
Student work:
{steps_formatted}
 
Return strict JSON:
{{
  "problem_type": "derivative|integral|simplify|factor|expand|solve_equation|trig_identity|limit|unknown",
  "expression": "the original math expression to operate on (clean LaTeX, no d/dx prefix, no integral sign, no = sign)",
  "variable": "the variable (usually x)",
  "student_answer": "the student's final simplified answer (clean LaTeX, no leading =)",
  "confidence": 0.0
}}
 
Rules:
- problem_type is the PRIMARY operation. If student takes a derivative then simplifies, type is "derivative"
- expression: extract ONLY the mathematical expression. For d/dx[(x^2+1)(x-3)], expression is "(x^2+1)(x-3)"
- student_answer: extract ONLY the final result. For "= 3x^2 - 6x + 1", answer is "3x^2 - 6x + 1"
- Ignore annotation steps where students write rules or formulas (e.g. "product rule: (fg)' = f'g + fg'")
- Clean LaTeX: remove \\left, \\right, convert \\dfrac to \\frac
- confidence: how certain you are (0.0 to 1.0)
""".strip()

    def _parse_response(self, parsed: dict) -> ClassificationResult:
        problem_type_str = parsed.get("problem_type", "unknown").lower()

        try:
            problem_type = ProblemType(problem_type_str)
        except ValueError:
            problem_type = ProblemType.UNKNOWN
        
        return ClassificationResult(
            problem_type=problem_type,
            expression=parsed.get("expression", ""),
            variable=parsed.get("variable", "x"),
            student_answer=parsed.get("student_answer", ""),
            confidence=float(parsed.get("confidence", 0.0))
        )

 

    
    