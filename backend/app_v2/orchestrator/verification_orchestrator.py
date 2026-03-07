from typing import List
 
from app.core.logger import get_logger
from app_v2.contracts.verification import VerificationResult
from app_v2.domain.enums import VerificationMethod
from app_v2.tools.math_classifier import MathClassifierTool
from app_v2.tools.symbolic_verifier import SymbolicVerifierTool
 
logger = get_logger(__name__)


class VerificationOrchestrator:
    """
    Coordinates multi-layer verification:
    1. LLM classifies problem type and extracts expressions
    2. SymPy verifies symbolically
    3. If SymPy can't verify, returns None (caller uses LLM evaluator as fallback)
    """

    def __init__(self):
        self.classifier = MathClassifierTool()
        self.symbolic_verifier = SymbolicVerifierTool()
    
    async def verify(self, steps_latex: List[str]) -> VerificationResult:
        if not steps_latex or len(steps_latex) < 2:
            return VerificationResult(
                explanation="Not enough steps to verify"
            )
        #layer 1 LLM CLASSIFICATION
        classification = await self.classifier.classify(steps_latex)

        logger.info(
            "Math classification: type=%s expression=%s student_answer=%s confidence=%.2f",
            classification.problem_type,
            classification.expression,
            classification.student_answer,
            classification.confidence,
        )

        #layer 2 SYMBOLIC VERIFICATION
        result = self.symbolic_verifier.verify(
            classification=classification
        )

        logger.info(
            "Verification result: is_correct=%s confidence=%.2f method=%s explanation=%s",
            result.is_correct,
            result.confidence,
            result.method,
            result.explanation,
        )


        return result
