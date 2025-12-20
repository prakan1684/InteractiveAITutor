
from typing import List, Dict

def annotate(proposed_regions: List[Dict]) -> List[Dict]:
    """
    Takes in a list of proposed regions and returns a teh coordinates of the regions to highlight


    """

    highlights= []
    for region in proposed_regions:
        highlights.append({
            "type":"highlight",
            "topleft": region.get("top_left", {"x":0,"y":0}),
            "width": region.get("width", 0),
            "height": region.get("height", 0),
            "colorHex": region.get("color_hex", "#FFFF00"),
            "opacity": region.get("opacity", 0.25)
        })
    return highlights