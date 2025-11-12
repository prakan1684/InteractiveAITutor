
import sys 
import os
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from vision_analyzer import VisionAnalyzer
def test_vision_analyzer():
    print("testing vision analyzer...")

    try:
        analyzer = VisionAnalyzer()
        
        test_image = "Fig09.jpg"
        print(f"Testing image analysis with image: {test_image}")

        result = analyzer.analyze_image(test_image, user_query="What is the user solving?")
        if result["success"]:
            print("Image analysis generated successfully.")
            print(f"Analysis: {result['analysis']}")
        else:
            print(f"Error analyzing image: {result['error']}")
    except Exception as e:
        print(f"Error testing vision analyzer: {e}")



if __name__ == "__main__":

    test_vision_analyzer()


