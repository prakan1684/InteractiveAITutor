from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Dict, List
from app.services.vision import VisionService
from app.core.logger import get_logger

logger = get_logger(__name__)



#Defining input schemas

class AnalyzeCanvasInput(BaseModel):
    image_url: str = Field(
        description="URL of the canvas image to analyze"
    )
    prompt: str = Field(
        description="Prompt to guide the analysis"
    )
class DetectRegionsInput(BaseModel):
    strokes: List[Dict] = Field(
        description="List of stroke data from the canvas"
    )




#defining tool functions

def analyze_canvas_image(image_url: str, prompt: str) -> Dict:
    """
    Analyze a canvas image using AI vision.
    
    Args:
        image_url: URL of the canvas image to analyze
        prompt: Prompt to guide the analysis
        
    Returns:
        Analysis result from the vision service
    """
    logger.info(f"🔧 Tool called: analyze_canvas_image")
    logger.info(f"   Image: {image_url[:50]}...")
    logger.info(f"   Prompt length: {len(prompt)} chars")
    
    vision = VisionService()
    result = vision.analyze_image(image_url, prompt)
    
    logger.info(f"   Result: {'success' if result.get('success') else 'failed'}")
    return result
 
def detect_regions(strokes: List[Dict]) -> Dict:
    """
    Detect regions from canvas strokes.
    
    Args:
        strokes: List of stroke data from the canvas
        
    Returns:
        Region detection result
    """
    logger.info(f"🔧 Tool called: detect_regions")
    logger.info(f"   Strokes count: {len(strokes)}")
    
    from app.services.clustering import cluster_strokes
    clusters, symbol_boxes, stroke_boxes = cluster_strokes(strokes)
    regions = [
        {"x": box.x, "y": box.y, "w": box.w, "h": box.h}
        for box in symbol_boxes
    ]

    logger.info(f"Detected {len(regions)} regions")
    return regions



#create langchain tools

analyze_canvas_tool = StructuredTool.from_function(
    func=analyze_canvas_image,
    name="analyze_canvas_image",
    description="Analyze a canvas image using AI vision",   
    args_schema=AnalyzeCanvasInput,
    return_direct=False
)
    
detect_regions_tool = StructuredTool.from_function(
    func=detect_regions,
    name="detect_regions",
    description="Detect regions from canvas strokes",
    args_schema=DetectRegionsInput,
    return_direct=False
)

#tool registry

ALL_TOOLS = [
    analyze_canvas_tool,
    detect_regions_tool
]

VISION_TOOLS = [
    analyze_canvas_tool,
    detect_regions_tool
]



    
