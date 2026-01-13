from typing import Dict
from app.agents.schemas import State
from app.agents.graph import build_graph
from datetime import datetime


def run(img_path:str) -> Dict:
    """
    Orchestrates the canvas analysis process

    """
    graph = build_graph()

    initial_state = State(
        session_id="test_session",
        student_id="test_student",
        img_path=img_path,
        strokes=[],
        created_at=datetime.now(),

    )
    out_state = graph.invoke(initial_state)
    print(out_state["final_response"])
    



