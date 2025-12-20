
from typing import Dict, List

def reason(observations:Dict, classification:Dict) -> Dict:
    """
    Takes in observations, classification, and returns a structured response
    returns:
        analysis_text: str
        hints: List[str]
        issues: List[str]
        proposed_regions: List[Dict]
    """
    return {
        "analysis_text":"",
        "hints":[],
        "issues":[],
        "proposed_regions":[],
    }