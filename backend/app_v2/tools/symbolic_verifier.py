from sympy import (
    simplify, expand, factor, solve, diff, integrate,
    Symbol, latex, trigsimp, Eq,
)
from sympy.parsing.latex import parse_latex
 
from app.core.logger import get_logger
from app_v2.contracts.verification import ClassificationResult, VerificationResult
from app_v2.domain.enums import ProblemType, VerificationMethod
 
logger = get_logger(__name__)
 


class SymbolicVerifierTool:
    """
    Universal symbolic math verifier.
    
    Given a ClassificationResult (problem type + expression + student answer),
    applies the correct SymPy operation and checks correctness.
    
    Returns:
        is_correct=True   → student is right (99% confidence)
        is_correct=False  → student is wrong (99% confidence, includes correct answer)
        is_correct=None   → can't verify (0% confidence, falls back to LLM)

    
    """
    def verify(self, classification: ClassificationResult) -> VerificationResult:
        if not classification.expression or not classification.student_answer:
            return self._cannot_verify("Missing Expression or Student Answer")
        
        if not classification.problem_type:
            return self._cannot_verify("Missing Problem Type")
        
        # Parse expressions (latex) into sympy objects
        try:
            expr = parse_latex(classification.expression)
            student = parse_latex(classification.student_answer)
            var = Symbol(classification.variable)
        except Exception as e:
            return self._cannot_verify(f"Failed to parse expressions: {str(e)}")
        
        #route to correct hander based on problem type
        dispatch = {
            ProblemType.DERIVATIVE: self._verify_derivative,
            ProblemType.INTEGRAL: self._verify_integral,
            ProblemType.SIMPLIFY: self._verify_simplify,
            ProblemType.FACTOR: self._verify_factor,
            ProblemType.EXPAND: self._verify_expand,
            ProblemType.SOLVE_EQUATION: self._verify_solve,
            ProblemType.TRIG_IDENTITY: self._verify_trig,
            ProblemType.LIMIT: self._verify_limit,
        }

        handler = dispatch.get(classification.problem_type)
        if handler is None:
            return self._cannot_verify(f"Unsupported problem type: {classification.problem_type}")


        try:
            return handler(expr, student, var)
        except Exception as e:
            return self._cannot_verify(f"Verification error: {str(e)}")



    def _verify_derivative(self, expr, student, var)-> VerificationResult:
        correct = diff(expr, var)
        return self._compare(correct, student, "derivative")

    def _verify_integral(self, expr, student, var)-> VerificationResult:
        diff_of_student = diff(student, var)
        difference = simplify(diff_of_student - expr)
        is_correct = (difference == 0)
        correct = integrate(expr, var)
        return VerificationResult(
            is_correct=is_correct,
            confidence=0.99,
            method=VerificationMethod.SYMBOLIC,
            explanation="Integral verified by differentiating student answer",
            correct_answer=latex(correct),
            details={
                "correct_integral": str(correct),
                "student_answer": str(student),
                "verified_by": "differentiation_check",
            },
        )

    def _verify_simplify(self, expr, student, var)-> VerificationResult:
        return self._compare(expr, student, "simplification")

    def _verify_factor(self, expr, student, var)-> VerificationResult:
        return self._compare(expr, student, "factoring")

    def _verify_expand(self, expr, student, var)-> VerificationResult:
        correct = expand(expr)
        return self._compare(correct, student, "expansion")

    def _verify_solve(self, expr, student, var)-> VerificationResult:
        try:
            if isinstance(expr, Eq):
                solutions = solve(expr, var)
            else:
                solutions = solve(expr, var)
        
            if not solutions:
                return self._cannot_verify("could not solve equation")
            
            for sol in solutions:
                if simplify(sol - student) == 0:
                    return VerificationResult(
                        is_correct=True,
                        confidence=0.99,
                        method=VerificationMethod.SYMBOLIC,
                        explanation="Equation solution verified",
                        correct_answer=str(solutions),
                        details={"solutions": [str(s) for s in solutions]},
                    )
                
            return VerificationResult(
                is_correct=False,
                confidence=0.99,
                method=VerificationMethod.SYMBOLIC,
                explanation="Student answer is not a solution to the equation",
                correct_answer=str(solutions),
                details={"solutions": [str(s) for s in solutions]},
            )
        
        except Exception as e:
            return self._cannot_verify(f"solution verification failed: {str(e)}")

    def _verify_trig(self, expr, student, var)-> VerificationResult:
        difference = trigsimp(expr - student)
        is_correct = (difference == 0)
        return VerificationResult(
            is_correct=is_correct,
            confidence=0.99,
            method=VerificationMethod.SYMBOLIC,
            explanation="Trig identity verification",
            correct_answer=latex(trigsimp(expr)),
            details={"difference": str(difference)},
        )

    def _verify_limit(self, expr, student, var)-> VerificationResult:
        return self._cannot_verify("limit verification not implemented")
    
    def _compare(self, correct, student, operation: str) -> VerificationResult:
        """
        Core comparison: checks if simplify(correct - student) == 0.
        Used by most handlers.
        """
        # Simplify both sides before comparing to handle algebraically equivalent forms
        correct_simplified = simplify(correct)
        student_simplified = simplify(student)
        
        difference = simplify(correct_simplified - student_simplified)
        is_correct = (difference == 0)
        correct_latex = latex(correct_simplified)

        if is_correct:
            logger.info("Symbolic %s verification PASSED", operation)
        else:
            logger.warning(
                "Symbolic %s verification FAILED: expected %s, got %s",
                operation, correct_latex, latex(student_simplified),
            )


        return VerificationResult(
            is_correct=is_correct,
            confidence=0.99 if is_correct else 0.1,
            method=VerificationMethod.SYMBOLIC,
            explanation="Symbolic verification",
            correct_answer=correct_latex,
            details={"correct": str(correct_simplified), "student": str(student_simplified), "difference": str(difference)},
        )

        
    def _cannot_verify(self, reason: str) -> VerificationResult:
        return VerificationResult(
            is_correct=None,
            confidence=0.0,
            method=VerificationMethod.NONE,
            explanation=reason,
        )

