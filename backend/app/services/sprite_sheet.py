from PIL import Image, ImageDraw, ImageFont
import math
from typing import List
from app.services.canvas_context import CanvasContext
from app.mcp_servers.perception.schemas import Box

def crop_symbol(ctx: CanvasContext, box_norm: Box, pad_px: int) -> Image.Image:

    image_width = ctx.image_width
    image_height = ctx.image_height
    image = ctx.image   
    

    x_px = int(box_norm.x * image_width)
    y_px = int(box_norm.y * image_height)
    w_px = int(box_norm.w * image_width)
    h_px = int(box_norm.h * image_height)

    x1 = max(0, x_px - pad_px)
    y1 = max(0, y_px - pad_px)
    x2 = min(image_width, x_px + w_px + pad_px)
    y2 = min(image_height, y_px + h_px + pad_px)
    
    return image.crop((x1, y1, x2, y2))


def make_tile(
    crop: Image.Image,
    tile_size: int = 192,
    label_height: int = 24,
    label: str = "symbol",
) -> Image.Image:
    mode = "RGB"
    tile = Image.new(mode, (tile_size, tile_size+label_height), (255, 255, 255))


    crop_copy = crop.convert("RGB")
    crop_copy.thumbnail((tile_size, tile_size), Image.Resampling.LANCZOS)


    paste_x = (tile_size - crop_copy.width) // 2
    paste_y = label_height + (tile_size - crop_copy.height) // 2
    tile.paste(crop_copy, (paste_x, paste_y))
    draw = ImageDraw.Draw(tile)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)  # (left, top, right, bottom)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    label_x = (tile_size - text_w) // 2
    label_y = (label_height - text_h) // 2  # keeps it vertically centered in the label band
    draw.text((label_x, label_y), label, font=font, fill=(0, 0, 0))
    #draw border
    draw.rectangle((0, 0, tile_size-1, tile_size+label_height-1), outline=(0, 0, 0), width=2)
    return tile



def build_sprite_sheet(tiles: List[Image.Image], cols: int = 6) -> Image.Image:
    if not tiles:
        return Image.new("RGB", (1, 1), (255, 255, 255))
    
    tile_w, tile_h = tiles[0].size
    rows = math.ceil(len(tiles) / cols)
    sheet_w = tile_w * cols
    sheet_h = tile_h * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))

    for i, tile in enumerate(tiles):
        col = i% cols
        row = i // cols
        sheet.paste(tile, (col * tile_w, row * tile_h))

    return sheet

def build_sprite_sheet_from_ctx(
    ctx: CanvasContext,
    cols: int = 6,
    tile_size: int = 192,
    label_height: int = 24,
    pad_px: int = 16,
) -> Image.Image:
    tiles = []
    for i, box in enumerate(ctx.symbol_boxes):
        crop = crop_symbol(ctx, box, pad_px)
        tile = make_tile(crop, tile_size, label_height, f"ID:{i}")
        tiles.append(tile)
    return build_sprite_sheet(tiles, cols)
    

    



    

