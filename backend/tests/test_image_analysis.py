import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.services.vision import VisionService


def test_vision_analyzer():
    print("testing vision analyzer...")
    try:
        vision_service = VisionService()
        result = vision_service.analyze_image(
            "/Users/pranavkandikonda/Documents/AI/InteractiveAITutor/backend/uploads/QuadEquationTest.jpg",
            "Tell me what is going on in this image",
            "medium"
        )
        print(result["analysis"])
    except Exception as e:
        print(f"Error testing vision analyzer: {e}")


if __name__ == "__main__":
    test_vision_analyzer()

    
