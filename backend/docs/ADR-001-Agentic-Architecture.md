# ADR-001: Agentic Architecture Spine for Interactive AI Tutor

- Status: Accepted
- Date: 2026-02-19
- Owners: Backend / Agentic Platform

## Context
The codebase currently has two competing orchestration paths:
- A production-like chat flow (`app/agents/chat/workflow.py`) used by API routes.
- A newer agentic flow (`app/agents/nodes.py`) with Orchestrator, Memory, Vision, Feedback agents.

This split creates duplicated logic, mismatched state contracts, and unclear product direction.
The product goal requires both:
- Portfolio-quality agentic architecture (clear planning, tool use, traces).
- Real product quality (low latency, reliability, observability, maintainability).

## Decision
Adopt a single architecture spine:

1. One orchestrator is the decision-maker.
- `LangGraph` orchestrator owns intent, planning, routing, and retries.
- API layer does not implement business logic beyond request/response handling.

2. Capabilities are tools with strict contracts.
- Vision/perception, memory, course retrieval, and feedback capability surface as tools.
- Tool inputs/outputs are typed, versioned, and testable.

3. MCP is the external tool boundary.
- Perception tools will be exposed via MCP server for architecture clarity and portability.
- Internal agents call tools through stable interfaces (MCP-compatible contract design).

4. Canonical state schema is mandatory.
- One `TutorState` and one `TraceState` contract.
- Eliminate conflicting field names (e.g., `img_path` vs `full_canvas_path`).

5. Observability is a first-class feature.
- Every run captures: plan, tool calls, latencies, token usage, errors, final outcome.
- Trace data must be queryable for debugging and demo.

## Non-Goals
- Full multi-provider model abstraction in v1.
- Premature microservice split.
- Perfect autonomy before reliability baselines.

## Consequences
Positive:
- Strong portfolio narrative: orchestrator + tools + MCP + trace.
- Faster product iteration from one path.
- Lower bug surface from contract alignment.

Tradeoffs:
- Refactor cost now (merging/deprecating old paths).
- Short-term reduced feature velocity while contracts are stabilized.

## Architecture Shape
1. API Layer
- Endpoints: `/steps`, `/chat`, `/chat/stream`, health/admin.
- SSE streams orchestrator status and final response.

2. Orchestration Layer
- Nodes: `orchestrator -> memory/vision/feedback -> orchestrator`.
- Routing from explicit `next_action`.
- Retry policy and fallback paths defined per tool type.

3. Tool Layer
- `perception` tools (detect regions, parse expressions, step reasoning).
- `memory` tools (retrieve recent, retrieve relevant, store session).
- `rag` tools (course/material retrieval).

4. Data Layer
- Conversation history store.
- Session artifact store (canvas images, step crops, analysis outputs).
- Trace store (run metadata + tool events).

## Acceptance Criteria
Architecture is considered adopted when:
1. `/chat` and `/chat/stream` both invoke the same orchestrator flow.
2. MCP perception server is implemented and used by at least one orchestrator tool path.
3. A single canonical state schema is enforced in code.
4. Run traces include plan + tool calls + timings + token usage.
5. Legacy workflow paths are marked deprecated with removal date.

## Migration Plan
1. Freeze state contract and tool contracts.
2. Route chat APIs into orchestrator for one vertical slice (`check my work`).
3. Implement MCP perception server minimal set.
4. Add trace persistence and a debug endpoint/UI.
5. Remove duplicated old flow once parity is reached.

## Open Questions
1. Where should traces persist first: Azure Search index vs lightweight SQL table?
2. Which tasks should be async/background vs synchronous for v1 latency targets?
3. Should model policy be static by task or adaptive by confidence/complexity?
