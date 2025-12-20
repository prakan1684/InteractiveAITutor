from app.services import perception as perception_service

from app.mcp_servers.perception.schemas import (
    AnalyzeCanvasInput,
    AnalyzeCanvasOutput,
    AnalyzeCanvasOptions,
    Region,
    Expression,
    Step,
)


async def analyze_canvas_image(payload: AnalyzeCanvasInput) -> AnalyzeCanvasOutput:
    return perception_service.analyze_canvas_image(payload.image_url)


