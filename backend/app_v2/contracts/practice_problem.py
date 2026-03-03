



from pydantic import BaseModel, Field
from typing import List, Optional


class PracticeProblemResult(BaseModel):
    problem_text: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    difficulty: str = Field(..., min_length=1)

    hints: List[str] = Field(default_factory=list)

    source_snapshot_id: Optional[str] = None
