import aiosqlite
import json
import os

DB_PATH = os.getenv("DB_PATH", "ma_prospecting.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'created',
            target_url TEXT NOT NULL,
            target_profile TEXT,
            user_filters TEXT,
            scoring_weights TEXT,
            prospects TEXT,
            signals TEXT,
            scored_prospects TEXT,
            error_message TEXT,
            step_timings TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
        );

        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            ttl_seconds INTEGER NOT NULL
        );
    """)
    await db.commit()


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
