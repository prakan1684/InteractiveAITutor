"""
Memory Agent - Fully Agentic Historian
 
Responsibilities:
- Autonomously decide retrieval strategy
- Generate dynamic filters based on query understanding
- Adapt to any subject (math, science, history, language, etc.)
- No hardcoded subject-specific logic
"""
 
from typing import Dict, Any, List, Optional
from app.agents.tools.memory_tools import store_session, get_recent_work
from app.services.azure_search_service import AzureSearchService
from app.services.ai_service import AIService
from app.core.logger import get_logger
from datetime import datetime

import json
 
logger = get_logger(__name__)


class MemoryAgent:
    """
        Fully autonomous memory agent that uses llm to make all decisions
    """
    def __init__(self):
        self.name = "MemoryAgent"
        self.azure_search = AzureSearchService()
        self.ai = AIService(default_model="gpt-4o-mini")
    

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("💾 Memory Agent starting...")


        trace = state.get("trace", {})

        trace.setdefault("steps", []).append({
            "agent_name": self.name,
            "thought": "Starting memory operations",
            "timestamp": datetime.now()
        })


        #create internal plan where AI will decide which steps to take

        internal_plan = await self._create_internal_plan(state)

        #log the plan
        trace["steps"].append({
            "agent_name": self.name,
            "thought": f"My plan: {internal_plan}",
            "action": "create_internal_plan",
            "timestamp": datetime.now()
        })

        result = await self._execute_plan(state, internal_plan)

        #mark complete 
        if self.name not in trace.get("agents_completed", []):
            trace.setdefault("agents_completed", []).append(self.name)
        
        return {
            "memory_output": result,
            "trace": trace
        }

    async def _create_internal_plan(self, state: Dict[str, Any]) -> str:
        """
        AI analyzes the state and context to create an internal plan
        """

        trace = state.get("trace", {})
        intent = trace.get("intent", "")
        user_message = state.get("user_message", "")
        has_canvas = bool(state.get("img_path"))
        

        #getting workflow context
        execution_plan = trace.get("execution_plan", [])
        current_step = trace.get("current_step", 0)
        agents_completed = trace.get("agents_completed", [])

        memory_calls = [i for i, agent in enumerate(execution_plan) if agent == "memory"]
        is_first_memory_call = len(memory_calls) > 0 and current_step == memory_calls[0]
        is_last_memory_call = len(memory_calls) > 0 and current_step == memory_calls[-1]

        planning_prompt = f"""You are the Memory Agent planning your execution steps. Analyze the context and create a step-by-step plan.
 
**Context:**
- Intent: {intent}
- User Message: "{user_message}"
- Has Canvas: {has_canvas}
- Workflow Position: Step {current_step + 1}/{len(execution_plan)}
- Is First Memory Call: {is_first_memory_call}
- Is Last Memory Call: {is_last_memory_call}
- Completed Agents: {agents_completed}
 
**Available Steps:**
- analyze_context: Understand what the user needs from memory
- decide_operation: Choose between retrieve/search/store
- build_search_query: Create semantic search query
- build_filters: Create structured filters (topic, correctness, etc.)
- retrieve_recent: Get most recent work from cache
- search_semantic: Search using embeddings
- search_filtered: Search with structured filters
- rank_results: Order results by relevance
- format_output: Prepare results for downstream agents
- store_session: Save completed session to memory
 
**Planning Guidelines:**
- If first memory call + canvas_review → [analyze_context, retrieve_recent, format_output]
- If last memory call → [analyze_context, store_session]
- If history_query → [analyze_context, decide_operation, build_search_query OR build_filters, search, rank_results, format_output]
- Keep plans focused and efficient (3-6 steps typically)
- Only include steps you actually need
 
**Respond with JSON:**
{{
    "plan": ["step1", "step2", "step3", ...],
    "reasoning": "brief explanation of why this plan"
}}
 
Create the plan now."""
 
        try:
            response = await self.ai.complete(
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
            result = json.loads(response.content)
            plan = result.get("plan", [])
            reasoning = result.get("reasoning", "")
        
            logger.info(f"🤖 AI created plan: {plan}")
            logger.info(f"📝 Reasoning: {reasoning}")
        
            return plan
        
        except Exception as e:
            logger.error(f"❌ AI planning failed: {e}")
        # Fallback to safe default
            if is_last_memory_call:
                return ["analyze_context", "store_session"]
            else:
                return ["analyze_context", "retrieve_recent", "format_output"]



    async def _execute_plan(self, state: Dict[str, Any], plan: List[str]) -> Dict[str, Any]:
        trace = state.get("trace", {})

        context = {}
        final_result = None

        for i, step_name in enumerate(plan):
            trace["steps"].append({
                "agent_name": self.name,
                "thought":f"Step {i+1}/{len(plan)}: {step_name}",
                "action": step_name,
                "timestamp": datetime.now()
            })
        
        # the try should be inside the for loop to handle each step individually
        #executing the steps
            try:
                step_result = await self._execute_step(step_name, state, context)

                #store result in context for next step
                context[step_name] = step_result

                #log results

                if step_result:
                    trace["steps"].append({
                        "agent_name": self.name,
                        "thought": f"Completed {step_name}",
                        "observation": str(step_result.get("summary", "Done")),
                        "timestamp": datetime.now()
                    })

                    final_result = step_result
                
            except Exception as e:
                logger.error(f"❌ Plan execution failed: {e}")
                trace["steps"].append({
                    "agent_name": self.name,
                    "thought": f"Step {step_name} failed",
                    "observation": str(e),
                    "timestamp": datetime.now()
                })
        return final_result or {
            "type":"no result",
            "message":"No result from plan execution"
        }



    async def _execute_step(self, step_name: str, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step from the plan"""
        if step_name == "analyze_context":
            return await self._analyze_context(state, context)
        elif step_name == "retrieve_recent":
            return await self._retrieve_recent(state, context)
        elif step_name == "format_output":
            return await self._format_output(state, context)
        elif step_name == "store_session":
            return await self._store_session(state, context)
        else:
            logger.warning(f"Unknown step: {step_name}")
            return {"type": "unknown_step", "step": step_name, "message": "Unknown step"}





    async def _execute_step(
        self,
        step_name: str,
        state: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single step from the plan"""
        student_id = state.get("student_id", "student_123")

        if step_name == "analyze_context":
            return await self._analyze_context(state, context)
        elif step_name == "retrieve_recent":
            return await self._retrieve_recent(state, context)
        elif step_name == "format_output":
            return await self._format_output(state, context)
        elif step_name == "store_session":
            return await self._store_session(state, context)
        else:
            logger.warning(f"Unknown step: {step_name}")
            return {"type": "unknown_step", "step": step_name, "message": "Unknown step"}

    async def _analyze_context(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze context to understand what memory operation is needed.
        """
        trace = state.get("trace", {})
        intent = trace.get("intent", "")
        
        # Check workflow position
        execution_plan = trace.get("execution_plan", [])
        current_step = trace.get("current_step", 0)
        
        memory_calls = [i for i, agent in enumerate(execution_plan) if agent == "memory"]
        is_last_memory_call = len(memory_calls) > 0 and current_step == memory_calls[-1]
        
        operation = "store" if is_last_memory_call else "retrieve"
        
        logger.info(f"📊 Context analysis: {operation}")
        
        return {
            "type": "context_analysis",
            "operation": operation,
            "summary": f"Operation: {operation}"
        }


    async def _retrieve_recent(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve most recent work from cache.
        """
        student_id = state.get("student_id", "student_123")
        
        logger.info(f"📝 Retrieving recent work for {student_id}")
        
        recent_work = get_recent_work(student_id)
        has_recent = bool(recent_work)
        
        if has_recent:
            logger.info(f"✅ Found recent work")
        else:
            logger.info("ℹ️ No recent work found")
        
        return {
            "type": "retrieve_recent",
            "data": recent_work,
            "has_recent": has_recent,
            "summary": f"Found recent work: {has_recent}"
        }


    async def _format_output(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format results for downstream agents.
        """
        retrieve_result = context.get("retrieve_recent", {})
        
        if retrieve_result.get("has_recent"):
            data = retrieve_result.get("data")
            formatted = {
                "type": "recent_work",
                "sessions": [data] if data else [],
                "count": 1,
                "source": "cache"
            }
        else:
            formatted = {
                "type": "no_data",
                "sessions": [],
                "count": 0,
                "source": "none"
            }
        
        logger.info(f"📦 Formatted: {formatted['count']} sessions")
        
        return {
            "type": "formatted_output",
            "data": formatted,
            "summary": f"Formatted {formatted['count']} sessions"
        }


    async def _store_session(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store completed session to memory.
        """
        session_id = state.get("session_id", "")
        student_id = state.get("student_id", "student_123")
        final_response = state.get("final_response", "")
        canvas_analysis = state.get("canvas_analysis", {})
        flags = state.get("flags", {})
        canvas_image_url = state.get("img_path", "")
        
        if not session_id or not final_response:
            logger.warning("⚠️ Missing required data for storage")
            return {
                "type": "store_session",
                "success": False,
                "summary": "Missing required data"
            }
        
        logger.info(f"💾 Storing session {session_id}")
        
        success = store_session(
            session_id=session_id,
            student_id=student_id,
            final_response=final_response,
            canvas_analysis=canvas_analysis,
            flags=flags,
            canvas_image_url=canvas_image_url
        )
        
        if success:
            logger.info(f"✅ Session stored successfully")
        else:
            logger.error(f"❌ Storage failed")
        
        return {
            "type": "store_session",
            "success": success,
            "session_id": session_id,
            "summary": f"Storage {'successful' if success else 'failed'}"
        }


# LangGraph node wrapper
async def memory_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node wrapper for Memory Agent"""
    memory_agent = MemoryAgent()
    return await memory_agent.execute(state)


        
        
        