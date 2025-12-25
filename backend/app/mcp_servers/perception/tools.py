from app.services import perception as perception_service
from typing import List, Tuple  

from app.mcp_servers.perception.schemas import (
    AnalyzeCanvasInput,
    AnalyzeCanvasOutput,
    AnalyzeCanvasOptions,
    Region,
    Expression,
    Step,
)


async def analyze_canvas_image_tool(payload: AnalyzeCanvasInput) -> AnalyzeCanvasOutput:
    data = await perception_service.analyze_canvas_image(payload.image_url)
    return data

async def detect_regions_tool(img_path:str, max_regions:int = 50) -> List[Region]:
    data = await perception_service.detect_regions(img_path, max_regions)
    return data
    
async def classify_regions_tool(regions:List[Region]) -> List[Region]:
    data = await perception_service.classify_regions(regions)
    return data
    
async def extract_expressions_tool(img_path:str, regions:List[Region]) -> List[Expression]:
    data = await perception_service.extract_expressions(img_path, regions)
    return data
    
async def extract_steps_tool(expressions:List[Expression], regions:List[Region]) -> List[Step]:
    data = await perception_service.extract_steps(expressions, regions)
    return data
    
async def guess_problem_type_tool(steps:List[Step], expressions:List[Expression]) -> Tuple[str, float]:
    data = await perception_service.guess_problem_type(steps, expressions)
    return data

        


