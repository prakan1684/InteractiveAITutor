from openai import OpenAI
import os
from app.core.logger import get_logger
from typing import Optional, Dict
from io import BytesIO
import requests
logger = get_logger(__name__)


class VisionService:
    def __init__(self, api_key:Optional[str] = None, model_name:Optional[str] = "gpt-4.1-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    def create_file_for_vision(self, image_path:str) -> Optional[str]:
        try:
            if image_path.startswith("http"):
                #download from azure blbo storage
                response = requests.get(image_path)
                response.raise_for_status()
                file_content = BytesIO(response.content)
            else:
                file_content = open(image_path, "rb")
                

            result = self.client.files.create(
                file=file_content,
                purpose="vision"
            )

            if isinstance(file_content, BytesIO):
                file_content.close()
            else: 
                file_content.close()
            return result.id
        except Exception as e:
            logger.error(f"Error creating file for vision: {e}")
            return None
    
    def analyze_image(self, image_path, prompt:str, verbosity:str = "medium") -> Dict:
        try:
            file_id = self.create_file_for_vision(image_path)
            if not file_id:
                return {
                    "success": False,
                    "error": "Failed to create file for vision",
                }
            
            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "file_id": file_id,
                            },
                        ],
                    }
                ],
                text={"verbosity": verbosity}
            )
            
            analysis = response.output_text
            if analysis:
                logger.info("image analysis generated successfully")
            else:
                logger.error("image analysis failed")
            
            try:
                self.client.files.delete(file_id)
            except Exception as e:
                pass
            
            return {
                "success": True,
                "analysis": analysis,
                "image_path": image_path,
                "prompt": prompt,
                "model": self.model_name,
            }    
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path,
                "analysis": None,
            }
    def get_image_summary(self, image_path: str) -> str:
        """Quick summary of an image"""
        result = self.analyze_image(
            image_path=image_path,
            prompt="Provide a brief 2-3 sentence summary of this image."
        )
        return result.get("analysis", "") if result.get("success") else f"Error: {result.get('error')}"
    
    def detect_problem_type(self, image_path: str) -> Dict:
        """Detect problem type from canvas image"""
        from prompts.canvas_prompts import DETECTION_PROMPT
        result = self.analyze_image(image_path=image_path, prompt=DETECTION_PROMPT)
        
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        
        # Parse response (keep the parsing logic from VisionAnalyzer)
        return self._parse_detection_response(result["analysis"])
    
    def _parse_detection_response(self, response: str) -> Dict:
        """Parse structured detection response"""
        try:
            lines = response.strip().split("\n")
            result = {
                "problem_type": "general",
                "context": None,
                "confidence": "medium",
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("PROBLEM_TYPE:"):
                    problem_type = line.split(":", 1)[1].strip().lower()
                    if problem_type in ["math", "physics", "chemistry", "diagram"]:
                        result["problem_type"] = problem_type
                elif line.startswith("CONTEXT:"):
                    context = line.split(":", 1)[1].strip()
                    result["context"] = context if context else None
                elif line.startswith("CONFIDENCE:"):
                    confidence = line.split(":", 1)[1].strip().lower()
                    if confidence in ["high", "medium", "low"]:
                        result["confidence"] = confidence
            
            result["success"] = True
            return result
        except Exception as e:
            logger.error(f"Error parsing detection response: {e}")
            return {"success": False, "error": str(e)}


    


    
        