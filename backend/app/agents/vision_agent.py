"""
Vision Agent - will be the eyes

Responsibilities:
- Detect regions on the canvas
- Analyze handwritten mathematical work
- Extract structured problem data
- Classify problem type and algebra
- Assess work quality

"""


from typing import Dict, Any, List
from app.services.vision import VisionService
from app.core.logger import get_logger
from datetime import datetime
import json
 
logger = get_logger(__name__)

class VisionAgent:
    def __init__(self):
        self.vision_service = VisionService()
        self.name = "VisionAgent"
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Two-phase analysis: Full canvas first, then detailed step analysis as needed.
        """
        logger.info("👁️ Vision Agent starting...")
        
        # Debug: Log what state we received
        logger.info(f"🔍 State keys received: {list(state.keys())}")
        logger.info(f"🖼️ full_canvas_path in state: {state.get('full_canvas_path', 'NOT FOUND')}")
        logger.info(f"📝 steps_metadata count: {len(state.get('steps_metadata', []))}")
        
        trace = state.get("trace", {})
        trace.setdefault("steps", []).append({
            "agent_name": self.name,
            "thought": "Analyzing canvas with step context",
            "timestamp": datetime.now()
        })
        
        full_canvas_path = state.get("full_canvas_path")
        steps_metadata = state.get("steps_metadata", [])
        step_image_paths = state.get("step_image_paths", {})
        
        if not full_canvas_path:
            logger.warning("No canvas image provided")
            logger.warning(f"State dump: {state}")
            return {"vision_output": None, "trace": trace}
        
        # Phase 1: Analyze full canvas with step context
        logger.info(f"📊 Analyzing full canvas with {len(steps_metadata)} steps")
        full_analysis = await self._analyze_full_canvas(
            canvas_path=full_canvas_path,
            steps_metadata=steps_metadata,
            state=state
        )
        
        trace["steps"].append({
            "agent_name": self.name,
            "thought": f"Analyzed full canvas: {full_analysis.get('summary', 'N/A')}",
            "observation": f"Detected {len(steps_metadata)} steps, {len(full_analysis.get('steps_needing_analysis', []))} need detail",
            "timestamp": datetime.now()
        })
        
        # Phase 2: AI-driven detailed step analysis
        steps_to_analyze = full_analysis.get("steps_needing_analysis", [])
        step_details = {}
        
        if steps_to_analyze:
            logger.info(f"🔍 AI requested detailed analysis of {len(steps_to_analyze)} steps")
            
            for step_id in steps_to_analyze:
                step_image_path = step_image_paths.get(step_id)
                if step_image_path:
                    detail = await self._analyze_step_detail(
                        step_image_path=step_image_path,
                        step_metadata=self._get_step_metadata(step_id, steps_metadata),
                        full_context=full_analysis
                    )
                    step_details[step_id] = detail
                    logger.info(f"✅ Analyzed step {step_id}: {detail.get('operation', 'N/A')}")
        
        logger.info(f"✅ Vision analysis complete: {full_analysis.get('problem_type')}")
        
        return {
            **state,  # Preserve all existing state fields
            "vision_output": {
                "full_analysis": full_analysis,
                "step_details": step_details,
                "steps_metadata": steps_metadata
            },
            "trace": trace
        }
    
    async def _analyze_full_canvas(
        self,
        canvas_path: str,
        steps_metadata: List[Dict],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 1: Analyze the full canvas with step context.
        AI sees the big picture and decides what needs closer inspection.
        """
        steps_summary = self._build_steps_context(steps_metadata)
        
        prompt = f"""Analyze this student's work on the canvas.

**Step Context:**
The student's work has been segmented into {len(steps_metadata)} steps:
{steps_summary}

**Your Task:**
1. Understand the overall problem being solved
2. Identify the subject/topic (math, physics, chemistry, etc.)
3. Evaluate the overall approach and correctness
4. Identify which steps (if any) need detailed analysis

**Return JSON:**
{{
    "problem_type": "quadratic equation / derivative / balancing equation / etc",
    "subject": "algebra / calculus / chemistry / etc",
    "overall_correctness": "correct / partially correct / incorrect",
    "summary": "brief description of the work",
    "steps_overview": [
        {{
            "step_id": "uuid",
            "order": 0,
            "description": "what this step does",
            "appears_correct": true/false,
            "needs_detailed_analysis": true/false,
            "reason": "why it needs analysis (if true)"
        }}
    ],
    "steps_needing_analysis": ["step_id1", "step_id2"],
    "key_concepts": ["concept1", "concept2"],
    "overall_feedback_hint": "brief note for feedback agent"
}}
"""
        
        result = self.vision_service.analyze_image(canvas_path, prompt)
        
        if not result.get("success"):
            logger.error(f"Vision analysis failed: {result.get('error')}")
            return self._fallback_full_analysis(steps_metadata)
        
        try:
            analysis = json.loads(result.get("analysis", "{}"))
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            return self._fallback_full_analysis(steps_metadata)
    
    def _build_steps_context(self, steps_metadata: List[Dict]) -> str:
        """Build a text summary of step metadata for the AI"""
        if not steps_metadata:
            return "No steps detected"
        
        lines = []
        for step in sorted(steps_metadata, key=lambda s: s.get("order", 0)):
            bbox = step.get("bbox_canvas", {})
            lines.append(
                f"  Step {step.get('order', 0)}: "
                f"bbox({bbox.get('x', 0):.0f}, {bbox.get('y', 0):.0f}, "
                f"{bbox.get('width', 0):.0f}×{bbox.get('height', 0):.0f}), "
                f"strokes {step.get('stroke_start', 0)}-{step.get('stroke_end_exclusive', 0)}"
            )
        return "\n".join(lines)
    
    async def _analyze_step_detail(
        self,
        step_image_path: str,
        step_metadata: Dict,
        full_context: Dict
    ) -> Dict[str, Any]:
        """
        Phase 2: Analyze a specific step in detail.
        Only called when AI determines it's necessary.
        """
        prompt = f"""Analyze this specific step in detail.

**Context:**
- Overall problem: {full_context.get('problem_type', 'unknown')}
- This is step {step_metadata.get('order', 0)} of {len(full_context.get('steps_overview', []))}
- Overall assessment: {full_context.get('overall_correctness', 'unknown')}

**Focus on:**
1. Extract exact mathematical content (LaTeX if applicable)
2. Identify the specific operation/transformation
3. Check for errors (arithmetic, algebraic, conceptual)
4. Assess clarity and completeness

**Return JSON:**
{{
    "content": "extracted LaTeX or text",
    "operation": "specific operation being performed",
    "is_correct": true/false,
    "errors": ["list of specific errors"],
    "clarity_issues": ["list of clarity problems"],
    "suggestions": ["how to improve this step"]
}}
"""
        
        result = self.vision_service.analyze_image(step_image_path, prompt)
        
        if not result.get("success"):
            logger.error(f"Step detail analysis failed: {result.get('error')}")
            return {
                "content": "Unable to analyze",
                "operation": "unknown",
                "is_correct": False,
                "errors": ["Analysis failed"],
                "clarity_issues": [],
                "suggestions": []
            }
        
        try:
            analysis = json.loads(result.get("analysis", "{}"))
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse step detail JSON: {e}")
            return {
                "content": "Parse error",
                "operation": "unknown",
                "is_correct": False,
                "errors": ["Failed to parse analysis"],
                "clarity_issues": [],
                "suggestions": []
            }
    
    def _get_step_metadata(self, step_id: str, steps_metadata: List[Dict]) -> Dict:
        """Find step metadata by step_id"""
        for step in steps_metadata:
            if step.get("step_id") == step_id:
                return step
        return {}
    
    def _fallback_full_analysis(self, steps_metadata: List[Dict]) -> Dict:
        """Fallback analysis if full canvas analysis fails"""
        return {
            "problem_type": "unknown",
            "subject": "unknown",
            "overall_correctness": "unknown",
            "summary": "Unable to analyze canvas",
            "steps_overview": [
                {
                    "step_id": step.get("step_id", ""),
                    "order": step.get("order", 0),
                    "description": "Unable to analyze",
                    "appears_correct": False,
                    "needs_detailed_analysis": False,
                    "reason": "Analysis failed"
                }
                for step in steps_metadata
            ],
            "steps_needing_analysis": [],
            "key_concepts": [],
            "overall_feedback_hint": "Unable to provide feedback due to analysis failure"
        }

async def vision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Vision analysis node"""
    agent = VisionAgent()
    return await agent.execute(state)