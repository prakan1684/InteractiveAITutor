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

from app_v2.stores.db import get_db, init_db

class SnapshotStore:
    def __init__(self):
        init_db()
    


    def save(self, snapshot: Snapshot) -> Snapshot:
        """
        Save a snapshot and return the stored snapshot (with id/timestamp populated).

        We store a deep copy and return a deep copy to avoid accidental external mutation.
        """
        stored = snapshot.model_copy(deep=True)
        if not stored.snapshot_id:
            stored.snapshot_id = str(uuid4())
        if stored.created_at is None:
            stored.created_at = datetime.utcnow()
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (snapshot_id, session_id, created_at, data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    stored.snapshot_id,
                    stored.session_id,
                    stored.created_at.isoformat(),
                    stored.model_dump_json(),
                ),
            )
        return stored.model_copy(deep=True)

       


    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT data FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,)
            ).fetchone()
        
        if row is None:
            return None
        
        return Snapshot.model_validate_json(row["data"])
    def get_latest_for_session(self, session_id: str) -> Optional[Snapshot]:
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT data FROM snapshots 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (session_id,)
            ).fetchone()
        
        if row is None:
            return None
        
        return Snapshot.model_validate_json(row["data"])
        
    def list_ids_for_session(self, session_id: str) -> List[str]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT snapshot_id FROM snapshots 
                WHERE session_id = ? 
                ORDER BY created_at ASC
                """,
                (session_id,)
            ).fetchall()
        
        return [row["snapshot_id"] for row in rows]
    
    def clear(self) -> None:
        """Test helper: clear all data"""
        with get_db() as conn:
            conn.execute("DELETE FROM snapshots")