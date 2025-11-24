from openai import OpenAI
import os
from typing import Optional, Dict
from dotenv import load_dotenv
from prompts.canvas_prompts import get_vision_prompt, DETECTION_PROMPT
import base64
import json



load_dotenv()

class VisionAnalyzer:


    """
    Analyzes images using OpenAI's Vision API GPT4.1 mini

    Integrates with RAG system for multi modal response
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = "gpt-4.1-mini"

    

    def create_file_for_vision(self, image_path:str) -> Optional[str]:
        """
        Uploads image file to openai for vision analysis


        args:
            image_path (str): Path to the image file.

        returns:
            Optional[str]: File ID if successful, None otherwise.

        """

        try:
            with open(image_path, "rb") as file_content:
                result = self.client.files.create(
                    file=file_content,
                    purpose="vision"
                )
                return result.id
        except Exception as e:
            print(f"Error creating file for vision: {e}")
            return None

    
    def analyze_image(self, image_path:str, user_query:str = None)-> Dict:
        """
        COmprehensive analysis of image using GPT 4.1 mini vision model.

        Args:
            image_path (str): Path to the image file.
            user_query (str, optional): User query for the image. Defaults to None.

        Returns:
            Dict: Analysis results.
        """


        try:
            #create file for vision
            file_id = self.create_file_for_vision(image_path)
            if not file_id:
                return {"error": "Failed to create file for vision", "analysis": None}
            
            prompt = get_vision_prompt(user_query)
            #call gpt4.1 mini api
            response = self.client.responses.create(
                model = self.model_name,
                input = [{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "file_id": file_id,
                        },
                    ],
                }],
                #reasoning = {"effort": "minimal"},
                text= {"verbosity":"medium"}
            )

            analysis = response.output_text
            print("analysis generated successfully")

            #clean up and delete the uploaded file

            try:
                self.client.files.delete(file_id)
                print("file deleted successfully")
            except Exception as e:
                pass

            return {
                "success": True,
                "analysis": analysis,
                "image_path": image_path,
                "query": user_query,
                "model": self.model_name,
            }
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path,
                "analysis": None,
            }


    def get_image_summary(self, image_path:str) -> str:
        """
        Analyze an image and return a summary of the image

        args:
            image_path (str): Path to the image file.

        returns:
            str: Summary of the image.
        """

        result = self.analyze_image(image_path, user_query="Provide a brief 2-3 sentence summary of the image.")
        if result["success"]:
            return result["analysis"]
        else:
            return f"Error analyzing image: {result['error']}"

    def detect_problem_type_and_context(self, image_path:str) -> Dict:
        """
        Automatically detect the problem type and context from the image

        args:
            image_path (str): Path to the image file.

        returns:
            Dict: Dictionary containing the problem type and context.
        """    
        try:
            #create file for vision
            file_id= self.create_file_for_vision(image_path)
            if not file_id: 
                return {
                    "success": False,
                    "error": "Failed to create file for vision",
                    "problem_type": None,
                    "context": None,
                }

            #specialized prompt for detecting the problem type and context
            prompt = DETECTION_PROMPT

            #call gpt4.1 mini api
            response = self.client.responses.create(
                model = self.model_name,
                input = [{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "file_id": file_id,
                        },
                    ],
                }],
                #reasoning = {"effort": "minimal"},
                text = {"verbosity": "medium"}
            )

            analysis = response.output_text
            #clean up file

            try:
                self.client.files.delete(file_id)
            except Exception as e:
                pass

            result = self._parse_detection_response(analysis)
            result['success'] = True
            print(f"Detected: {result['problem_type']} - {result['context']}")
            return result

        except Exception as e:
            print(f"Error detecting problem type and context: {e}")
            return {
                "success": False,
                "error": str(e),
                "problem_type": None,
                "context": None,
            }
    def _parse_detection_response(self, response: str) -> Dict:
        """
        Parses the detection response and returns a dictionary containing the problem type and context
        
        Args:
            response (str): Detection response

        Returns:
            Dict: Dictionary containing the problem type and context
        """

        try: 
            lines= response.strip().split("\n")
            result={
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
                    else:
                        result["problem_type"] = "general"
                elif line.startswith("CONTEXT:"):
                    context = line.split(":", 1)[1].strip()
                    result["context"] = context if context else None
                elif line.startswith("CONFIDENCE:"):
                    confidence = line.split(":", 1)[1].strip().lower()
                    if confidence in ["high", "medium", "low"]:
                        result["confidence"] = confidence
            
            return result
        except Exception as e:
            print(f"Error parsing detection response: {e}")
            return {
                "problem_type": None,
                "context": None,
                "confidence": None,
            }
            
            

    def annotate_image(self, image_path:str, prompt:str) -> Dict:        
        try:
            file_id = self.create_file_for_vision(image_path)
            if not file_id:
                return {
                    "success": False,
                    "error": "Failed to create file for vision",
                }
            
            #call gpt4.1 mini api
            response = self.client.responses.create(
                model=self.model_name,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "file_id": file_id,
                            "detail": "high",
                        },
                    ],
                }],
                text={"verbosity": "medium"}
            )
            raw = response.output_text
            try:
                data= json.loads(raw)
            except Exception as e:
                return {"success": False, "error": "invalid JSON response", "raw": raw}
            
            #basic validation/clamping for different shapes
            annoations = []
            for ann in data.get("annotations", []):
                t = ann.get("type")
                if t not in {"circle", "rect", "arrow", "text"}:
                    continue
                def clamp01(v): return max(0.0, min(1,0, float(v)))
                if t == "circle":
                    c == ann.get("center", {})
                    radius = float(ann.get("radius", 0))
                    if radius <=0 or radius > 1:
                        continue
                    annoations.append({
                        "type": "circle",
                        "center": {
                            "x": clamp01(c.get("x", 0)),
                            "y": clamp01(c.get("y", 0)),
                        },
                        "radius": radius,
                        "colorHex": ann.get("colorHex", "#FF0000"),
                        "lineWidth": int(ann.get("lineWidth", 3)),
                    })
                elif t == "rect":
                    tl = ann.get("topLeft", {})
                    w = float(ann.get("width", 0))
                    h = float(ann.get("height", 0))
                    if w <= 0 or h <= 0 or w > 1 or h > 1:
                        continue
                    annoations.append({
                        "type": "rect",
                        "topLeft": {
                            "x": clamp01(tl.get("x", 0)),
                            "y": clamp01(tl.get("y", 0)),
                        },
                        "width": w,
                        "height": h,
                        "colorHex": ann.get("colorHex", "#FF0000"),
                        "lineWidth": int(ann.get("lineWidth", 3)),
                    })
                elif t == arrow:
                    frm = ann.get("from", {})
                    to = ann.get("to", {})
                    annotations.append({
                        "type": "arrow",
                        "from": {
                            "x": clamp01(frm.get("x", 0)),
                            "y": clamp01(frm.get("y", 0)),
                        },
                        "to": {
                            "x": clamp01(to.get("x", 0)),
                            "y": clamp01(to.get("y", 0)),
                        },
                        "colorHex": ann.get("colorHex", "#FF0000"),
                        "lineWidth": int(ann.get("lineWidth", 3)),
                    })
                elif t == "text":
                    pos = ann.get("position", {})
                    annotations.append({
                        "type": "text",
                        "position": {
                            "x": clamp01(pos.get("x", 0)),
                            "y": clamp01(pos.get("y", 0)),
                        },
                        "text": ann.get("text", ""),
                        "colorHex": ann.get("colorHex", "#000000"),
                        "fontSize": int(ann.get("fontSize", 16)),
                    })
            metadata = data.get("metadata", {})
            if not metadata.get("annotations", []):
                metadata = {
                    "problem_type":None,
                    "context":None,
                    "confidence":None,
                }

                return {
                    "success": True,
                    "annotations": annotations,
                    "metadata": metadata,
                    "raw": raw,
                    "model": self.model_name,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw": raw,
                "model": self.model_name,
            }

                
                    


    

                



        
        