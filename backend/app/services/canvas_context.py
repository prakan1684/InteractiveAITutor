from dataclasses import dataclass
from functools import cached_property
from typing import List, Dict
from app.mcp_servers.perception.schemas import Box
from PIL import Image
import io

@dataclass
class CanvasContext:
    """
    Data class used to store context on canvas
    - image_width: Width of image in pixels
    - image_height: Height of image in pixels
    - symbol_boxes: List of symbol boxes detected on canvas
    - image_bytes: Image bytes
    """
    
    image_width: int
    image_height: int
    symbol_boxes: List[Box]
    image_bytes: bytes

    @cached_property
    def image(self) -> Image.Image:
        img = Image.open(io.BytesIO(self.image_bytes))
        img.load()
        return img