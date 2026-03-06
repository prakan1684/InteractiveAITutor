from datetime import datetime
from uuid import uuid4

from app.core.logger import get_logger
from app_v2.contracts.trace import CheckTrace, TraceEvent
from app_v2.domain.enums import TraceEventType, TutorIntent
from app_v2.contracts.agent_goal import AgentGoal
from app_v2.graph.state import TutorGraphState
from app_v2.stores.session_state_store import SessionStateStore
from app_v2.stores.snapshot_store import SnapshotStore
from app_v2.stores.trace_store import TraceStore
from app_v2.tools.feedback_generator import FeedbackGeneratorTool
from app_v2.tools.solution_evaluator import SolutionEvaluatorTool
from app_v2.contracts.diff_feedback import EvaluationResult
from app_v2.contracts.session_state import SessionMode
from app_v2.domain.enums import CheckStatus, EvaluationVerdict
from app_v2.contracts.check_api import CheckResponse
logger = get_logger(__name__)

snapshot_store = SnapshotStore()
trace_store = TraceStore()
session_state_store = SessionStateStore()

evaluator_tool = SolutionEvaluatorTool()
feedback_tool = FeedbackGeneratorTool()



def _goal(
    intent: TutorIntent,
    title: str,
    message: str,
    next_action: str,
    tools_planned: list[str] | None = None,
    tools_used: list[str] | None = None
) -> AgentGoal:
    return AgentGoal(
        intent=intent,
        title=title,
        message=message,
        next_action=next_action,
        tools_planned=tools_planned or [],
        tools_used=tools_used or [],
    )

def _resolve_hint(
    summary: str | None,
    fallback:str
) -> str:
    normalized = (summary or "").strip()    
    return normalized or fallback


def _route_decision(
    *,
    evaluation_result: EvaluationResult,
    previous_snapshot_exists: bool,
    current_mode,
) -> tuple[CheckStatus, float, str, AgentGoal, SessionMode]:
    verdict = evaluation_result.verdict
    conf = evaluation_result.confidence
    summary = evaluation_result.summary
    
    if verdict == EvaluationVerdict.CORRECT:
        goal = _goal(
            intent=TutorIntent.CELEBRATE_AND_ADVANCE,
            title="Advance",
            message="Your work looks correct. Next step is to move to a new practice problem.",
            next_action="NEW_PRACTICE",
            tools_planned=[],
            tools_used=["solution_evaluator"],
        )
        hint = _resolve_hint(summary, "Nice work. Your current solution looks correct.")
        return CheckStatus.VALID, conf, hint, goal, SessionMode.NORMAL

    if verdict == EvaluationVerdict.NEEDS_REVISION:
        goal = _goal(
            intent=TutorIntent.CORRECT_ACTIVE_ERROR,
            title="Revise This Step",
            message="There is an issue to fix. I’ll guide one revision at a time and re-check your update.",
            next_action="REVISE_AND_CHECK",
            tools_planned=["solution_evaluator"],
            tools_used=["solution_evaluator"],
        )
        hint = _resolve_hint(
            summary,
            "There is an issue in the current work. Revise this step and check again.",
        )
        return CheckStatus.INVALID, conf, hint, goal, SessionMode.CORRECTION_ACTIVE

    if not previous_snapshot_exists:
        goal = _goal(
            intent=TutorIntent.COLLECT_MORE_CONTEXT,
            title="Need One More Step",
            message="I need a bit more work shown before I can evaluate reliably.",
            next_action="ADD_STEP_AND_CHECK",
            tools_planned=["solution_evaluator"],
            tools_used=["solution_evaluator"],
        )
        hint = _resolve_hint(summary, "Add one more clear step, then press Check again.")
        return CheckStatus.NEED_MORE_CONTEXT, conf, hint, goal, SessionMode.NORMAL

    goal = _goal(
        intent=TutorIntent.HANDLE_UNCERTAINTY,
        title="Uncertain Evaluation",
        message="I can’t verify confidence in your solution.",
        next_action="CLARIFY_AND_CHECK",
        tools_planned=["solution_evaluator"],
        tools_used=["solution_evaluator"],
    )
    hint = _resolve_hint(
        summary,
        "I can’t verify this confidently yet. Clarify the next step and check again.",
    )
    return CheckStatus.UNCERTAIN, conf, hint, goal, SessionMode.NORMAL


async def load_context_node(state: TutorGraphState) -> dict:
    request = state["request"]
    started_at = datetime.utcnow()
    trace = CheckTrace(
        trace_id=f"trace_{uuid4().hex}",
        session_id=request.session_id,
        started_at=started_at,
        tool_calls=[],
        events=[],
    )
    saved_snapshot = snapshot_store.save(request.snapshot)
    trace.snapshot_id_after = saved_snapshot.snapshot_id

    session_state = session_state_store.get_or_default(request.session_id)

    previous_snapshot = None
    if request.last_snapshot_id:
        previous_snapshot = snapshot_store.get(request.last_snapshot_id)
        if previous_snapshot:
            trace.snapshot_id_before = previous_snapshot.snapshot_id

    trace.events.append(
        TraceEvent(
            event_type=TraceEventType.DECISION,
            message="Graph context loaded",
            details={
                "has_previous_snapshot": previous_snapshot is not None,
                "session_mode": session_state.mode.value,
                "step_count": len(saved_snapshot.steps),
            },
        )
    )

    return {
        "trace": trace,
        "saved_snapshot": saved_snapshot,
        "previous_snapshot": previous_snapshot,
        "session_state": session_state,
    }



async def evaluate_solution_node(state: TutorGraphState) -> dict:
    trace = state["trace"]
    saved_snapshot = state["saved_snapshot"]

    evaluation_result = await evaluator_tool.evaluate(
        snapshot=saved_snapshot,
        workdiff_result=None,
    )

    trace.events.append(
        TraceEvent(
            event_type=TraceEventType.TOOL_CALL,
            message="Solution evaluator completed",
            details={
                "tool": "solution_evaluator",
                "verdict": evaluation_result.verdict.value,
                "confidence": evaluation_result.confidence,
                "reason_code": evaluation_result.reason_code,
                "summary": evaluation_result.summary,
                "target_step": (
                    evaluation_result.target_step.model_dump()
                    if evaluation_result.target_step
                    else None
                ),
            },
        )
    )
    
    return {
        "evaluation_result": evaluation_result,
        "trace": trace
    }



async def route_decision_node(state: TutorGraphState) -> dict:
    trace = state["trace"]
    evaluation_result = state["evaluation_result"]
    previous_snapshot = state.get("previous_snapshot")
    session_state = state["session_state"]

    status, confidence, hint, agent_goal, next_mode = _route_decision(
        evaluation_result=evaluation_result,
        previous_snapshot_exists=previous_snapshot is not None,
        current_mode=session_state.mode,
    )

    trace.events.append(
        TraceEvent(
            event_type=TraceEventType.DECISION,
            message="Decision routed",
            details={
                "status": status.value,
                "confidence": confidence,
                "intent": agent_goal.intent.value,
                "next_action": agent_goal.next_action,
                "next_mode": next_mode.value,
            },
        )
    )

    return {
        "status": status,
        "confidence": confidence,
        "hint": hint,
        "agent_goal": agent_goal,
        "next_mode": next_mode,
        "trace": trace,
    }


async def generate_feedback_node(state: TutorGraphState) -> dict:
    trace = state["trace"]
    saved_snapshot = state["saved_snapshot"]
    evaluation_result = state["evaluation_result"]
    session_state = state["session_state"]
    agent_goal = state["agent_goal"]

    feedback_output = await feedback_tool.generate(
        snapshot=saved_snapshot,
        evaluation_result=evaluation_result,
        agent_goal=agent_goal,
        workdiff_result=None,
        session_state=session_state,
    )

    agent_goal.title = feedback_output.title
    agent_goal.message = feedback_output.message
    agent_goal.next_action = feedback_output.next_action
    agent_goal.focus_step_id = feedback_output.focus_step_id
    agent_goal.focus_line_index = feedback_output.focus_line_index

    trace.events.append(
        TraceEvent(
            event_type=TraceEventType.TOOL_CALL,
            message="Feedback generated",
            details={
                "tool": "feedback_generator",
                "title": feedback_output.title,
                "next_action": feedback_output.next_action,
                "focus_step_id": feedback_output.focus_step_id,
                "focus_line_index": feedback_output.focus_line_index,
                "tone": feedback_output.tone,
            },
        )
    )

    return {
        "feedback_output": feedback_output,
        "hint": feedback_output.hint,
        "agent_goal": agent_goal,
        "trace": trace,
    }

async def finalize_response_node(state: TutorGraphState) -> dict:
    trace = state["trace"]
    status = state["status"]
    confidence = state["confidence"]
    hint = state["hint"]
    agent_goal = state["agent_goal"]
    saved_snapshot = state["saved_snapshot"]
    session_state = state["session_state"]
    next_mode = state["next_mode"]



    #switching to next mode
    session_state.mode = next_mode
    session_state.updated_at = datetime.utcnow()
    session_state_store.save(session_state)

    completed_at = datetime.utcnow()
    latency_ms = int((completed_at - trace.started_at).total_seconds() * 1000)


    trace.final_status = status
    trace.final_confidence = confidence
    trace.completed_at = completed_at
    trace.total_latency_ms = latency_ms


    trace.events.append(
        TraceEvent(
            event_type=TraceEventType.FINAL,
            message="Graph check completed",
            details={
                "status": status.value,
                "confidence": confidence,
                "new_snapshot_id": saved_snapshot.snapshot_id,
            },
        )
    )

    saved_trace = trace_store.save(trace)

    response = CheckResponse(
        status=status,
        confidence=confidence,
        highlights=[],
        hint=hint,
        agent_goal=agent_goal,
        correction=None,
        new_snapshot_id=saved_snapshot.snapshot_id,
        trace_id=saved_trace.trace_id,
        debug_trace_summary=None,
    )

    return {
        "response": response,
    }





