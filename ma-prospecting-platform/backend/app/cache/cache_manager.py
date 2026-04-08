import json
import logging
from datetime import datetime, timezone

from app.storage.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)


async def cache_get(key: str) -> dict | list | None:
    """Get a value from cache. Returns None if expired or not found."""
    db = await get_db()
    cursor = await db.execute("SELECT value, created_at, ttl_seconds FROM cache_entries WHERE key = ?", (key,))
    row = await cursor.fetchone()

    if row is None:
        return None

    created_at = datetime.fromisoformat(row["created_at"])
    elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()

    if elapsed > row["ttl_seconds"]:
        await db.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
        await db.commit()
        return None

    return json.loads(row["value"])


async def cache_set(key: str, value: dict | list, ttl_seconds: int | None = None) -> None:
    """Set a value in cache."""
    ttl = ttl_seconds or settings.cache_ttl_seconds
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT OR REPLACE INTO cache_entries (key, value, created_at, ttl_seconds)
           VALUES (?, ?, ?, ?)""",
        (key, json.dumps(value), now, ttl),
    )
    await db.commit()
    logger.debug(f"Cached key: {key} (TTL: {ttl}s)")


async def cache_invalidate(key: str) -> None:
    """Remove a specific key from cache."""
    db = await get_db()
    await db.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
    await db.commit()
