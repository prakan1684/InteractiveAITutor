"""
This router is for obtaining bounding box regions of handwriting sent
from the ios canvas app

"""

from fastapi import APIRouter, File, UploadFile, Form
from logger import get_logger
from typing import List, Dict
import json
from PIL import Image, ImageDraw
import io
import uuid
logger = get_logger(__name__)

router = APIRouter()


@router.post("/regions")
async def regions(
    image: UploadFile = File(...),
    regions: str = Form(...),
    image_width: int = Form(...),
    image_height: int = Form(...),
 ):
    geometry = json.loads(regions)
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes))


    #create drawing context
    draw = ImageDraw.Draw(img)



    colors = ["red", "green", "blue", "yellow", "orange", "purple", "pink", "brown", "gray", "black"]
    for i, region in enumerate(geometry):
        bbox_px = normalized_to_pixel(region, image_width, image_height)

        logger.debug(f"Region {i}: {bbox_px}")

        color = colors[i % len(colors)]


        draw.rectangle(bbox_px, outline=color, width=2)
        

        draw.text((bbox_px[0], bbox_px[1]-15), f"Region {i}", fill=color)

    debug_path = f"/tmp/debug_{uuid.uuid4().hex[:8]}.png"
    img.save(debug_path)

    logger.info(f"Saved debug image to {debug_path}")

    return {
        "success": True, 
        "received_regions": geometry, 
        "image_width": image_width, 
        "image_height": image_height
    }

def normalized_to_pixel(
    bbox_norm: Dict[str, float],
    img_width: int,
    img_height: int
) -> List[int]:
    x_px =  int(bbox_norm['x'] * img_width)
    y_px = int(bbox_norm['y'] * img_height)
    w_px = int(bbox_norm['width'] * img_width)
    h_px = int(bbox_norm['height'] * img_height)
    return [x_px, y_px, x_px + w_px, y_px + h_px]
    
    
    

    

