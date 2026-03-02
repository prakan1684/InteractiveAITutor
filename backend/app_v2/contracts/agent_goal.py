from typing import List, Optional

from pydantic import BaseModel, Field

from app_v2.domain.enums import TutorIntent


class AgentGoal(BaseModel):
    # Internal orchestration intent (safe to expose in debug/UI)
    intent: TutorIntent

    # Short user-facing goal label for the tutor panel
    title: str = Field(..., min_length=1)

    # Main user-facing explanation of what the agent is doing next
    message: str = Field(..., min_length=1)

    # UI hint for the next action the student can take (kept flexible in V1)
    next_action: str = Field(..., min_length=1)

    # Planned/used tools make the agent behavior explicit and traceable
    tools_planned: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)

    # Optional focus target for canvas-linked guidance
    focus_step_id: Optional[str] = None
    focus_line_index: Optional[int] = Field(default=None, ge=0)
