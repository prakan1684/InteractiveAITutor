
import math
from typing import List, Dict, Tuple
from app.mcp_servers.perception.schemas import Region, Expression, Step, AnalyzeCanvasOutput, Box


def analyze_canvas_image(image_path:str) -> AnalyzeCanvasOutput:
    """
    Analyzes the canvas image and returns the regions, expressions, and steps
    """
    return AnalyzeCanvasOutput(
        image_size_px=(0, 0),
        regions=[],
        expressions=[],
        steps=[],
        problem_type_guess="",
        global_confidence=0.0
    )


async def detect_regions(image_path:str, max_regions:int = 50) -> List[Region]:
    """
    Detects regions in the image
    """
    return []

async def classify_regions(regions:List[Region]) -> List[Region]:
    """
    Classifies regions in the image
    """
    return []

async def extract_expressions(image_path:str, regions:List[Region]) -> List[Expression]:
    """
    Extracts expressions from the regions
    """
    return []


async def extract_steps(expressions:List[Expression], regions:List[Region]) -> List[Step]:
    """
    Extracts steps from the expressions and regions
    """
    return []


async def guess_problem_type(steps:List[Step], expressions:List[Expression]) -> Tuple[str, float]:
    """
    Guesses the problem type based on the steps and expressions
    """
    return "", 0.0

    




