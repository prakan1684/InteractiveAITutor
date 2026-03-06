# app_v2 Handoff Summary (For Next Codex Thread)

This document is a detailed handoff for continuing `app_v2` development in a new Codex thread.

## Project Goal (Current Direction)

Build a portfolio-grade, agentic backend for an iOS canvas-based tutor app.

Current V1 strategy:
- Contract-first backend
- iOS payload adapter -> canonical backend request
- Stateful snapshot tracking across checks
- Orchestrator-driven decisions
- LLM-backed `workdiff` tool to classify changes between snapshots

Near-term product loop (agreed direction):
1. Student writes work and presses Check
2. Orchestrator evaluates state/context
3. If needs revision -> feedback path
4. If correct -> practice problem generation path
5. `workdiff` is a decision-support tool (not the full loop)

## Current Milestone Status

### Completed
- `app_v2` skeleton created
- Canonical contracts implemented (`check`, `snapshot`, `trace`, enums)
- iOS transport contract implemented (`IOSAnalyzePayload`)
- iOS -> canonical adapter implemented
- `/check` and `/check/ios` endpoints implemented
- iOS payload ingestion tested successfully from iPad (real payloads)
- Optional canvas image debug artifact dump implemented (base64 decode -> file)
- `SnapshotStore` (in-memory) implemented and wired
- `TraceStore` (in-memory) implemented and wired
- `CheckOrchestrator` minimal flow implemented and wired
- Follow-up path recognizes previous snapshot (`lastSnapshotId`)
- LLM-backed `WorkDiffTool` implemented and integrated
- Orchestrator now routes follow-up status based on `workdiff.change_type`
- Logging format improved for `app_v2` (no timestamp, extra spacing)

### In Progress / Next
- `workdiff` is integrated and returns decisions, but no diff context bank yet
- No evaluator (correct/incorrect/uncertain) tool yet
- No feedback generator (revision hints) or practice problem generator yet
- No math engine integration yet (Phase 2+)

## Key Architecture (Current)

### Layers
- `app_v2/contracts/` -> request/response + internal typed contracts
- `app_v2/stores/` -> in-memory stores (`SnapshotStore`, `TraceStore`)
- `app_v2/orchestrator/` -> `CheckOrchestrator` owns check flow
- `app_v2/tools/` -> `WorkDiffTool` (LLM-based)
- `app_v2/routers/` -> FastAPI endpoints, transport + adaptation only

### Current `check` Flow
1. iOS sends `/check/ios` payload (transport shape)
2. Router logs payload summary + saves debug image artifact (optional)
3. Adapter converts iOS payload -> canonical `CheckRequest`
4. Router calls `CheckOrchestrator.run_check(...)`
5. Orchestrator:
   - saves snapshot
   - creates trace
   - baseline path if no previous snapshot id
   - follow-up path loads previous snapshot
   - calls `WorkDiffTool` on previous/current snapshots
   - maps `change_type` to `CheckStatus`
   - saves trace and returns `CheckResponse`

## Important Contracts / Models

### Canonical backend request/response
- `app_v2/contracts/check_api.py`
  - `CheckRequest`
  - `CheckResponse`

Current canonical request field is `snapshot` (not `current_snapshot`).

### Canonical snapshot
- `app_v2/contracts/snapshot.py`
  - `Snapshot`
  - `StepSnapshot`
  - `BBox`
  - `ClientMeta`

Internal `BBox` is normalized (`x`, `y`, `width`, `height` in `[0,1]`).
Adapter normalizes from iOS MyScript editor coordinates.

### Trace contract
- `app_v2/contracts/trace.py`
  - `CheckTrace`, `TraceEvent`, `ToolCallTrace`

### iOS transport payload
- `app_v2/contracts/ios_payload.py`
  - `IOSAnalyzePayload` and nested models

Current important transport additions:
- `snapshotId` (client-generated current snapshot id)
- `lastSnapshotId` (client-provided previous snapshot id)
- optional `canvasImage`

### Diff contracts
- `app_v2/contracts/diff_feedback.py`
  - `DiffResult`
  - `ChangedStepRef`
  - `DiffContextEntry` (placeholder for upcoming context bank)
  - `FeedbackResult` (placeholder for upcoming feedback generator)

## Current Stores

### `SnapshotStore` (implemented)
- `app_v2/stores/snapshot_store.py`
- Supports:
  - `save(snapshot)`
  - `get(snapshot_id)`
  - `get_latest_for_session(session_id)`
  - `list_ids_for_session(session_id)`
- Uses deep copies for mutation safety

Note:
- If `snapshot.snapshot_id` is provided by iOS, store preserves it.
- Store still has fallback snapshot ID generation if missing (good defensive behavior).

### `TraceStore` (implemented)
- `app_v2/stores/trace_store.py`
- Supports:
  - `save(trace)`
  - `get(trace_id)`
  - `list_ids_for_session(session_id)`
- Uses deep copies for mutation safety

## Current `workdiff` Tool (LLM-backed)

### File
- `app_v2/tools/workdiff.py`

### Behavior
- Builds compact structured snapshot summaries from canonical snapshots
- Sends summaries + geometry semantics prompt to LLM
- Requires JSON output
- Parses/sanitizes LLM output via `_to_diff_result(...)`
- Returns `DiffResult`
- Falls back to `ChangeType.UNKNOWN` on failure

### Why `_to_diff_result(...)` exists
It converts raw/untrusted LLM JSON into a trusted typed `DiffResult`:
- enum normalization (`change_type`)
- confidence clamping
- `changed_steps` validation
- merges trusted snapshot facts with LLM decisions

## Orchestrator Status Mapping (Current)

In follow-up path (`previous_snapshot` exists), orchestrator maps `workdiff.change_type`:
- `EDIT_IN_PLACE` -> `STALE_DUE_TO_EDIT`
- `REWRITE` -> `BASELINE_RESET`
- `APPEND` -> `UNCERTAIN` (until verifier exists)
- `UNKNOWN` -> `UNCERTAIN`

Hints currently use `workdiff_result.summary` when present, else fallback templates.

## Logging / Debugging (Current)

### Logging format
- `app/core/logging_config.py` updated:
  - supports `include_time` and `leading_newline`

### `app_v2` startup config
- `app_v2/main.py` calls:
  - `setup_logging(level="INFO", include_time=False, leading_newline=True)`

### Current logs include
- iOS payload summary
- per-step logs (first few)
- image debug artifact save path + size
- adapter success
- orchestrator lifecycle logs
- `workdiff_start`
- `workdiff_result`
- final routed status

### Known logging limitation
- logs show `[req:-]` because `app_v2` does **not** yet have request-id middleware (old app had it).

## iOS Integration Status

### Confirmed working
- iPad can call `/check/ios` successfully
- iOS sends `snapshotId` and `lastSnapshotId`
- Backend recognizes follow-up requests (`has_last_snapshot_id=True`)
- Previous snapshot loads successfully
- `workdiff` runs and returns structured results
- Orchestrator routes based on diff result

### Confirmed example behavior
Example correction/edit scenario:
- First request -> `NEED_MORE_CONTEXT` (baseline)
- Second request with `lastSnapshotId` -> `EDIT_IN_PLACE` from `workdiff`
- Orchestrator routes -> `STALE_DUE_TO_EDIT`

## Important Product/Architecture Decisions Made

1. `workdiff` is a **decision-support tool**, not the entire tutoring loop.
2. `SnapshotStore`/`TraceStore` come before advanced agent behaviors.
3. iOS owns:
   - `sessionId`
   - `snapshotId`
   - `lastSnapshotId`
4. Backend owns:
   - `trace_id`
5. LLM-backed `workdiff` is acceptable for V1 speed, using structured snapshot summaries (not raw image diffing).
6. Future correctness verification should be hybrid:
   - LLM + math engine tool (Phase 2+), but Phase 1 can be LLM-only evaluator.

## TODO / Next Steps (Prioritized)

### Highest Priority (Next Session)
1. Build an LLM-only `SolutionEvaluator` (Phase 1)
   - Goal: classify current work as `CORRECT`, `NEEDS_REVISION`, `UNCERTAIN`
   - Use structured steps (no image required initially)
   - Add `EvaluationResult` contract first

2. Integrate evaluator into `CheckOrchestrator`
   - For follow-up path after `workdiff`
   - Optionally for baseline path too (product decision)
   - Route:
     - `NEEDS_REVISION` -> feedback path
     - `CORRECT` -> practice generation path
     - `UNCERTAIN` -> conservative feedback

3. Add minimal feedback generator (template-based first)
   - Use evaluation result + `workdiff` summary
   - Return short student-facing hints

4. Add minimal practice problem generator (template or LLM)
   - Trigger only on `CORRECT`

### Important but Not Blocking
5. Implement `DiffContextBank` (in-memory)
   - Store recent `DiffResult`s by session
   - Enables future rolling-window context
   - Can log `recent_diff_count` initially

6. Add request-id middleware to `app_v2/main.py`
   - Reuse pattern from old app for `[req:...]` logging context

7. Add duplicate snapshot ID safety in `SnapshotStore`
   - If client reuses `snapshotId`, log or validate idempotency
   - Prevent accidental overwrite of different snapshot content under same ID

8. Move `ios_to_check.py` out of `contracts/`
   - Current location: `app_v2/contracts/ios_to_check.py`
   - Better location: `app_v2/adapters/ios_to_check.py`
   - Low priority for now

## Suggested Next Contracts to Create

### `EvaluationResult` (new)
Likely fields:
- `verdict`: `CORRECT | NEEDS_REVISION | UNCERTAIN`
- `confidence`
- `reason_code`
- `summary`
- `target_step` (optional)
- `math_engine_used` (bool, for future hybrid path)

### `PracticeProblemResult` (new)
Likely fields:
- `problem_text`
- `difficulty`
- `topic`
- `hints` (optional)

## Suggested Next Tool Interfaces (Phase 1)

### `SolutionEvaluatorTool` (LLM-only first)
- Input: canonical snapshot + optional context (`workdiff`, recent diffs)
- Output: `EvaluationResult`

### `FeedbackGenerator` (template first)
- Input: `EvaluationResult` + `DiffResult`
- Output: `FeedbackResult` (or directly map to `CheckResponse` hint/status)

### `PracticeProblemGeneratorTool`
- Input: current topic/observed skill level (minimal first)
- Output: new practice prompt/problem

## Known Technical Notes / Gotchas

1. `workdiff` uses LLM; latency currently around ~2-3s on follow-up checks.
   - Consider switching model to `gpt-4o-mini` later if needed.

2. `workdiff` LLM output can be imperfect (e.g., `matched_steps` not always intuitive).
   - This is acceptable for V1, but keep trace logs and sanity-checks.

3. Router logs are readable now, but long summaries can still be noisy.
   - Structured event logging helper could be added later.

4. `CheckRequest` still uses `snapshot` field (canonical backend contract).
   - Do not rename casually without coordinated updates.

## Quick Start Checklist for Next Thread

1. Read these files first:
   - `app_v2/orchestrator/check_orchestrator.py`
   - `app_v2/tools/workdiff.py`
   - `app_v2/contracts/check_api.py`
   - `app_v2/contracts/diff_feedback.py`
   - `app_v2/contracts/ios_payload.py`
   - `app_v2/contracts/ios_to_check.py`

2. Confirm current flow still works:
   - `/check/ios` baseline request
   - `/check/ios` follow-up request with `lastSnapshotId`
   - verify `workdiff_result` logs and routed status

3. Implement `EvaluationResult` contract and `SolutionEvaluatorTool` (LLM-only Phase 1)

4. Wire evaluator into orchestrator after `workdiff`

5. Add feedback/practice routing outputs

## Validation Scenarios to Keep Running

1. Baseline first check (`lastSnapshotId = null`)
   - Expect `NEED_MORE_CONTEXT`

2. Correction edit-in-place
   - Expect `workdiff=EDIT_IN_PLACE`
   - Expect `STALE_DUE_TO_EDIT`

3. Full rewrite/new problem
   - Expect `workdiff=REWRITE` (or `UNKNOWN` initially)
   - Expect `BASELINE_RESET` (or conservative fallback)

4. Append-only new step
   - Expect `workdiff=APPEND`
   - Expect `UNCERTAIN` until verifier exists

