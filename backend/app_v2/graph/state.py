from typing import TypedDict, Optional, List

from app_v2.contracts.agent_goal import AgentGoal
from app_v2.contracts.check_api import CheckRequest, CheckResponse, Highlight
from app_v2.contracts.diff_feedback import DiffResult, EvaluationResult
from app_v2.contracts.feedback import FeedbackOutput
from app_v2.contracts.practice_problem import PracticeProblemResult
from app_v2.contracts.session_state import SessionAgentState, SessionMode
from app_v2.contracts.snapshot import Snapshot
from app_v2.contracts.trace import CheckTrace
from app_v2.domain.enums import CheckStatus


class TutorGraphState(TypedDict, total=False):
    request: CheckRequest
    trace: CheckTrace

    saved_snapshot: Snapshot
    previous_snapshot: Optional[Snapshot]
    session_state: SessionAgentState

    evaluation_result: Optional[EvaluationResult]
    workdiff_result: Optional[DiffResult]
    feedback_output: Optional[FeedbackOutput]
    practice_problem: Optional[PracticeProblemResult]

    agent_goal: Optional[AgentGoal]
    highlights: List[Highlight]

    status: Optional[CheckStatus]
    confidence: Optional[float]
    hint: Optional[str]
    next_mode: Optional[SessionMode]

    response: Optional[CheckResponse]
