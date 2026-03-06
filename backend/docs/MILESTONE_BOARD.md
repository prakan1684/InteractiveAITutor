# Milestone Board: Agentic Tutor to Polished Product

- Start Date: 2026-02-19
- Horizon: 10 weeks
- Cadence: weekly milestones, daily execution tickets

## Success Metrics (Global)
1. Median `/chat/stream` first token latency < 2.5s.
2. Canvas-review success rate > 90% on test set.
3. Trace completeness = 100% for production runs.
4. Crash-free API sessions > 99%.
5. Cost per tutoring turn stays within target budget.

## M0: Architecture Freeze (Week 1)
Goal: End ambiguity; define one spine.

Deliverables:
1. ADR approved (`docs/ADR-001-Agentic-Architecture.md`).
2. Canonical state contract doc with field definitions and owners.
3. Tool contract doc (perception/memory/rag/feedback).
4. Deprecation list of old paths and target removal dates.

Exit Criteria:
1. No new features added to deprecated path.
2. All new work references canonical contracts.

## M1: Vertical Slice #1 - "Check My Work" (Weeks 2-3)
Goal: Complete end-to-end value path through orchestrator.

Scope:
1. iOS uploads `/steps` canvas data.
2. Chat asks: "check my work".
3. Orchestrator plans and calls memory + perception + feedback.
4. SSE returns status events + final feedback.
5. Trace captures full run.

Exit Criteria:
1. E2E test passes for at least 20 representative samples.
2. One-click demo script available for portfolio walkthrough.

## M2: MCP Perception Server Productionized (Weeks 4-5)
Goal: Make tool boundary explicit and reliable.

Scope:
1. Implement `app/mcp_servers/perception/server.py`.
2. Register minimal tools: region detect, classify, extract, step inference.
3. Strict schema validation and normalized error envelope.
4. Integration tests for all tool endpoints.

Exit Criteria:
1. At least one orchestrator path uses MCP implementation directly.
2. Tool reliability >= 99% in local/staging test runs.

## M3: Vertical Slice #2 - Multi-turn Improvement Loop (Weeks 6-7)
Goal: Demonstrate real agentic memory behavior.

Scope:
1. Handle follow-up turns: "did I fix it this time?"
2. Retrieve prior context and compare with latest canvas analysis.
3. Generate progress-aware feedback and next actions.

Exit Criteria:
1. Test set shows improvement-aware responses in >= 85% cases.
2. Regression tests confirm no loss in single-turn performance.

## M4: Product Hardening (Weeks 8-9)
Goal: Ready for controlled real users.

Scope:
1. Replace in-memory caches with durable storage for critical paths.
2. Add auth/rate limiting and request validation hardening.
3. Add cost guards (token limits, retries, model fallback policy).
4. Add telemetry dashboard for latency, errors, cost.

Exit Criteria:
1. Load test meets target for expected concurrent sessions.
2. On-call runbook and rollback process documented.

## M5: Launch and Portfolio Pack (Week 10)
Goal: Ship with proof of engineering quality.

Deliverables:
1. Public architecture diagram and short technical write-up.
2. Demo recording with trace walk-through.
3. "Design tradeoffs" section (why this architecture, what changed, lessons).
4. Metrics snapshot from real/staging usage.

Exit Criteria:
1. Deployed environment is stable for first user cohort.
2. Portfolio artifacts are publish-ready.

## Weekly Execution Template
Use this each week:
1. Plan: 3 outcomes, 5 max engineering tasks.
2. Build: focus on one vertical slice, not broad parallel experiments.
3. Verify: tests + manual demo scenario + metrics capture.
4. Decide: keep/change/remove based on evidence.
5. Document: update ADRs/contracts/changelog.

## Kill List (Anti-Patterns)
1. Building parallel orchestration systems.
2. Adding tools without contracts/tests.
3. Prompt-only fixes for data contract bugs.
4. Measuring quality from anecdotal chats only.
5. Shipping without trace visibility.
