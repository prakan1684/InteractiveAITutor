# Tool Contracts (v1.0)

## Purpose
Define stable interfaces for agent tools, independent of prompt internals.

## Standard Error Envelope (all tools)

```json
{
  "ok": false,
  "error": {
    "code": "TOOL_TIMEOUT",
    "message": "Timed out calling tool",
    "retryable": true,
    "details": {}
  }
}
```

## Tool: `perception.analyze_canvas`

### Input
```json
{
  "image_path": "canvas_uploads/<session>/steps/full_canvas.png",
  "steps_metadata": [],
  "step_image_paths": {},
  "options": {
    "infer_steps": true,
    "max_regions": 50
  }
}
```

### Output
```json
{
  "ok": true,
  "data": {
    "problem_type": "algebra",
    "subject": "algebra",
    "overall_correctness": "partially_correct",
    "summary": "Student isolates x with one arithmetic mistake.",
    "steps_overview": [],
    "steps_needing_analysis": [],
    "key_concepts": []
  }
}
```

### SLO / Behavior
- Timeout target: 12s
- Retryable on timeout/transient model errors
- Idempotent by input content

## Tool: `memory.get_recent`

### Input
```json
{
  "student_id": "student_123",
  "limit": 5
}
```

### Output
```json
{
  "ok": true,
  "data": {
    "sessions": [],
    "count": 0,
    "source": "cache_or_index"
  }
}
```

## Tool: `memory.store_session`

### Input
```json
{
  "session_id": "session_001",
  "student_id": "student_123",
  "summary": "Solved linear equation with support",
  "misconceptions": [],
  "canvas_analysis": {},
  "final_response": "Great correction on step 2."
}
```

### Output
```json
{
  "ok": true,
  "data": {
    "stored": true
  }
}
```

## Tool: `feedback.generate`

### Input
```json
{
  "user_message": "Did I fix it this time?",
  "vision_output": {},
  "memory_output": {}
}
```

### Output
```json
{
  "ok": true,
  "data": {
    "evaluation": {},
    "feedback": "You fixed the sign error in step 3.",
    "annotations": [],
    "hints": []
  }
}
```

## Versioning Rules
1. Additive fields: minor revision, backward compatible.
2. Removed/renamed required fields: major revision and migration required.
3. Contract tests must validate:
- schema shape
- required fields
- error envelope shape
