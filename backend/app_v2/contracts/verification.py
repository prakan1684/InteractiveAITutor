from typing import Optional
from pydantic import BaseModel, Field
from app_v2.domain.enums import ProblemType, VerificationMethod


class ClassificationResult(BaseModel):
    problem_type: ProblemType = ProblemType.UNKNOWN
    expression: Optional[str] = None
    variable: str = "x"
    student_answer: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class VerificationResult(BaseModel):
    is_correct: Optional[bool] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    method: VerificationMethod = VerificationMethod.NONE
    explanation: str = ""
    correct_answer: Optional[str] = None
    details: dict = {}