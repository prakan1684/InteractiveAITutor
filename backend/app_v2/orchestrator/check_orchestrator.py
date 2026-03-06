from datetime import datetime
from uuid import uuid4
from typing import List
import asyncio

from app.core.logger import get_logger
from app_v2.contracts.agent_goal import AgentGoal
from app_v2.contracts.snapshot import Snapshot
from app_v2.contracts.check_api import CheckRequest, CheckResponse, Highlight
from app_v2.contracts.diff_feedback import DiffResult, EvaluationResult
from app_v2.contracts.session_state import SessionMode
from app_v2.contracts.trace import CheckTrace, TraceEvent
from app_v2.domain.enums import (
    ChangeType,
    CheckStatus,
    EvaluationVerdict,
    TraceEventType,
    TutorIntent,
    HighlightType,
)
from app_v2.stores.session_state_store import SessionStateStore
from app_v2.stores.snapshot_store import SnapshotStore
from app_v2.stores.trace_store import TraceStore
from app_v2.tools.solution_evaluator import SolutionEvaluatorTool
from app_v2.tools.workdiff import WorkDiffTool
from app_v2.tools.feedback_generator import FeedbackGeneratorTool
from app_v2.contracts.practice_problem import PracticeProblemResult
from app_v2.tools.practice_problem_generator import PracticeProblemGeneratorTool




logger = get_logger(__name__)



class CheckOrchestrator:
    """
    Responsibilities:
    1. persist snapshots
    2. early agentic branching decisions
    3. persist traces
    """
    def __init__(self,
     snapshot_store: SnapshotStore, 
     trace_store: TraceStore,
     session_state_store: SessionStateStore
     ):
        self.snapshot_store = snapshot_store
        self.trace_store = trace_store
        self.session_state_store = session_state_store
        self.workdiff_tool = WorkDiffTool()
        self.evaluator_tool = SolutionEvaluatorTool()
        self.feedback_tool = FeedbackGeneratorTool()
        self.practice_problem_generator_tool = PracticeProblemGeneratorTool()

    async def _retry_llm_call(self, func, *args, max_retries=2, **kwargs):
        """Retry LLM calls with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    "LLM call attempt %d/%d failed: %s - retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    type(e).__name__,
                    0.5 * (2 ** attempt)
                )
                await asyncio.sleep(0.5 * (2 ** attempt))
    
    async def run_check(self, request: CheckRequest) -> CheckResponse:
        started_at = datetime.utcnow()

        #create the trace
        trace = CheckTrace(
            trace_id = f"trace_{uuid4().hex}",
            session_id = request.session_id,
            started_at = started_at,
            tool_calls = [],
            events = []
        )
        
        # persist current snapshot to the snapshot store
        saved_snapshot = self.snapshot_store.save(request.snapshot)
        trace.snapshot_id_after = saved_snapshot.snapshot_id

        #load session state and previous snapshot if it exists
        session_state = self.session_state_store.get_or_default(request.session_id)
        previous_snapshot = None
        if request.last_snapshot_id:
            previous_snapshot = self.snapshot_store.get(request.last_snapshot_id)
            if previous_snapshot:
                trace.snapshot_id_before = previous_snapshot.snapshot_id

        
        #evaluate current work (no previous snapshot needed)
        evaluation_result = await self._retry_llm_call(
            self.evaluator_tool.evaluate,
            snapshot=saved_snapshot,
            workdiff_result=None
        )

        self._trace_evaluator(trace, evaluation_result)

        #we will only check workdiff if previous snap exists and we are in "correction" mode
        workdiff_result = None
        should_run_diff= (
            session_state.mode == SessionMode.CORRECTION_ACTIVE
            and previous_snapshot is not None
        )

        if should_run_diff:
            workdiff_result = await self.workdiff_tool.compute_diff(
                before=previous_snapshot,
                after=saved_snapshot
            )
            self._trace_workdiff(trace, workdiff_result)
        

        #now we route to response + next mode + goal
        status, confidence, hint, agent_goal, next_mode = self._route_decision(
            evaluation_result=evaluation_result,
            workdiff_result=workdiff_result,
            previous_snapshot_exists=previous_snapshot is not None,
            current_mode=session_state.mode,
        )


        #generate feedback 
        
        # Load original error snapshot if we're in correction mode for celebration context
        original_error_snapshot = None
        if session_state.original_error_snapshot_id:
            original_error_snapshot = self.snapshot_store.get(session_state.original_error_snapshot_id)

        feedback_output = await self._retry_llm_call(
            self.feedback_tool.generate,
            snapshot=saved_snapshot,
            evaluation_result=evaluation_result,
            agent_goal=agent_goal,
            workdiff_result=workdiff_result,
            session_state=session_state,
            original_error_snapshot=original_error_snapshot,
        )


        hint = feedback_output.hint
        agent_goal.title = feedback_output.title
        agent_goal.message = feedback_output.message
        agent_goal.next_action = feedback_output.next_action
        agent_goal.focus_step_id = feedback_output.focus_step_id
        agent_goal.focus_line_index = feedback_output.focus_line_index


        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.DECISION,
                message="Agent goal selected",
                details={
                    "intent": agent_goal.intent.value,
                    "title": agent_goal.title,
                    "next_action": agent_goal.next_action,
                    "focus_step_id": agent_goal.focus_step_id,
                    "focus_line_index": agent_goal.focus_line_index,
                    "current_mode": session_state.mode.value,
                    "next_mode": next_mode.value,
                },
            )
        )


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

        highlights = self._build_highlights(
            snapshot=saved_snapshot,
            focus_step_id=feedback_output.focus_step_id,
            focus_line_index=feedback_output.focus_line_index,
            status=status,
        )

        # Track mode transitions for correction flow
        current_mode = session_state.mode
        was_in_correction_mode = current_mode == SessionMode.CORRECTION_ACTIVE
        entering_correction_mode = next_mode == SessionMode.CORRECTION_ACTIVE and not was_in_correction_mode
        exiting_correction_mode = current_mode == SessionMode.CORRECTION_ACTIVE and next_mode == SessionMode.NORMAL

        session_state.mode = next_mode
        session_state.updated_at = datetime.utcnow()

        if evaluation_result.verdict == EvaluationVerdict.NEEDS_REVISION:
            session_state.active_reason_code = evaluation_result.reason_code
            session_state.active_step_id = evaluation_result.target_step.step_id if evaluation_result.target_step else None
            session_state.active_line_index = evaluation_result.target_step.line_index if evaluation_result.target_step else None
            
            # Store original error snapshot when first entering correction mode
            if entering_correction_mode:
                session_state.original_error_snapshot_id = saved_snapshot.snapshot_id
                
        elif evaluation_result.verdict == EvaluationVerdict.CORRECT:
            session_state.active_reason_code = None
            session_state.active_step_id = None
            session_state.active_line_index = None
            
            # Clear original error snapshot when correction succeeds or mode resets
            if exiting_correction_mode or session_state.original_error_snapshot_id:
                session_state.original_error_snapshot_id = None

        
        self.session_state_store.save(session_state)

        practice_problem = None
        if status == CheckStatus.VALID:
            practice_problem = await self.practice_problem_generator_tool.generate(saved_snapshot)

        return self._finalize_and_build_response(
            trace=trace,
            status=status,
            confidence=confidence,
            hint=hint,
            highlights=highlights,
            agent_goal=agent_goal,
            new_snapshot_id=saved_snapshot.snapshot_id,
            started_at=started_at,
            practice_problem=practice_problem,
        )


    def _route_decision(
        self,
        *,
        evaluation_result: EvaluationResult,
        workdiff_result: DiffResult | None,
        previous_snapshot_exists: bool,
        current_mode: SessionMode,
    ) -> tuple[CheckStatus, float, str, AgentGoal, SessionMode]:
        verdict = evaluation_result.verdict
        conf = evaluation_result.confidence
        summary = evaluation_result.summary
        
        # Low confidence safety override
        if conf < 0.6:
            goal = self._goal(
                intent=TutorIntent.HANDLE_UNCERTAINTY,
                title="Uncertain Evaluation",
                message="I can't verify confidence in your solution.",
                next_action="CLARIFY_AND_CHECK",
                tools_planned=["solution_evaluator"],
                tools_used=["solution_evaluator"] + (["workdiff"] if workdiff_result else []),
            )
            hint = self._resolve_hint(
                summary=summary,
                fallback="I can't verify this confidently yet. Clarify the next step and check again.",
            )
            return CheckStatus.UNCERTAIN, conf, hint, goal, current_mode

        # Optional override if correction attempt became a rewrite
        if workdiff_result and workdiff_result.change_type == ChangeType.REWRITE:
            goal = self._goal(
                intent=TutorIntent.RESET_BASELINE,
                title="Reset Baseline",
                message="You rewrote the work significantly, so I’ll treat this as a fresh attempt.",
                next_action="CONTINUE_SOLVING",
                tools_planned=["solution_evaluator"],
                tools_used=["solution_evaluator", "workdiff"],
            )
            hint = self._resolve_hint(
                summary=workdiff_result.summary or summary,
                fallback="You rewrote much of the work, so I reset baseline for the next check.",
            )
            return CheckStatus.BASELINE_RESET, conf, hint, goal, SessionMode.NORMAL



        if verdict == EvaluationVerdict.CORRECT:
            goal = self._goal(
                intent=TutorIntent.CELEBRATE_AND_ADVANCE,
                title="Advance",
                message="Your work looks correct. Next step is to move to a new practice problem.",
                next_action="NEW_PRACTICE",
                tools_planned=[],
                tools_used=["solution_evaluator"] + (["workdiff"] if workdiff_result else []),
            )
            hint = self._resolve_hint(
                summary=summary,
                fallback="Nice work. Your current solution looks correct.",
            )
            return CheckStatus.VALID, conf, hint, goal, SessionMode.NORMAL
        


        if verdict == EvaluationVerdict.NEEDS_REVISION:
            in_revision_check = workdiff_result is not None
            goal = self._goal(
                intent=TutorIntent.VERIFY_REVISION if in_revision_check else TutorIntent.CORRECT_ACTIVE_ERROR,
                title="Revise This Step",
                message="There is an issue to fix. I’ll guide one revision at a time and re-check your update.",
                next_action="REVISE_AND_CHECK",
                tools_planned=["workdiff", "solution_evaluator"] if not in_revision_check else ["solution_evaluator"],
                tools_used=["solution_evaluator"] + (["workdiff"] if workdiff_result else []),
            )
            hint = self._resolve_hint(
                summary=summary,
                fallback="There is an issue in the current work. Revise this step and check again.",
            )
            return CheckStatus.INVALID, conf, hint, goal, SessionMode.CORRECTION_ACTIVE


        # UNCERTAIN
        if not previous_snapshot_exists:
            goal = self._goal(
                intent=TutorIntent.COLLECT_MORE_CONTEXT,
                title="Need One More Step",
                message="I need a bit more work shown before I can evaluate reliably.",
                next_action="ADD_STEP_AND_CHECK",
                tools_planned=["solution_evaluator"],
                tools_used=["solution_evaluator"],
            )
            hint = self._resolve_hint(
                summary=summary,
                fallback="Add one more clear step, then press Check again.",
            )
            return CheckStatus.NEED_MORE_CONTEXT, conf, hint, goal, current_mode
        

        goal = self._goal(
            intent=TutorIntent.HANDLE_UNCERTAINTY,
            title="Uncertain Evaluation",
            message="I can’t verify confidence in your solution.",
            next_action="CLARIFY_AND_CHECK",
            tools_planned=["solution_evaluator"],
            tools_used=["solution_evaluator"] + (["workdiff"] if workdiff_result else []),
        )

        hint = self._resolve_hint(
            summary=summary,
            fallback="I can’t verify this confidently yet. Clarify the next step and check again.",
        )
        return CheckStatus.UNCERTAIN, conf, hint, goal, current_mode
    


    def _trace_evaluator(self, trace: CheckTrace, evaluation_result: EvaluationResult) -> None:
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


    def _trace_workdiff(self, trace: CheckTrace, workdiff_result: DiffResult) -> None:
        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.TOOL_CALL,
                message="Workdiff computed successfully",
                details={
                    "tool": "workdiff",
                    "change_type": workdiff_result.change_type.value,
                    "confidence": workdiff_result.confidence,
                    "step_count_before": workdiff_result.step_count_before,
                    "step_count_after": workdiff_result.step_count_after,
                    "step_count_delta": workdiff_result.step_count_delta,
                    "matched_steps": workdiff_result.matched_steps,
                    "changed_steps": [s.model_dump() for s in workdiff_result.changed_steps],
                    "summary": workdiff_result.summary,
                },
            )
        )



    #building highlight helper
    def _build_highlights(
        self,
        snapshot: Snapshot,
        focus_step_id: str | None,
        focus_line_index: int | None,
        status: CheckStatus,
    ) -> List[Highlight]:
        matched_step = None
        if focus_step_id:
            matched_step = next(
                (step for step in snapshot.steps if step.step_id == focus_step_id),
                None,
            )

        if matched_step is None and focus_line_index is not None:
            matched_step = next(
                (step for step in snapshot.steps if step.line_index == focus_line_index),
                None,
            )
        
        if matched_step is None:
            logger.warning(
                "Highlight target not found: focus_step_id=%s focus_line_index=%s",
                focus_step_id, focus_line_index
            )
            return []
        
        
        if status == CheckStatus.INVALID:
            highlight_type = HighlightType.UNDERLINE
            label = "Revise this step"
        elif status == CheckStatus.UNCERTAIN:
            highlight_type = HighlightType.HIGHLIGHT
            label = "Check again"
        else:
            highlight_type = HighlightType.HIGHLIGHT
            label = "Focus here"
        
        return [
            Highlight(
                bbox=matched_step.bbox,
                type=highlight_type,
                label=label,
            )
        ]





        

    

    def _finalize_and_build_response(
        self,
        *,
        trace: CheckTrace,
        status: CheckStatus,
        confidence: float,
        hint: str,
        new_snapshot_id: str,
        started_at: datetime,
        agent_goal: AgentGoal | None,
        highlights: List[Highlight],
        practice_problem: PracticeProblemResult | None,
    ) -> CheckResponse:

        completed_at = datetime.utcnow()
        latency_ms = int((completed_at - started_at).total_seconds() * 1000)


        trace.final_status = status
        trace.final_confidence = confidence
        trace.completed_at = completed_at
        trace.total_latency_ms = latency_ms


        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.FINAL,
                message="Check Completed",
                details={
                    "status": status.value,
                    "confidence": confidence,
                    "new_snapshot_id": new_snapshot_id,
                },
            )
        )

        saved_trace = self.trace_store.save(trace)
        logger.info(
            "orchestrator_final trace_id=%s status=%s confidence=%.2f snapshot_before=%s snapshot_after=%s latency_ms=%d events=%d",
            saved_trace.trace_id,
            status.value,
            confidence,
            trace.snapshot_id_before,
            trace.snapshot_id_after,
            latency_ms,
            len(trace.events),
        )

        return CheckResponse(
            status=status,
            confidence=confidence,
            highlights=highlights,
            hint=hint,
            correction=None,
            new_snapshot_id=new_snapshot_id,
            trace_id=saved_trace.trace_id,
            debug_trace_summary=None,
            agent_goal=agent_goal,
            practice_problem=practice_problem,
        )


    def _goal(
        self, 
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
            tools_used=tools_used or []
        )

    def _resolve_hint(self, summary: str | None, fallback: str) -> str:
        normalized = (summary or "").strip()
        return normalized or fallback
