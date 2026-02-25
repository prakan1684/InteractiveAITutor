

from app_v2.stores.snapshot_store import SnapshotStore
from app_v2.stores.trace_store import TraceStore
from app_v2.contracts.trace import CheckTrace, TraceEvent
from app_v2.contracts.check_api import CheckRequest, CheckResponse
from app_v2.domain.enums import TraceEventType, CheckStatus, ChangeType
from app.core.logger import get_logger
from app_v2.tools.workdiff import WorkDiffTool

from datetime import datetime
from uuid import uuid4

logger = get_logger(__name__)



class CheckOrchestrator:
    """
    Responsibilities:
    1. persist snapshots
    2. early agentic branching decisions
    3. persist traces
    """
    def __init__(self, snapshot_store: SnapshotStore, trace_store: TraceStore):
        self.snapshot_store = snapshot_store
        self.trace_store = trace_store
        self.workdiff_tool = WorkDiffTool()

    
    async def run_check(self, request: CheckRequest) -> CheckResponse:
        started_at = datetime.utcnow()
        trace = CheckTrace(
            trace_id = f"trace_{uuid4().hex}",
            session_id = request.session_id,
            started_at = started_at,
            tool_calls = [],
            events = []
        )
        logger.info(
            "orchestrator_start trace_id=%s session_id=%s has_last_snapshot_id=%s step_count=%d",
            trace.trace_id,
            request.session_id,
            request.last_snapshot_id is not None,
            len(request.snapshot.steps),
        )

        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.DECISION,
                message="Received Check Request",
                details={
                    "has_last_snapshot_id": request.last_snapshot_id is not None,
                    "step_count": len(request.snapshot.steps)
                },

            )
        )

        saved_snapshot = self.snapshot_store.save(request.snapshot)
        trace.snapshot_id_after = saved_snapshot.snapshot_id
        logger.info(
            "snapshot_saved trace_id=%s snapshot_id_after=%s session_id=%s",
            trace.trace_id,
            saved_snapshot.snapshot_id,
            saved_snapshot.session_id,
        )

        if not request.last_snapshot_id: 
            logger.info("orchestrator_branch trace_id=%s branch=baseline_no_previous", trace.trace_id)
            trace.events.append(
                TraceEvent(
                    event_type=TraceEventType.DECISION,
                    message="No previous snapshot found, starting new session"
                )
            )

            return self._finalize_and_build_response(
                trace=trace,
                status=CheckStatus.NEED_MORE_CONTEXT,
                confidence=1.0,
                hint="Baseline saved. Add one more step, then press check again",
                new_snapshot_id=saved_snapshot.snapshot_id,
                started_at=started_at
            )
        
        previous_snapshot = self.snapshot_store.get(request.last_snapshot_id)
        if previous_snapshot is None:
            logger.info(
                "orchestrator_branch trace_id=%s branch=previous_missing requested_last_snapshot_id=%s",
                trace.trace_id,
                request.last_snapshot_id,
            )
            trace.events.append(
                TraceEvent(
                    event_type=TraceEventType.STORE_READ,
                    message="Previous snapshot id not found",
                    details={"last_snapshot_id": request.last_snapshot_id},
                )
            )
            return self._finalize_and_build_response(
                trace=trace,
                status=CheckStatus.NEED_MORE_CONTEXT,
                confidence=0.9,
                hint="I couldn't find the previous snapshot. Baseline saved; add one more step and press Check again.",
                new_snapshot_id=saved_snapshot.snapshot_id,
                started_at=started_at,
            )



        trace.snapshot_id_before = previous_snapshot.snapshot_id
        logger.info(
            "previous_snapshot_loaded trace_id=%s snapshot_id_before=%s",
            trace.trace_id,
            previous_snapshot.snapshot_id,
        )
        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.STORE_READ,
                message="Loaded previous snapshot successfully",
                details={
                    "previous_snapshot_id": previous_snapshot.snapshot_id,
                    "previous_step_count": len(previous_snapshot.steps),
                    "current_step_count": len(saved_snapshot.steps),
                },
            )
        )

        

        #implement workdiff tool to analyze snapshot and previous snapshot
        logger.info(
            "workdiff_start trace_id=%s snapshot_before=%s snapshot_after=%s",
            trace.trace_id,
            previous_snapshot.snapshot_id,
            saved_snapshot.snapshot_id,
        )
        workdiff_result = await self.workdiff_tool.compute_diff(previous_snapshot, saved_snapshot)
        logger.info(
            "workdiff_result trace_id=%s change_type=%s confidence=%.2f matched_steps=%d step_delta=%d changed_steps=%d summary=%s",
            trace.trace_id,
            workdiff_result.change_type.value,
            workdiff_result.confidence,
            workdiff_result.matched_steps,
            workdiff_result.step_count_delta,
            len(workdiff_result.changed_steps),
            workdiff_result.summary,
        )


        trace.events.append(
            TraceEvent(
                event_type=TraceEventType.TOOL_CALL,
                message="Workdiff computed successfully",
                details={
                    "change_type": workdiff_result.change_type.value,
                    "confidence": workdiff_result.confidence,
                    "step_count_before": workdiff_result.step_count_before,
                    "step_count_after": workdiff_result.step_count_after,
                    "step_count_delta": workdiff_result.step_count_delta,
                    "matched_steps": workdiff_result.matched_steps,
                    "changed_steps": [step.model_dump() for step in workdiff_result.changed_steps],
                    "summary": workdiff_result.summary,
                },
            )
        )
        status, hint = self._map_workdiff_to_response(workdiff_result)
        logger.info(
            "orchestrator_branch trace_id=%s branch=follow_up_diff_routed change_type=%s routed_status=%s",
            trace.trace_id,
            workdiff_result.change_type.value,
            status.value,
        )

        return self._finalize_and_build_response(
            trace=trace,
            status=status,
            confidence=workdiff_result.confidence,
            hint=hint,
            new_snapshot_id=saved_snapshot.snapshot_id,
            started_at=started_at,
        )


    def _finalize_and_build_response(
        self,
        *,
        trace: CheckTrace,
        status: CheckStatus,
        confidence: float,
        hint: str,
        new_snapshot_id: str,
        started_at: datetime,
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
            highlights=[],
            hint=hint,
            correction=None,
            new_snapshot_id=new_snapshot_id,
            trace_id=saved_trace.trace_id,
            debug_trace_summary=None,
        )

    def _map_workdiff_to_response(self, workdiff_result) -> tuple[CheckStatus, str]:
        """
        Map workdiff change classification into a user-facing check status + hint.

        This is intentionally simple for V1 and can be replaced by a richer
        feedback generator later.
        """
        change_type = workdiff_result.change_type
        summary = (workdiff_result.summary or "").strip()

        if change_type == ChangeType.EDIT_IN_PLACE:
            return (
                CheckStatus.STALE_DUE_TO_EDIT,
                summary or "You changed an earlier step. Later work may be stale, so re-check from here.",
            )

        if change_type == ChangeType.REWRITE:
            return (
                CheckStatus.BASELINE_RESET,
                summary or "This looks like a major rewrite. I reset the baseline for the next check.",
            )

        if change_type == ChangeType.APPEND:
            return (
                CheckStatus.UNCERTAIN,
                summary or "You added a new step. I can compare it next once verifier logic is enabled.",
            )

        return (
            CheckStatus.UNCERTAIN,
            summary or "I couldn't confidently classify the change. Try checking again after one more clear step.",
        )
        
