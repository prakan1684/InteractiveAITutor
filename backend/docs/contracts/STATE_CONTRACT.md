# State Contract (v1.0)

## Purpose
Canonical runtime state for tutor orchestration.

This contract prevents field drift between API, orchestrator, and agent nodes.

## Owners
- API Entry: `session_id`, `student_id`, `user_message`, canvas ingestion fields
- Orchestrator: `trace.intent`, `trace.execution_plan`, `trace.current_step`, `trace.next_action`
- Memory Node: `memory_output`
- Vision Node: `vision_output`
- Feedback Node: `feedback_output`, `final_response`, `annotations`
- All nodes: append to `trace.steps` and `trace.tool_calls` when relevant

## Field Table

| Field | Type | Required | Written By | Notes |
|---|---|---:|---|---|
| `state_version` | string | yes | system | Must be `"1.0"` |
| `session_id` | string | yes | API | Stable per run/session |
| `student_id` | string | yes | API | Stable per student |
| `user_message` | string | no | API/chat | Present for chat turns |
| `full_canvas_path` | string | no | steps ingest | Canonical image path |
| `canvas_dimensions` | object | no | steps ingest | `{ width, height }` style data |
| `steps_metadata` | array<object> | no | steps ingest | Ordered step metadata |
| `step_image_paths` | object | no | steps ingest | `step_id -> image_path` |
| `strokes_data` | array<object> | no | steps ingest | Raw stroke payload |
| `memory_output` | object | no | memory node | Retrieved/stored memory results |
| `vision_output` | object | no | vision node | Canvas analysis output |
| `feedback_output` | object | no | feedback node | Evaluation and pedagogical response |
| `final_response` | string | no | feedback node | Student-facing response |
| `annotations` | array<object> | no | feedback node | Step-level visual annotations |
| `flags` | object | no | nodes/tools | Runtime flags and quality signals |
| `trace` | object | yes | orchestrator + nodes | Run planning and execution trace |

## Trace Contract

### Required fields
- `trace.run_id` (string)
- `trace.steps` (array)

### Standard fields
- `intent`, `execution_plan`, `current_step`, `next_action`
- `tool_calls`, `agents_completed`, `workflow_complete`
- `started_at`, `completed_at`, `total_tokens_used`

## Invariants
1. `img_path` is forbidden. Use only `full_canvas_path`.
2. Nodes write only their owned output fields.
3. Orchestrator is the only owner of routing fields (`next_action`, `current_step`, `execution_plan`).
4. `trace` must always exist and be append-only for step history.

## Versioning
- Current: `1.0`
- Breaking changes require:
1. Bumping version.
2. Migration notes.
3. Contract test updates.
