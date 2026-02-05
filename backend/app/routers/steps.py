from fastapi import APIRouter, Request
from app.core.logger import get_logger
import json
import uuid
from fastapi import File, UploadFile
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.agents.nodes import run_canvas_analysis

logger = get_logger(__name__)

router = APIRouter()






@router.post("/steps")
async def analyze_steps(request: Request):
    """
    Endpoint to receive ios payload of step data. 

    multipart/form-data:
    - image: full canvas PNG
    - image_width, image_height: canvas dimensions
    - session_id, student_id: identifiers
    - steps: JSON string with step metadata
    - strokes: JSON string with stroke data
    - step_image_0, step_image_1, ...: cropped step images


    """
    try:
        logger.info(" steps endpoint called")
        form = await request.form()


        # Extract text fields
        session_id = form.get("session_id")
        student_id = form.get("student_id")
        image_width = int(form.get("image_width", 0))
        image_height = int(form.get("image_height", 0))
        
        # Parse JSON fields
        steps_json = form.get("steps")
        strokes_json = form.get("strokes")
        
        steps_data = json.loads(steps_json) if steps_json else {"steps": []}
        strokes_data = json.loads(strokes_json) if strokes_json else {"strokes": []}


        logger.info(f"📊 Session: {session_id}, Student: {student_id}")
        logger.info(f"📐 Canvas dimensions: {image_width}x{image_height}")
        logger.info(f"📝 Steps count: {len(steps_data.get('steps', []))}")
        logger.info(f"✏️ Strokes count: {len(strokes_data.get('strokes', []))}")



        canvas_dir = Path("canvas_uploads")
        canvas_dir.mkdir(exist_ok=True)

        

        steps_dir = canvas_dir / session_id / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)



        #saving the full canvas image
        full_canvas_file = form.get("image")
        full_canvas_path = None

        if full_canvas_file:
            full_canvas_path = steps_dir / "full_canvas.png"
            with open(full_canvas_path, "wb") as buffer:
                content = await full_canvas_file.read()
                buffer.write(content)
            
            logger.info(f"Saved full canvas to {full_canvas_path}")
        

        #saving the step images
        step_image_paths = {}

        for step in steps_data.get("steps", []):
            step_id = step.get("step_id")
            image_field = step.get("image_field")

            step_image_file = form.get(image_field) # <- gets "step_image_0", "step_image_1", etc.

            if step_image_file and hasattr(step_image_file, "read"):
                step_image_path = steps_dir / f"{step_id}.png"
                with open(step_image_path, "wb") as buffer:
                    content = await step_image_file.read()
                    buffer.write(content)
                
                logger.info(f"Saved step {step_id} image to {step_image_path}")
                step_image_paths[step_id] = step_image_path
        
        logger.info(f"Step image paths: {len(step_image_paths)} steps processed")

        # Run simplified canvas analysis (Vision -> Feedback)
        logger.info("🎨 Starting canvas analysis...")
        
        # Convert step_image_paths to string dict for state
        step_paths_str = {k: str(v) for k, v in step_image_paths.items()}
        
        final_state = await run_canvas_analysis(
            session_id=session_id,
            student_id=student_id,
            full_canvas_path=str(full_canvas_path),
            canvas_dimensions={"width": image_width, "height": image_height},
            steps_metadata=steps_data.get("steps", []),
            step_image_paths=step_paths_str,
            strokes_data=strokes_data.get("strokes", [])
        )
        
        logger.info("✅ Canvas analysis complete")
        
        # Extract results from final state
        feedback_output = final_state.get("feedback_output", {})
        annotations = final_state.get("annotations", [])
        final_response = final_state.get("final_response", "")

        analysis_dir = Path("analysis_results")
        analysis_dir.mkdir(exist_ok=True)
        analysis_file = analysis_dir / f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Extract detailed analysis from vision and feedback outputs
        vision_output = final_state.get("vision_output", {})
        feedback_output = final_state.get("feedback_output", {})
        
        analysis_data = {
            "session_id": session_id,
            "student_id": student_id,
            "timestamp": datetime.now().isoformat(),
            
            # Vision Analysis Details
            "vision_analysis": {
                "full_analysis": vision_output.get("full_analysis", {}),
                "step_details": vision_output.get("step_details", {}),
                "steps_metadata": vision_output.get("steps_metadata", [])
            },
            
            # Feedback Analysis Details
            "feedback_analysis": {
                "evaluation": feedback_output.get("evaluation", {}),
                "feedback_message": feedback_output.get("feedback", ""),
                "step_feedback": feedback_output.get("step_feedback", []),
                "hints": feedback_output.get("hints", []),
                "encouragement": feedback_output.get("encouragement", "")
            },
            
            # Annotations for UI
            "annotations": annotations,
            
            # Complete execution trace
            "trace": final_state.get("trace", {}),
            
            # Raw outputs (for debugging)
            "raw": {
                "vision_output": vision_output,
                "feedback_output": feedback_output,
                "full_state": final_state
            }
        }

        with open(analysis_file, "w") as f:
            json.dump(analysis_data, f, indent=2, default=str)
        
        logger.info(f"💾 Saved analysis to {analysis_file}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "feedback": final_response,
            "evaluation": feedback_output.get("evaluation", {}),
            "annotations": annotations,
            "step_feedback": feedback_output.get("step_feedback", []),
            "hints": feedback_output.get("hints", []),
            "encouragement": feedback_output.get("encouragement", ""),
            "metadata": {
                "steps_analyzed": len(steps_data.get("steps", [])),
                "canvas_dimensions": {"width": image_width, "height": image_height}
            }
        }

    except Exception as e:
        logger.error(f"Error processing steps: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }











        


