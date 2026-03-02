from copy import deepcopy
from typing import Dict, Optional


from app_v2.contracts.session_state import SessionAgentState

class SessionStateStore:
    def __init__(self):
        self._by_session: Dict[str, SessionAgentState] = {}

    def get(self, session_id:str) -> SessionAgentState | None:
        state = self._by_session.get(session_id)
        return deepcopy(state) if state else None

    def save(self, state: SessionAgentState) -> SessionAgentState:
        self._by_session[state.session_id] = deepcopy(state)
        return deepcopy(state)

    def get_or_default(self, session_id: str) -> SessionAgentState:
        existing = self.get(session_id)
        if existing:
            return existing
        return SessionAgentState(session_id=session_id)


