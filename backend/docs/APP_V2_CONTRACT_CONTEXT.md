# app_v2 Contract Context (LLM / Coding Assistant Guide)

This document explains the current contract structure for `app_v2` and how to work with it safely.

## Purpose

`app_v2` is the new contract-first backend spine for Elara Tutor V1.

Primary use case:
- `POST /check` for step validation on a canvas math workflow (Calc I/II scope)

The goal of these contracts is to:
1. Keep request/response schemas stable.
2. Make orchestrator/tool routing explicit.
3. Preserve traceability for debugging and portfolio demos.
4. Prevent architecture drift from ad-hoc dicts.

## Current Contract Files (Source of Truth)

### Enums / shared vocabulary
- `/Users/pranavkandikonda/Documents/AI/InteractiveAITutor/backend/app_v2/domain/enums.py`

### Shared contracts
- `/Users/pranavkandikonda/Documents/AI/InteractiveAITutor/backend/app_v2/contracts/snapshot.py`
- `/Users/pranavkandikonda/Documents/AI/InteractiveAITutor/backend/app_v2/contracts/trace.py`

### API contracts
- `/Users/pranavkandikonda/Documents/AI/InteractiveAITutor/backend/app_v2/contracts/check_api.py`

## Architecture Roles (Contract Perspective)

### `check_api.py`
Defines the external API contract for client <-> backend.

Use for:
- request validation in FastAPI route handlers
- response validation/serialization

Contains:
- `CheckRequest`
- `CheckResponse`
- `Highlight`
- `CorrectionPayload`
- `CorrectionRequest`
- `CorrectionResponse`

### `snapshot.py`
Defines the reusable snapshot model used across API, orchestrator, stores, and tools.

Use for:
- client payload structure
- snapshot persistence
- diffing / replay / evaluation

Contains:
- `BBox`
- `CanvasImageRef`
- `StepSnapshot`
- `ClientMeta`
- `Snapshot`

### `trace.py`
Defines the internal trace contract for one `/check` run.

Use for:
- trace persistence
- debugging
- tool call logging
- orchestrator decision logging

Contains:
- `TraceEvent`
- `ToolCallTrace`
- `CheckTrace`

## Key Semantic Distinctions (Important)

### `CheckStatus` vs `Verdict`
- `CheckStatus` (API/orchestrator-level): final user-facing outcome
- `Verdict` (tool-level): verifier result only

Do not conflate them.

Examples:
- `BASELINE_RESET` is a `CheckStatus`, not a verifier `Verdict`
- `UNCERTAIN` can appear in both, but at different layers/meanings

### Snapshot vs Trace
- `Snapshot` = the student's canvas state at a point in time
- `CheckTrace` = the backend decision log for processing that state

## Current Status Enums (V1)

From `CheckStatus`:
- `VALID`
- `INVALID`
- `UNCERTAIN`
- `NEED_MORE_CONTEXT`
- `BASELINE_RESET`
- `STALE_DUE_TO_EDIT`

From `ChangeType`:
- `APPEND`
- `EDIT_IN_PLACE`
- `REWRITE`
- `UNKNOWN`

## Current `/check` Request Shape (As Implemented)

Note: The current field name is `snapshot` (not `current_snapshot`).
This is intentional for now because it matches the current code. Do not rename without coordinating router/client updates.

```json
{
  "session_id": "session_001",
  "snapshot": {
    "session_id": "session_001",
    "user_id": "user_123",
    "steps": [
      {
        "step_id": "step_1",
        "raw_myscript": "d/dx (x^2) = 2x",
        "bbox": {
          "x": 0.12,
          "y": 0.31,
          "width": 0.42,
          "height": 0.08
        },
        "stroke_ids": ["s1", "s2"],
        "line_index": 0
      }
    ],
    "canvas_image": {
      "mime_type": "image/png",
      "path": "canvas_uploads/session_001/full.png",
      "width": 1024,
      "height": 768
    },
    "client_meta": {
      "device": "iPad",
      "app_version": "0.1.0",
      "canvas_width": 1024,
      "canvas_height": 768,
      "zoom_scale": 1.0,
      "content_offset_x": 0,
      "content_offset_y": 0
    }
  },
  "last_snapshot_id": null,
  "client_meta": null,
  "include_correction": false,
  "include_debug_trace": true
}
```

## Current `/check` Response Shape (Target Contract)

`CheckResponse` should remain the stable client-facing response.

```json
{
  "status": "NEED_MORE_CONTEXT",
  "confidence": 1.0,
  "highlights": [],
  "hint": "Baseline saved. Add one more step, then press Check again.",
  "correction": null,
  "new_snapshot_id": "snap_123",
  "trace_id": "trace_123",
  "debug_trace_summary": null
}
```

## Snapshot Contract Notes (Current Implementation)

### `BBox`
Current implementation uses normalized coordinates in `[0, 1]`:
- `x`, `y`, `width`, `height` all constrained to `0..1`

This means client code must normalize canvas coordinates before sending.

### `StepSnapshot`
Current source-of-truth field for V1 checking:
- `raw_myscript` (required, non-empty)

Derived fields are optional and may be filled later by backend tools:
- `normalized_latex`
- `structured_repr`
- `parse_confidence`

### `Snapshot.steps`
Required and must contain at least one item (`min_length=1`).

This is a V1 design decision to support diffing and step validation.

## Trace Contract Notes (Current Implementation)

`CheckTrace` is intended for internal persistence and debugging, not direct client payloads.

Trace includes:
- run identity (`trace_id`, `session_id`)
- snapshot linkage (`snapshot_id_before`, `snapshot_id_after`)
- orchestrator decision summary (`change_type`, `final_status`, `final_confidence`)
- tool call list (`tool_calls`)
- event timeline (`events`)

## Guidance for LLMs / Coding Assistants

### Do
1. Reuse models from `snapshot.py` and `trace.py` instead of duplicating shapes.
2. Use `CheckStatus`, `ChangeType`, and `Verdict` enums instead of magic strings.
3. Keep `CheckResponse` user-facing and keep internals in `CheckTrace`.
4. Validate inputs/outputs at boundaries (router, orchestrator, tools).
5. Preserve backward compatibility when changing field names.

### Do Not
1. Rename `CheckRequest.snapshot` to `current_snapshot` without updating all call sites and client payloads.
2. Put tool-specific raw output directly into `CheckResponse`.
3. Replace typed models with `dict` payloads “for convenience.”
4. Introduce broad `metadata: dict` fields for stable concepts that deserve typed fields.
5. Expand V1 scope in contracts (e.g., full grading, broad subjects) without an explicit decision.

## Planned Evolution (Not Implemented Yet)

These are expected future changes but are not the current contract:
1. Tool-specific contracts in `app_v2/tools/*` or `app_v2/contracts/tools/*`
2. Cross-field validators (e.g., max 2 highlights, request/session consistency)
3. Optional migration from `snapshot` -> `current_snapshot` (only if desired and coordinated)
4. Debug trace summary gating by environment/request flag

## Contract Change Rules

When modifying contracts:
1. Document the reason and impact.
2. Prefer additive changes over breaking changes.
3. Update client payload examples in this file.
4. Update any route/orchestrator code using the changed fields.
5. If breaking, explicitly version the contract or provide a migration path.

