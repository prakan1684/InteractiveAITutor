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

    








        

    

                



        
        