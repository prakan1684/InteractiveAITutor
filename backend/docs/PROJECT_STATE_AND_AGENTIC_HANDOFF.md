# Elara Backend: Current State + Agentic Handoff (for Claude)

## Purpose
This is the single source-of-truth handoff for the backend project.

Audience:
- Next coding assistant/thread (Claude or similar)
- Future collaborators
- Project owner learning agentic architecture hands-on

## Project Goal
Build a portfolio-grade, publishable iPad tutoring backend that:
- accepts handwritten canvas math work
- evaluates correctness
- gives personalized feedback + visual focus hints
- generates follow-up practice problems
- evolves into a robust agentic workflow with clear state and traceability

## Important Collaboration Requirement (Learning-First)
The owner is actively learning agentic architecture and wants teaching-oriented collaboration while building.

Expected assistant behavior:
1. Explain architectural decisions in plain language.
2. Make incremental changes with clear rationale.
3. Keep strong engineering quality, but avoid over-abstracting too early.
4. Prefer showing how/why over black-box implementation.
5. Surface tradeoffs explicitly (speed vs correctness, flexibility vs complexity, etc.).

## Current Runtime Paths

### 1) Primary app_v2 path (custom orchestrator)
Files:
- `app_v2/orchestrator/check_orchestrator.py`
- `app_v2/routers/check.py` endpoints: `/check`, `/check/ios`

Responsibilities:
- snapshot persistence
- session mode handling
- evaluator + optional workdiff
- agent goal routing
- feedback generation
- optional practice problem generation on valid outcomes
- trace persistence

### 2) Experimental graph path (LangGraph learning track)
Files:
- `app_v2/graph/state.py`
- `app_v2/graph/nodes.py`
- `app_v2/graph/workflow.py`
- `app_v2/routers/check.py` endpoint: `/check/ios/graph`

Status:
- first linear graph workflow is in place for learning
- used for side-by-side testing without replacing primary path yet

## Current API Surface (app_v2)
- `POST /check`
- `POST /check/ios`
- `POST /check/ios/graph` (experimental LangGraph path)
- `GET /trace/{trace_id}` (trace inspection)

## Core Contracts (Current)
Primary files:
- `app_v2/contracts/check_api.py`
- `app_v2/contracts/snapshot.py`
- `app_v2/contracts/trace.py`
- `app_v2/contracts/diff_feedback.py`
- `app_v2/contracts/agent_goal.py`
- `app_v2/contracts/feedback.py`
- `app_v2/contracts/practice_problem.py`
- `app_v2/contracts/session_state.py`

Notable response fields now:
- `status`
- `confidence`
- `hint`
- `agent_goal`
- `highlights`
- `practice_problem` (optional path; keep parity checks in mind)
- `trace_id`

## What Is Working
1. iOS payload ingestion and adapter flow (`/check/ios`) works.
2. Snapshot + trace persistence works (in-memory stores).
3. Evaluator + feedback generation path works end-to-end.
4. Agent goal is returned for UI guidance.
5. Basic highlight targeting exists (focus step/line driven).
6. Trace inspection endpoint exists (`GET /trace/{trace_id}`).
7. LangGraph prototype endpoint (`/check/ios/graph`) exists for experimentation.

## Known Gaps / Risks
1. LLM-only evaluator can confidently misclassify concise-but-correct work.
2. Graph and primary path are not yet feature-parity.
3. In-memory stores are not durable (dev-only reliability).
4. Potential trace store split between custom path and graph path if not unified.
5. Feedback quality is improving but still needs stronger revision-aware personalization.

## Near-Term Product Priorities
1. Improve personalized feedback quality (especially revision-aware coaching).
2. Stabilize practice problem generation and ensure it is returned/displayed consistently.
3. Improve highlighting/annotation precision and UX alignment with iPad client.
4. Keep trace data inspectable and useful for debugging + demos.

## Agentic Architecture Direction
Short-term:
- keep custom orchestrator shipping
- keep LangGraph as an experimental migration track

Medium-term:
- move orchestration complexity into LangGraph nodes/edges
- preserve existing contracts/stores/tool boundaries
- avoid framework leakage into API contracts

Long-term:
- mode-based product flows (e.g., Practice Mode)
- richer stateful coaching loops
- robust observability and reliability gates

## Suggested Next Milestones

### Milestone A: Feedback quality upgrade
- improve feedback generator prompts + sanitizer behavior
- add explicit progress-aware and correction-aware response templates/fallbacks
- increase use of target step/line in output

### Milestone B: Practice mode readiness
- make practice generation deterministic enough for UX consistency
- store and use last valid solve context as seed
- standardize `practice_problem` response behavior

### Milestone C: LangGraph slice parity
- ensure graph path mirrors primary path for: evaluate -> route -> feedback -> finalize
- then add conditional branches for practice generation and correction/diff

### Milestone D: Trace + debug quality
- unify trace stores across runtime paths
- add summary endpoint(s) if needed
- keep request-level logs concise while trace remains detailed

## Expectations for Claude Handoff
When continuing this project:
1. Read current code paths before proposing architecture changes.
2. Prioritize small, testable slices.
3. Keep both runtime paths understandable while migration is in progress.
4. Explain each architectural move in teaching mode.
5. Document changes and tradeoffs as part of implementation.

## Practical Definition of “Good Progress”
A change is considered successful if it is:
1. demoable from iPad with realistic payloads,
2. observable via trace and clear logs,
3. consistent with existing contracts, and
4. understandable by the project owner from a learning standpoint.

