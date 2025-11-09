from openai import OpenAI
import os
from typing import Optional, Dict
from dotenv import load_dotenv
import base64



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
            

            if user_query:
                prompt = f"""As an educational AI tutor, analyze this image and specifically answer: {user_query}

Additionally, provide:
1. **Content Summary**: What educational content is shown?
2. **Key Details**: Extract any text, numbers, or important visual elements
3. **Educational Context**: How does this relate to learning objectives?
4. **Concepts Covered**: What topics or subjects does this image address?

Be thorough and educational - this will help students understand the material."""
            else:
                prompt = """As an educational AI tutor, provide a comprehensive analysis of this educational image:

1. **Content Type**: What type of educational material is this? (diagram, graph, photo, whiteboard, etc.)
2. **Text Extraction**: Transcribe any visible text, equations, labels, or annotations
3. **Visual Elements**: Describe charts, graphs, diagrams, illustrations in detail
4. **Data & Values**: Include any numerical data, measurements, or specific values shown
5. **Key Concepts**: What educational concepts, topics, or subjects are presented?
6. **Learning Objectives**: What would a student learn from this image?
7. **Context Clues**: Any additional details that provide educational context

Be precise and comprehensive - students will use this analysis for studying."""

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
                }]
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
            prompt = """Analyze this student's whiteboard/canvas work and identify:

1. **Problem Type**: Classify as ONE of these:
   - "math" - if it contains mathematical equations, calculus, algebra, geometry, etc.
   - "physics" - if it contains physics formulas, force diagrams, motion equations, etc.
   - "chemistry" - if it contains chemical formulas, reactions, molecular structures, etc.
   - "diagram" - if it's primarily a concept map, flowchart, or visual diagram
   - "general" - if it's notes, text, or unclear

2. **Context**: In ONE concise sentence, describe what specific problem or concept they're working on.
   Examples:
   - "Solving the integral of x squared"
   - "Drawing free body diagram for inclined plane"
   - "Balancing chemical equation for combustion"
   - "Creating concept map for cell biology"

3. **Confidence**: How clear is the content? (high/medium/low)

Respond in EXACTLY this format (nothing else):
PROBLEM_TYPE: [type]
CONTEXT: [one sentence]
CONFIDENCE: [level]

Be concise and precise."""

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
                }]
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
            
            







        

    

                



        
        