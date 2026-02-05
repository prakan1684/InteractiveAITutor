
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Dict, Optional
from app.core.logger import get_logger
logger = get_logger(__name__)


class EvaluateMathInput(BaseModel):
    """Input for mathematical evaluation"""
    expression: str = Field(description="Mathematical expression to evaluate (e.g., '5 + 3')")
    student_answer: Optional[str] = Field(default=None, description="Student's answer if provided")
 
def evaluate_math_expression(expression: str, student_answer: Optional[str] = None) -> Dict:
    """
    Evaluate a mathematical expression and check student's answer.
    
    Use this to verify correctness of mathematical work.
    
    Args:
        expression: The math problem (e.g., "5 + 3")
        student_answer: What the student wrote (e.g., "8")
        
    Returns:
        Dict with is_correct, expected_answer, student_answer
    """
    logger.info(f"🔧 Tool: evaluate_math_expression")
    logger.info(f"   Expression: {expression}")
    
    try:
        # Simple evaluation - can be enhanced with sympy for complex math
        expected = eval(expression)
        
        result = {
            "expression": expression,
            "expected_answer": str(expected),
            "student_answer": student_answer,
            "is_correct": None
        }
        
        if student_answer:
            try:
                student_val = eval(student_answer)
                result["is_correct"] = (expected == student_val)
            except:
                result["is_correct"] = False
                result["error"] = "Could not parse student answer"
        
        logger.info(f"   Expected: {expected}, Correct: {result['is_correct']}")
        return result
        
    except Exception as e:
        logger.error(f"   Error: {e}")
        return {
            "expression": expression,
            "error": str(e),
            "is_correct": None
        }
 
# Create reasoning tool
evaluate_math_tool = StructuredTool.from_function(
    func=evaluate_math_expression,
    name="evaluate_math_expression",
    description=(
        "Evaluate a mathematical expression and check if student's answer is correct. "
        "Use this to verify arithmetic, algebra, or other mathematical work."
    ),
    args_schema=EvaluateMathInput
)
 

REASONING_TOOLS = [
    evaluate_math_tool,
]
