from typing import Optional
from pydantic import BaseModel, Field


class FeedbackOutput(BaseModel):
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    hint: str = Field(..., min_length=1)

    encouragement: Optional[str] = None

    next_action: str = Field(..., min_length=1)

    focus_step_id: Optional[str] = None
    focus_line_index: Optional[int] = Field(default=None, ge=0)

    tone: str = Field(default="supportive", min_length=1)
    
    # LaTeX expressions for iPad rendering
    problem_latex: Optional[str] = Field(default=None, description="The original problem in LaTeX")
    student_work_latex: Optional[str] = Field(default=None, description="Student's work/answer in LaTeX")
    correct_answer_latex: Optional[str] = Field(default=None, description="Correct answer in LaTeX (if applicable)")
    error_location_latex: Optional[str] = Field(default=None, description="Specific error step in LaTeX (if applicable)")


