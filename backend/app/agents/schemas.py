from typing import List, Tuple, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.mcp_servers.perception.schemas import Stroke


class RagChunk(BaseModel):
    source: str
    text: str
    score: float = Field(default=1.0, ge=0.0)


class BBoxNorm(BaseModel):
    x: float
    y: float
    w: float
    h: float


class PerceptionState(BaseModel):
    clusters: List[List[int]] = Field(default_factory=list)
    symbol_boxes: List[BBoxNorm] = Field(default_factory=list)
    stroke_boxes: List[BBoxNorm] = Field(default_factory=list)
    num_symbols: int = 0


class State(BaseModel):
    session_id: str
    student_id: str
    img_path: str
    strokes: List[Stroke]
    created_at: datetime = Field(default_factory=datetime.now)
    sprite_sheet_path: Optional[str] = None

    rag_context: List[RagChunk] = Field(default_factory=list)
    flags: Dict[str, Any] = Field(default_factory=dict)

    perception: Optional[PerceptionState] = None
    understanding: Optional[Dict[str, Any]] = None
    canvas_analysis: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = Field(default_factory=list)
    final_response: Optional[str] = None


class ChatState(BaseModel):
    #input 
    user_message: str
    student_id: Optional[str] = None
    conversation_history: List[Dict] = Field(default_factory=list)

    # Intent classification
    intent: Optional[str] = None  # "canvas_review", "concept_question", "problem_solving", "general"
    needs_canvas_context: bool = False
    needs_course_context: bool = False
    needs_tools: bool = False
    
    # Retrieved context
    canvas_context: List[Dict] = Field(default_factory=list)  # Recent + historical canvas work
    course_context: List[Dict] = Field(default_factory=list)  # RAG results from docs
    
    # Reasoning
    reasoning_steps: List[str] = Field(default_factory=list)  # Track agent's thinking
    confidence: Optional[float] = None  # How confident is the agent?
    
    # Tool use
    tools_used: List[Dict] = Field(default_factory=list)  # Track tool invocations
    tool_results: Dict = Field(default_factory=dict)
    
    # Output
    final_response: Optional[str] = None
    follow_up_suggestions: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    total_tokens: int = 0




class AgentStep(BaseModel):
    """Single step in agent execution trace"""
    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict] = None
    observation: Optional[str] = None
    confidence: float = 0.0


class AgenticTrace(BaseModel):
    """
    Separate trace for agentic execution.
    Tracks agent decisions, thoughts, and tool usage without polluting workflow state.
    """
    # Orchestration
    intent: Optional[str] = None
    execution_plan: List[str] = Field(default_factory=list)
    current_step: int = 0
    next_action: str = "start"
    
    # Agent execution trace
    steps: List[AgentStep] = Field(default_factory=list)
    
    # Tool usage
    tool_calls: List[Dict] = Field(default_factory=list)
    
    # Completion tracking
    agents_completed: List[str] = Field(default_factory=list)
    workflow_complete: bool = False
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_tokens_used: int = 0
    
    def add_step(self, agent_name: str, thought: str, **kwargs):
        """Add a step to the trace"""
        step = AgentStep(agent_name=agent_name, thought=thought, **kwargs)
        self.steps.append(step)
    
    def mark_agent_complete(self, agent_name: str):
        """Mark an agent as completed"""
        if agent_name not in self.agents_completed:
            self.agents_completed.append(agent_name)
    
    def get_thoughts(self) -> List[str]:
        """Get all agent thoughts in order"""
        return [f"{step.agent_name}: {step.thought}" for step in self.steps]


class TutorState(BaseModel):
    # ========== Input Data ==========
    session_id: str
    student_id: str
    full_canvas_path: Optional[str] = None
    canvas_dimensions: Optional[Dict[str, int]] = None

    steps_metadata: List[Dict] = Field(default_factory=list)
    step_image_paths: Dict[str, str] = Field(default_factory=dict)

    strokes_data: List[Dict] = Field(default_factory=list)
    

    user_message: Optional[str] = None
    
    # ========== Agent Outputs (Workflow Data Only) ==========
    vision_output: Optional[Dict] = None      # Vision agent results
    reasoning_output: Optional[Dict] = None   # Reasoning agent results
    memory_output: Optional[Dict] = None      # Memory agent results
    feedback_output: Optional[Dict] = None    # Feedback agent results
    
    perception: Optional[Any] = None
    canvas_analysis: Optional[Dict] = None
    understanding: Optional[Dict] = None
    
    # ========== Final Outputs ==========
    final_response: Optional[str] = None
    annotations: List[Dict] = Field(default_factory=list)
    flags: Dict = Field(default_factory=dict)
    
    # ========== Agentic Trace (Separate Concern) ==========
    trace: AgenticTrace = Field(default_factory=AgenticTrace)
    
    class Config:
        arbitrary_types_allowed = True

