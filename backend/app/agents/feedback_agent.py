"""
Feedback Agent - Evaluation and Pedagogical Response
 
Responsibilities:
- Evaluate correctness of student work
- Identify misconceptions and errors
- Generate pedagogical feedback
- Adapt tone based on performance
- Provide hints and encouragement
"""
 
from typing import Dict, Any, List, Optional
from app.services.ai_service import AIService
from app.core.logger import get_logger
from datetime import datetime
import json
 
logger = get_logger(__name__)



class FeedbackAgent:
    """
    Unified agent that evaluates work and generates pedagogical feedback.
    Combines reasoning and teaching in one cohesive step.
    """

    def __init__(self):
        self.ai = AIService(default_model="gpt-4o-mini")
        self.name = "FeedbackAgent"
    

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🎓 Feedback Agent starting...")

        trace = state.get("trace", {})

        #log start
        trace.setdefault("steps", []).append({
            "agent_name": self.name,
            "thought": "Starting evaluation and feedback generation",
            "timestamp": datetime.now()
        })


        #get inputs from previous agents
        vision_output = state.get("vision_output", {})
        memory_output = state.get("memory_output", {})
        canvas_analysis = state.get("canvas_analysis", {})


        #check if we hvae the necessary data
        if not vision_output and not canvas_analysis:
            logger.warning("No vision or canvas data available for feedback")
            trace['steps'].append({
                "agent_name": self.name,
                "thought": "No vision or canvas data available for feedback",
                "timestamp": datetime.now()
            })
            result = {
                "evaluation": {"has_analysis": False},
                "feedback": "I'd be happy to help! Please share your work so I can provide feedback.",
                "annotations": []
            }

        else:
            result = await self._generate_feedback(state, vision_output, memory_output)
            trace['steps'].append({
                "agent_name": self.name,
                "thought": "Generated feedback and evaluation",
                "observation": f"Generated feedback with {len(result.get('annotations', []))} annotations",
                "timestamp": datetime.now()
            })

        
        if self.name not in trace.get("agents_completed", []):
            trace.setdefault("agents_completed", []).append(self.name)
        
        return {
            **state,  # Preserve all existing state fields
            "feedback_output": result,
            "final_response": result.get("feedback", ""),
            "annotations": result.get("annotations", []),
            "trace": trace
        }

    async def _generate_feedback(
        self, 
        state: Dict[str, Any], 
        vision_output: Dict[str, Any], 
        memory_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate feedback using new vision output structure.
        Vision output contains: full_analysis, step_details, steps_metadata
        """
        full_analysis = vision_output.get("full_analysis", {})
        step_details = vision_output.get("step_details", {})
        steps_metadata = vision_output.get("steps_metadata", [])
        
        recent_sessions = memory_output.get("data", {}).get("sessions", [])
        user_message = state.get("user_message", "")
        
        # Build comprehensive prompt with new structure
        feedback_prompt = self._build_feedback_prompt(
            full_analysis=full_analysis,
            step_details=step_details,
            steps_metadata=steps_metadata,
            recent_sessions=recent_sessions,
            user_message=user_message
        )
        
        try:
            response = await self.ai.complete(
                messages=[{"role": "user", "content": feedback_prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.content)
            
            # Generate step-specific annotations
            annotations = self._create_step_annotations(
                steps_metadata=steps_metadata,
                step_details=step_details,
                full_analysis=full_analysis,
                feedback_result=result
            )
            
            result["annotations"] = annotations
            
            logger.info(f"✅ Feedback generated: {result.get('evaluation', {}).get('overall_correctness', 'unknown')}")
            logger.info(f"📍 Created {len(annotations)} step annotations")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Feedback generation failed: {e}")
            return {
                "evaluation": {
                    "has_analysis": False,
                    "error": str(e)
                },
                "feedback": "I encountered an issue analyzing your work. Please try again.",
                "annotations": []
            }

    

    def _build_feedback_prompt(
        self,
        full_analysis: Dict[str, Any],
        step_details: Dict[str, Any],
        steps_metadata: List[Dict],
        recent_sessions: List[Dict[str, Any]],
        user_message: str
    ) -> str:
        """
        Build comprehensive prompt for evaluation and feedback using new vision structure.
        """
        
        # Format full analysis
        problem_type = full_analysis.get("problem_type", "unknown")
        subject = full_analysis.get("subject", "unknown")
        overall_correctness = full_analysis.get("overall_correctness", "unknown")
        summary = full_analysis.get("summary", "No summary available")
        
        # Format step overview
        steps_overview = full_analysis.get("steps_overview", [])
        steps_text = ""
        for step_overview in steps_overview:
            step_id = step_overview.get("step_id")
            detail = step_details.get(step_id)
            
            steps_text += f"\n  Step {step_overview.get('order', 0)}: {step_overview.get('description', 'N/A')}\n"
            steps_text += f"    - Appears correct: {step_overview.get('appears_correct', 'unknown')}\n"
            
            if detail:
                steps_text += f"    - Content: {detail.get('content', 'N/A')}\n"
                steps_text += f"    - Operation: {detail.get('operation', 'N/A')}\n"
                if detail.get('errors'):
                    steps_text += f"    - Errors: {', '.join(detail.get('errors', []))}\n"
        
        # Format recent context
        context_text = ""
        if recent_sessions:
            context_text = "\n**Recent Work:**\n"
            for session in recent_sessions[:3]:
                context_text += f"- {session.get('topic', 'Unknown')}: {session.get('agent_feedback', 'No feedback')}\n"
        
        prompt = f"""You are an expert tutor providing feedback on student work. Analyze the work and generate helpful, pedagogical feedback.

**Overall Analysis:**
- Problem Type: {problem_type}
- Subject: {subject}
- Overall Correctness: {overall_correctness}
- Summary: {summary}

**Step-by-Step Analysis:**
{steps_text}

**User Message:**
"{user_message}"

{context_text}

**Your Task:**
1. **Evaluate Overall Work**: Based on the analysis, assess the student's understanding
2. **Identify Key Issues**: Focus on steps with errors or misconceptions
3. **Generate Feedback**: Create encouraging, helpful feedback that:
   - Acknowledges correct steps
   - Gently addresses errors in specific steps
   - Explains misconceptions
   - Provides hints (not full answers)
   - Encourages continued learning

**Respond with JSON:**
{{
    "evaluation": {{
        "overall_correctness": "{overall_correctness}",
        "correct_steps": 0,
        "total_steps": {len(steps_overview)},
        "has_errors": true/false,
        "error_types": ["calculation", "concept", "notation", etc.],
        "misconceptions": ["description of misconceptions"],
        "key_concepts": {full_analysis.get('key_concepts', [])}
    }},
    "feedback": "Your main feedback message here (2-4 sentences, encouraging and helpful)",
    "step_feedback": [
        {{
            "step_id": "uuid",
            "order": 0,
            "message": "Specific feedback for this step",
            "type": "success | error | suggestion"
        }}
    ],
    "hints": ["Helpful hint 1", "Helpful hint 2"],
    "encouragement": "Positive, encouraging closing statement"
}}

**Guidelines:**
- Be encouraging and supportive
- Focus on learning, not just correctness
- Provide specific, actionable feedback per step
- Adapt tone: more encouraging if struggling, more challenging if excelling

Generate the evaluation and feedback now."""

        return prompt
    
    def _create_step_annotations(
        self,
        steps_metadata: List[Dict],
        step_details: Dict[str, Any],
        full_analysis: Dict[str, Any],
        feedback_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create visual annotations for each step based on analysis and feedback.
        Returns list of annotations with bounding boxes for iOS to display.
        """
        annotations = []
        steps_overview = full_analysis.get("steps_overview", [])
        step_feedback_list = feedback_result.get("step_feedback", [])
        
        for step_meta in steps_metadata:
            step_id = step_meta.get("step_id")
            order = step_meta.get("order", 0)
            bbox = step_meta.get("bbox_canvas", {})
            
            # Find corresponding overview and feedback
            step_overview = next((s for s in steps_overview if s.get("step_id") == step_id), {})
            step_feedback = next((f for f in step_feedback_list if f.get("step_id") == step_id), {})
            detail = step_details.get(step_id)
            
            # Determine annotation type and message
            appears_correct = step_overview.get("appears_correct", True)
            has_errors = detail and detail.get("errors")
            
            if has_errors:
                # Error annotation
                annotations.append({
                    "step_id": step_id,
                    "order": order,
                    "type": "error",
                    "bbox": bbox,
                    "color": "red",
                    "message": step_feedback.get("message", detail.get("errors", ["Error detected"])[0]),
                    "severity": "high"
                })
            elif not appears_correct:
                # Warning annotation
                annotations.append({
                    "step_id": step_id,
                    "order": order,
                    "type": "warning",
                    "bbox": bbox,
                    "color": "yellow",
                    "message": step_feedback.get("message", "Check this step"),
                    "severity": "medium"
                })
            else:
                # Success annotation
                annotations.append({
                    "step_id": step_id,
                    "order": order,
                    "type": "success",
                    "bbox": bbox,
                    "color": "green",
                    "message": step_feedback.get("message", "✓"),
                    "severity": "low"
                })
        
        return annotations


# LangGraph node wrapper
async def feedback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node wrapper for Feedback Agent"""
    feedback_agent = FeedbackAgent()
    return await feedback_agent.execute(state) 
