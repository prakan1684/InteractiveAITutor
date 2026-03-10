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
        logger.info("=" * 80)
        logger.info("VERIFICATION ORCHESTRATOR START")
        logger.info("=" * 80)
        logger.info("Input: %d steps", len(steps_latex))
        for i, step in enumerate(steps_latex):
            logger.info("  Step %d: %s", i, step[:100] + "..." if len(step) > 100 else step)
        
        if not steps_latex or len(steps_latex) < 2:
            logger.warning("Not enough steps to verify (need at least 2)")
            return VerificationResult(
                explanation="Not enough steps to verify"
            )
        
        # Layer 1: LLM CLASSIFICATION
        logger.info("-" * 80)
        logger.info("LAYER 1: LLM CLASSIFIER")
        logger.info("-" * 80)
        classification = await self.classifier.classify(steps_latex)

        logger.info("Classification result:")
        logger.info("  Problem type: %s", classification.problem_type)
        logger.info("  Expression: %s", classification.expression)
        logger.info("  Variable: %s", classification.variable)
        logger.info("  Student answer: %s", classification.student_answer)
        logger.info("  Confidence: %.2f", classification.confidence)

        # Layer 2: SYMBOLIC VERIFICATION
        logger.info("-" * 80)
        logger.info("LAYER 2: SYMBOLIC VERIFIER")
        logger.info("-" * 80)
        result = self.symbolic_verifier.verify(
            classification=classification
        )

        logger.info("Symbolic verification result:")
        logger.info("  Is correct: %s", result.is_correct)
        logger.info("  Confidence: %.2f", result.confidence)
        logger.info("  Method: %s", result.method)
        logger.info("  Explanation: %s", result.explanation)
        if result.correct_answer:
            logger.info("  Correct answer: %s", result.correct_answer)
        logger.info("=" * 80)
        logger.info("VERIFICATION ORCHESTRATOR END")
        logger.info("=" * 80)

        return result
