# Agentic Architecture - Clean State Separation


---

## State Architecture

### TutorState (Workflow Data Only)
```python
class TutorState:
    # Input
    session_id: str
    student_id: str
    img_path: str
    user_message: str
    
    # Agent Outputs (workflow results)
    vision_output: Dict
    reasoning_output: Dict
    memory_output: Dict
    
    # Final Outputs
    final_response: str
    annotations: List[Dict]
    
    # Agentic Trace (separate concern)
    trace: AgenticTrace  # ✅ Clean reference
```

### AgenticTrace (Agent Execution Tracking)
```python
class AgenticTrace:
    # Orchestration
    intent: str
    execution_plan: List[str]
    current_step: int
    next_action: str
    
    # Agent execution trace
    steps: List[AgentStep]  # Each agent logs here
    
    # Tool usage
    tool_calls: List[Dict]
    
    # Completion tracking
    agents_completed: List[str]
    workflow_complete: bool
    
    # Metadata
    started_at: datetime
    total_tokens_used: int
```

### AgentStep (Single Trace Entry)
```python
class AgentStep:
    agent_name: str
    timestamp: datetime
    thought: str              # What the agent is thinking
    action: str               # What action it's taking
    action_input: Dict        # Input to the action
    observation: str          # Result of the action
    confidence: float
```

---

## How Agents Use It

### Orchestrator Agent
```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("trace", {})
    
    # Add step to trace
    trace["steps"].append({
        "agent_name": "Orchestrator",
        "thought": "Starting orchestration",
        "action": "classify_and_plan"
    })
    
    # Update trace with decisions
    trace["intent"] = "canvas_review"
    trace["execution_plan"] = ["memory", "vision", "reasoning", "teacher"]
    trace["next_action"] = "memory"
    
    return {"trace": trace}
```

### Memory Agent (Example)
```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("trace", {})
    
    # Add thought
    trace["steps"].append({
        "agent_name": "MemoryAgent",
        "thought": "Analyzing search query with AI",
        "action": "ai_driven_search"
    })
    
    # Perform work
    results = await self._ai_driven_search(...)
    
    # Add observation
    trace["steps"].append({
        "agent_name": "MemoryAgent",
        "thought": f"Found {len(results)} sessions",
        "observation": f"Retrieved {len(results)} matching sessions"
    })
    
    # Mark complete
    trace["agents_completed"].append("MemoryAgent")
    
    # Return workflow data separately
    return {
        "memory_output": results,  # Workflow data
        "trace": trace             # Agentic trace
    }
```

---

## Benefits

### 1. Clean Separation
- **TutorState**: What the system is processing
- **AgenticTrace**: How the system is thinking

### 2. Easy Inspection
```python
# Get all agent thoughts
thoughts = trace.get_thoughts()
# ["Orchestrator: Starting orchestration",
#  "Orchestrator: Intent classified as canvas_review",
#  "MemoryAgent: Analyzing search query",
#  "VisionAgent: Analyzing canvas"]

# Check workflow progress
current_agent = trace["next_action"]
completed = trace["agents_completed"]
```

### 3. Debugging
```python
# See exact agent decision chain
for step in trace["steps"]:
    print(f"{step['agent_name']}: {step['thought']}")
    if step.get('action'):
        print(f"  → Action: {step['action']}")
    if step.get('observation'):
        print(f"  → Result: {step['observation']}")
```

### 4. Analytics
```python
# Track agent performance
agent_times = {}
for i, step in enumerate(trace["steps"]):
    if i > 0:
        duration = step["timestamp"] - trace["steps"][i-1]["timestamp"]
        agent_times[step["agent_name"]] = duration

# Track token usage
total_tokens = trace["total_tokens_used"]
```

---

## Subject-Agnostic Design

### Vision Agent
- No hardcoded math problem types
- AI classifies any subject dynamically
- Prompt: "Identify the subject area first (math, science, language, history, etc.)"

### Memory Agent
- AI analyzes queries and decides retrieval strategy
- No keyword matching
- Works with any subject through dynamic filtering

### Storage Schema
Same fields work for all subjects

---