"""
Orchestrator Agent - The Brain of the Agentic System
 
Responsibilities:
- Classify user intent
- Plan multi-step workflows
- Route to specialized agents
- Coordinate agent outputs
- Ensure task completion
"""


from typing import Dict, Any
from app.agents.schemas import TutorState
from app.services.ai_service import AIService
from app.core.logger import get_logger
import json
 
logger = get_logger(__name__)


class OrchestratorAgent:
    def __init__(self):
        self.ai = AIService()
        self.name = "Orchestrator"
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method for the orchestrator

        Steps:
        1. classify user intent
        2. create execution plan
        3. decides next agent to route to
        4. update trace with decision
        """

        logger.info("🧠 Orchestrator Agent Starting")

        # Access trace from state
        trace = state.get("trace", {})
        
        # Add step to trace
        if "steps" not in trace:
            trace["steps"] = []
        
        trace["steps"].append({
            "agent_name": self.name,
            "thought": "Starting orchestration",
            "action": "classify_and_plan"
        })

        if trace.get("next_action") == "start":
            return await self._initial_planning(state)
        else:
            return await self._continue_workflow(state)
    

    async def _initial_planning(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initial planning of the workflow, will classify user intent and create an execution plan
        """


        logger.info("📋 Orchestrator: Initial Planning")

        user_message = state.get("user_message", "")
        full_canvas_path = state.get("full_canvas_path", "")
        has_canvas = bool(full_canvas_path)
        trace = state.get("trace", {})
        
        logger.info(f"🖼️ Canvas path: {full_canvas_path}")
        logger.info(f"📝 Steps metadata count: {len(state.get('steps_metadata', []))}")

        # Classify intent
        intent_result = await self._classify_intent(user_message, has_canvas)

        # Add to trace
        trace["steps"].append({
            "agent_name": self.name,
            "thought": f"Intent classified as: {intent_result.get('intent')}",
            "action": "classify_intent",
            "observation": intent_result.get('reasoning', '')
        })

        # Create plan
        plan = self._create_plan(intent_result, state)

        # Add to trace
        trace["steps"].append({
            "agent_name": self.name,
            "thought": f"Execution plan created: {plan}",
            "action": "create_plan"
        })

        # Update trace with orchestration data
        trace["intent"] = intent_result['intent']
        trace["execution_plan"] = plan
        trace["current_step"] = 0

        # Routing to first agent
        next_agent = plan[0] if plan else "end"
        trace["next_action"] = next_agent

        logger.info(f"✅ Plan created, routing to {next_agent}")

        # Return trace update while preserving all other state fields
        return {
            **state,  # Preserve all existing state fields
            "trace": trace  # Update trace
        }
    async def _classify_intent(self, user_message: str, has_canvas:bool) -> Dict:
        """
        Classify user intent based on message and canvas context
        """
        
        logger.info(f"Classifying intent for message: {user_message}")
        
        classification_prompt = f"""Analyze this student message and classify the intent.
 
Message: "{user_message}"
Has recent canvas: {has_canvas}
 
Respond in JSON format:
{{
    "intent": "canvas_review" | "problem_solving" | "concept_question" | "history_query" | "general",
    "needs_canvas": true/false,
    "needs_reasoning": true/false,
    "needs_memory": true/false,
    "reasoning": "brief explanation"
}}
 
Intent definitions:
- canvas_review: Student asking about their canvas work ("Check my work", "Is this right?", "How does it look?")
- problem_solving: Asking for help solving a problem ("Solve this", "Help me with...", "How do I...")
- concept_question: Asking to explain a concept ("What is...", "Explain...", "Why does...")
- history_query: Asking about past work ("What did we work on?", "Show my progress")
- general: Greetings, thanks, off-topic
 
Context needs:
- needs_canvas: true if intent is canvas_review OR message references "my work", "what I drew", etc.
- needs_reasoning: true if involves math evaluation or problem solving
- needs_memory: true if needs to retrieve or store session data
"""
        try:
            response = await self.ai.complete(
                messages = [{
                    "role": "user",
                    "content": classification_prompt
                }],
                temperature = 0.3,
                response_format = {"type": "json_object"}

            )

            result = json.loads(response.content)

            logger.info(f"Intent classified: {result['intent']}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to classify intent: {e}")
            return {
                "intent": "general",
                "needs_canvas": has_canvas,
                "needs_reasoning": False,
                "needs_memory": False,
                "reasoning": "Failed to classify intent"
            }
    

    def _create_plan(self, intent_result: Dict,  state: Dict[str, Any]) -> list:
        """
        Create a plan for the workflow based on the intent.
        """

        intent = intent_result.get("intent", "general")
        needs_canvas = intent_result.get("needs_canvas", False)
        needs_reasoning = intent_result.get("needs_reasoning", False)
        needs_memory = intent_result.get("needs_memory", False)

        plan = []


        #canvas review workflow

        # Canvas review workflow
        if intent == "canvas_review" or needs_canvas:
            plan.append("memory")      # Retrieve recent context
            plan.append("vision")      # Analyze canvas
            plan.append("feedback")    # Evaluate and generate feedback
            plan.append("memory")      # Store results
        
        # Problem solving workflow
        elif intent == "problem_solving":
            plan.append("feedback")    # Solve and explain
        
        # Concept question workflow
        elif intent == "concept_question":
            plan.append("feedback")    # Explain concept
        
        # History query workflow
        elif intent == "history_query":
            plan.append("memory")      # Retrieve history
            plan.append("feedback")    # Summarize
        
        # General - just respond
        else:
            plan.append("feedback")
        
        return plan
    
    async def _continue_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("⏭️ Continuing workflow...")

        trace = state.get("trace", {})
        plan = trace.get("execution_plan", [])
        current_step = trace.get("current_step", 0)

        next_step = current_step + 1

        # Check if plan is complete
        if next_step >= len(plan):
            logger.info("✅ Workflow complete")
            trace["steps"].append({
                "agent_name": self.name,
                "thought": "Workflow complete",
                "action": "end"
            })
            trace["workflow_complete"] = True
            trace["next_action"] = "end"
            trace["current_step"] = next_step
            return {
                **state,  # Preserve all existing state fields
                "trace": trace
            }

        # Continue to next agent in plan
        next_agent = plan[next_step]
        
        logger.info(f"➡️ Next agent: {next_agent} (step {next_step + 1}/{len(plan)})")
        trace["steps"].append({
            "agent_name": self.name,
            "thought": f"Routing to {next_agent} (step {next_step + 1}/{len(plan)})",
            "action": "route"
        })
        
        trace["next_action"] = next_agent
        trace["current_step"] = next_step
        
        return {
            **state,  # Preserve all existing state fields
            "trace": trace
        }
 


async def orchestrator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Langgraph node wrapper for the OrchestratorAgent.
    This function is what Langgraph calls to route to the appropriate agent.
    """
    orchestrator = OrchestratorAgent()
    return await orchestrator.execute(state)









