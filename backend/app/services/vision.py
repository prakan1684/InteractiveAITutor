from openai import OpenAI
import os
from logger import get_logger
from typing import Optional, Dict

logger = get_logger(__name__)


class VisionService:
    def __init__(self, api_key:Optional[str] = None, model_name:Optional[str] = "gpt-4.1-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    def create_file_for_vision(self, image_path:str) -> Optional[str]:
        try:
            with open(image_path, "rb") as file_content:
                result = self.client.files.create(
                    file=file_content,
                    purpose="vision"
                )
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

    


    
        