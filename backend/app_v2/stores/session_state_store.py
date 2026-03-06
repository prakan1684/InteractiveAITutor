from datetime import datetime
from typing import Optional

from app_v2.contracts.session_state import SessionAgentState
from app_v2.stores.db import get_db, init_db

class SessionStateStore:
    def __init__(self):
        init_db()
    
    def get(self, session_id: str) -> Optional[SessionAgentState]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT data FROM session_states WHERE session_id = ?",
                (session_id,)
            ).fetchone()
        
        if row is None:
            return None
        
        return SessionAgentState.model_validate_json(row["data"])
    
    def save(self, state: SessionAgentState) -> SessionAgentState:
        state.updated_at = datetime.utcnow()
        
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO session_states (session_id, updated_at, data)
                VALUES (?, ?, ?)
                """,
                (
                    state.session_id,
                    state.updated_at.isoformat(),
                    state.model_dump_json(),
                ),
            )
        
        return SessionAgentState.model_validate_json(state.model_dump_json())
    
    def get_or_default(self, session_id: str) -> SessionAgentState:
        existing = self.get(session_id)
        if existing:
            return existing
        return SessionAgentState(session_id=session_id)

