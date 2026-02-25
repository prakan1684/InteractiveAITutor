from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app_v2.contracts.trace import CheckTrace


class TraceStore:
    def __init__(self):
        self._by_id: Dict[str, CheckTrace] = {}
        self._ids_by_session: Dict[str, List[str]] = {}

    
    def save(self, trace: CheckTrace) -> CheckTrace:
        """
        Save a trace and return the stored version.

        Uses deep copies to avoid accidental mutation leaks.
        """
        stored = trace.model_copy(deep=True)

        if not stored.trace_id:
            stored.trace_id = f"trace_{uuid4().hex}"

        if stored.started_at is None:
            stored.started_at = datetime.utcnow()

        self._by_id[stored.trace_id] = stored

        session_ids = self._ids_by_session.setdefault(stored.session_id, [])
        if stored.trace_id not in session_ids:
            session_ids.append(stored.trace_id)

        return stored.model_copy(deep=True)

    def get(self, trace_id: str) -> Optional[CheckTrace]:
        """
        Return a trace by id, or None if not found.
        """
        found = self._by_id.get(trace_id)
        if found is None:
            return None
        return found.model_copy(deep=True)

    def list_ids_for_session(self, session_id: str) -> List[str]:
        """
        Return trace IDs in save order for a session.
        """
        return list(self._ids_by_session.get(session_id, []))

    def clear(self) -> None:
        """
        Test helper: clear all in-memory state.
        """
        self._by_id.clear()
        self._ids_by_session.clear()
