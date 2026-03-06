import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator


DB_PATH = Path(__file__).parent.parent.parent / "data" / "elara.db"

def init_db():
    """ Initialize database with schema """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    #Snapshots table

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        data TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_session ON snapshots(session_id)")

    # Traces table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            trace_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id)")

    # Session states table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_states (
            session_id TEXT PRIMARY KEY,
            updated_at TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    



