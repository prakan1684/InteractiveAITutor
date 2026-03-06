# Build Playbook: How to Actually Build the Agentic Tutor

This is the hands-on guide for building the system without getting lost.

## Core Rule
Work in vertical slices.  
Each slice must be:
1. Demoable.
2. Testable.
3. Measurable (latency, correctness, cost).

## Component-by-Component Build Order

## 1) Canonical State Contract
Why:
- Prevents silent breakage between agents/tools.

How:
1. Define a single state schema for runtime (`TutorState`) and trace (`TraceState`).
2. Add schema validation at orchestrator entry and before each node/tool call.
3. Add a contract test fixture with sample payloads.

Done when:
1. No duplicate/alias fields.
2. All agent nodes pass typed state tests.

## 2) Orchestrator (The Brain)
Why:
- Agentic behavior comes from planning/routing, not random prompting.

How:
1. Keep planner outputs constrained: intent + ordered steps + fallback.
2. Use deterministic routing policy around planner output.
3. Add retry budget per tool category.
4. Log every routing decision in trace.

Done when:
1. Same input produces stable plan class under low temperature.
2. Failures route to safe fallback response, not hard crash.

## 3) Tools Layer
Why:
- Tools are the real capabilities; agents are coordinators.

How:
1. Define tool contracts first (input/output/error).
2. Wrap each tool with timing, token/cost, and error logging.
3. Build tools to be independently runnable in tests.
4. Start with minimum useful tools:
- `perception.analyze_canvas`
- `memory.get_recent`
- `memory.store_session`
- `feedback.generate`

Done when:
1. Each tool has contract tests and failure-case tests.
2. Orchestrator can call tools with no direct service coupling.

## 4) MCP Boundary
Why:
- Gives portfolio-grade modularity and future interoperability.

How:
1. Implement perception MCP server with strict schema checks.
2. Normalize errors (`code`, `message`, `details`, `retryable`).
3. Keep MCP tool outputs stable even if internal model prompts change.

Done when:
1. At least one production path depends on MCP tool call.
2. Contract tests protect against schema drift.

## 5) Memory and Retrieval
Why:
- Multi-turn quality depends on memory more than prompt wording.

How:
1. Separate short-term convo memory from long-term learning memory.
2. Store session summaries + outcomes + misconceptions.
3. Retrieve by both recency and semantic relevance.
4. Pass only top relevant memory into prompts to control cost.

Done when:
1. "Did I fix it this time?" responses correctly reference prior turn/session.

## 6) Feedback Generation
Why:
- This is user-facing quality and trust.

How:
1. Enforce output schema: correctness, explanation, hint, next step options.
2. Validate mathematical claims with explicit check phase where feasible.
3. Calibrate tone with policy prompts and regression examples.

Done when:
1. Feedback is specific to detected work, not generic tutoring text.

## 7) Observability and Reliability
Why:
- You cannot polish what you cannot see.

How:
1. Add per-run IDs and trace persistence.
2. Track metrics:
- first-token latency
- total latency
- tool failure rate
- token/cost per turn
3. Build a simple "trace viewer" endpoint/UI for debugging/demo.

Done when:
1. Any bad response can be debugged from trace in under 5 minutes.

## 8) Productization
Why:
- Portfolio projects stand out when they feel shippable.

How:
1. Durable storage for artifacts and analysis outputs.
2. Auth + rate limit + abuse guardrails.
3. Circuit breaker for expensive tool/model chains.
4. Safe fallback response when dependencies fail.

Done when:
1. System handles expected concurrency and recovers gracefully.

## Development Rhythm (Use Weekly)
1. Monday: choose one vertical slice and define exit criteria.
2. Tue-Thu: implement only what that slice needs.
3. Friday: run regression + capture metrics + record demo.
4. Weekend: update docs and reduce tech debt created that week.

## What To Learn As You Build (Skill Ladder)
1. Week 1-2: contracts, typed state, orchestrator basics.
2. Week 3-4: tool reliability, retries, idempotency.
3. Week 5-6: memory retrieval quality and evaluation sets.
4. Week 7-8: performance tuning and cost controls.
5. Week 9-10: deployment, monitoring, and operational maturity.

## Portfolio Evidence Checklist
1. Architecture diagram with data/tool boundaries.
2. Trace screenshot showing plan and tool sequence.
3. Before/after metric table (latency, success, cost).
4. One failure postmortem and what you changed.
5. Short video: user prompt -> tool calls -> improved feedback.

## If You Feel Dizzy Mid-Build
Use this triage:
1. What is the single user outcome for this week?
2. Which component blocks that outcome right now?
3. What is the smallest test that proves progress?
4. What can be deleted or deferred today?

If you cannot answer all four, stop coding and rewrite the weekly slice scope.
