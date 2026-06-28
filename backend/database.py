import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'history.db')


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                text             TEXT    NOT NULL,
                timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
                duration_seconds REAL,
                model_used       TEXT,
                language         TEXT,
                confidence       REAL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_id ON transcriptions (id DESC)"
        )


@contextmanager
def _conn():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_transcription(text, duration, model_used, language, confidence):
    """Insert a transcription row. Returns the new row id."""
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO transcriptions
               (text, duration_seconds, model_used, language, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (text, duration, model_used, language, confidence),
        )
        return cur.lastrowid


def get_history(limit=50):
    """Return the most recent `limit` transcriptions as a list of dicts."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transcriptions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats():
    """Return total count, avg duration, and most-used model."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)            AS total,
                AVG(duration_seconds) AS avg_duration,
                (
                    SELECT model_used
                    FROM   transcriptions
                    WHERE  model_used IS NOT NULL
                    GROUP  BY model_used
                    ORDER  BY COUNT(*) DESC
                    LIMIT  1
                ) AS most_used_model
            FROM transcriptions
        """).fetchone()
        if row:
            return dict(row)
        return {'total': 0, 'avg_duration': None, 'most_used_model': None}


def delete_transcription(id):
    """Delete a transcription by id. Returns True if a row was deleted."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM transcriptions WHERE id = ?", (id,))
        return cur.rowcount > 0
