"""
analytics.py
============
Simple SQLite-based logging of queries and clicks.
Lets you measure: what users ask, which products they click, conversion rates.

Database file: bot_analytics.db (auto-created on first run).
"""
import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger(__name__)
DB_FILE = "bot_analytics.db"


def init_db():
    """Create tables on first run."""
    with _conn() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                raw_message TEXT NOT NULL,
                parsed_json TEXT,
                results_count INTEGER,
                timestamp TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asin TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def log_query(user_id: int, raw: str, parsed: dict, results_count: int) -> None:
    """Record a search query."""
    try:
        with _conn() as cur:
            cur.execute(
                "INSERT INTO queries (user_id, raw_message, parsed_json, results_count, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, raw, json.dumps(parsed), results_count, datetime.utcnow().isoformat()),
            )
    except Exception:
        log.exception("Failed to log query")


def log_click(user_id: int, asin: str, action: str) -> None:
    """Record a button click (like, view, etc)."""
    try:
        with _conn() as cur:
            cur.execute(
                "INSERT INTO clicks (user_id, asin, action, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (user_id, asin, action, datetime.utcnow().isoformat()),
            )
    except Exception:
        log.exception("Failed to log click")


def get_stats() -> dict:
    """Get basic usage stats. Call from a separate script: python -c 'from analytics import get_stats; print(get_stats())'"""
    with _conn() as cur:
        total = cur.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        unique_users = cur.execute("SELECT COUNT(DISTINCT user_id) FROM queries").fetchone()[0]
        likes = cur.execute("SELECT COUNT(*) FROM clicks WHERE action='like'").fetchone()[0]
        top_queries = cur.execute(
            "SELECT raw_message, COUNT(*) as c FROM queries GROUP BY raw_message ORDER BY c DESC LIMIT 10"
        ).fetchall()
    return {
        "total_queries": total,
        "unique_users": unique_users,
        "likes": likes,
        "top_queries": top_queries,
    }


# Auto-initialize on import
init_db()
