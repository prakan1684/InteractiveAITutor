"""
In memory database for canonical snapshot objects


Should only do:
1. Save snapshots
2. Retrieve snapshots
3. track latest snapshot
4. list session history IDs


Use 3 dictionaries inside a class:

_by_id
snapshot_id -> Snapshot
_latest_by_session
session_id -> snapshot_id
_ids_by_session



"""


from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from app_v2.contracts.snapshot import Snapshot



class SnapshotStore:
    def __init__(self):
        #snapshot_id, snapshot
        self._by_id: Dict[str, Snapshot] = {}
        #session_id, snapshot_id
        self._latest_by_session: Dict[str, str] = {}
        #session_id, list[snapshot_id]
        self._ids_by_session: Dict[str, List[str]] = {}
    


    def save(self, snapshot: Snapshot) -> Snapshot:
        """
        Save a snapshot and return the stored snapshot (with id/timestamp populated).

        We store a deep copy and return a deep copy to avoid accidental external mutation.
        """

        stored  = snapshot.model_copy(deep=True)
        if not stored.snapshot_id:
            stored.snapshot_id = str(uuid4())
        if stored.created_at is None:
            stored.created_at = datetime.utcnow()
        

        self._by_id[stored.snapshot_id] = stored
        self._latest_by_session[stored.session_id] = stored.snapshot_id

        #check if session_id exists in _ids_by_session, if not create empty list
        session_ids = self._ids_by_session.setdefault(stored.session_id, [])
        if stored.snapshot_id not in session_ids:
            session_ids.append(stored.snapshot_id)




        return stored.model_copy(deep=True)


    def get(self, snapshot_id:str) -> Optional[Snapshot]:
        """
        Return a snapshot by id, or None if not found.
        """

        found = self._by_id.get(snapshot_id)
        if found is None:
            return None
        return found.model_copy(deep=True)    
    

    def get_latest_for_session(self, session_id:str) -> Optional[Snapshot]:
        """
        Return the latest snapshot for a session, or None if no snapshots exist.
        """
        snapshot_id = self._latest_by_session.get(session_id)
        if snapshot_id is None:
            return None
        return self.get(snapshot_id)
        
    def list_ids_for_session(self, session_id: str) -> List[str]:
        """
        Return snapshot IDs in save order for a session.
        Useful for debugging and later rolling-window context.
        """
        return list(self._ids_by_session.get(session_id, []))

    def clear(self) -> None:
        """
        Test helper: clear all in-memory state.
        """
        self._by_id.clear()
        self._latest_by_session.clear()
        self._ids_by_session.clear()
