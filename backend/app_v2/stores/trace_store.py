from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from app_v2.contracts.trace import CheckTrace
from app_v2.stores.db import get_db, init_db

class TraceStore:
    def __init__(self):
        init_db()
    
    def save(self, trace: CheckTrace) -> CheckTrace:
        stored = trace.model_copy(deep=True)
        
        if not stored.trace_id:
            stored.trace_id = f"trace_{uuid4().hex}"
        if stored.started_at is None:
            stored.started_at = datetime.utcnow()
        
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO traces (trace_id, session_id, started_at, data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    stored.trace_id,
                    stored.session_id,
                    stored.started_at.isoformat(),
                    stored.model_dump_json(),
                ),
            )
        
        return stored.model_copy(deep=True)
    
    def get(self, trace_id: str) -> Optional[CheckTrace]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT data FROM traces WHERE trace_id = ?",
                (trace_id,)
            ).fetchone()
        
        if row is None:
            return None
        
        return CheckTrace.model_validate_json(row["data"])
    
    def list_ids_for_session(self, session_id: str) -> List[str]:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT trace_id FROM traces 
                WHERE session_id = ? 
                ORDER BY started_at ASC
                """,
                (session_id,)
            ).fetchall()
        
        return [row["trace_id"] for row in rows]
    
    def clear(self) -> None:
        with get_db() as conn:
            conn.execute("DELETE FROM traces")