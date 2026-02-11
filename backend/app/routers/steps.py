import json
import uuid
import traceback
from fastapi import APIRouter, Request, File, UploadFile
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.logger import get_logger
from app.services.canvas_storage import canvas_storage

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
        logger.info("/steps called")
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


        logger.info(f"Session={session_id}, Student={student_id}, Steps={len(steps_data.get('steps', []))}, Canvas={image_width}x{image_height}")



        canvas_dir = Path("canvas_uploads")
        canvas_dir.mkdir(exist_ok=True)

        

        steps_dir = canvas_dir / session_id / "steps"
        steps_dir.mkdir(parents=True, exist_ok=True)



        #saving the full canvas image
        full_canvas_file = form.get("image")
        full_canvas_path = None

        if full_canvas_file:
            full_canvas_path = steps_dir / "full_canvas.png"
            content = await full_canvas_file.read()
            logger.info(f"Canvas image received: {len(content)} bytes")
            with open(full_canvas_path, "wb") as buffer:
                buffer.write(content)
        else:
            logger.warning("No 'image' field in form data")
        

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
                
                logger.debug(f"Saved step {step_id} image to {step_image_path}")
                step_image_paths[step_id] = step_image_path
        
        # Store the latest canvas image path — analysis happens on-demand when user asks
        if full_canvas_path:
            canvas_storage.store_image(
                student_id=student_id,
                image_path=str(full_canvas_path)
            )
        
        logger.info(f"Canvas image stored for student={student_id}")
        
        # Return iOS-compatible response format
        return {
            "status": "ok",
            "problem_type": None,
            "context": None,
            "feedback": None,
            "annotations": None,
            "annotation_status": None,
            "annotation_error": None,
            "annotation_metadata": None,
            "error": None
        }
        
            
        
    except Exception as e:
        logger.error(f"Error processing steps: {str(e)}\n{traceback.format_exc()}")
        return {
            "status": "error",
            "problem_type": None,
            "context": None,
            "feedback": None,
            "annotations": None,
            "annotation_status": None,
            "annotation_error": None,
            "annotation_metadata": None,
            "error": str(e)
        }











        


