import json
from datetime import datetime, timezone

from app.storage.database import get_db


async def create_pipeline_run(run_id: str, target_url: str, user_filters: dict, scoring_weights: dict) -> dict:
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO pipeline_runs (id, created_at, status, target_url, user_filters, scoring_weights)
           VALUES (?, ?, 'created', ?, ?, ?)""",
        (run_id, now, target_url, json.dumps(user_filters), json.dumps(scoring_weights)),
    )
    await db.commit()
    return {"id": run_id, "created_at": now, "status": "created", "target_url": target_url}


async def get_pipeline_run(run_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,))
    row = await cursor.fetchone()
    if row is None:
        return None

    result = dict(row)
    for field in ("target_profile", "user_filters", "scoring_weights", "prospects", "signals", "scored_prospects", "step_timings"):
        if result.get(field):
            result[field] = json.loads(result[field])
    return result


async def update_pipeline_run(run_id: str, **fields) -> None:
    db = await get_db()
    json_fields = {"target_profile", "user_filters", "scoring_weights", "prospects", "signals", "scored_prospects", "step_timings"}

    set_clauses = []
    values = []
    for key, value in fields.items():
        set_clauses.append(f"{key} = ?")
        values.append(json.dumps(value) if key in json_fields else value)

    values.append(run_id)
    await db.execute(
        f"UPDATE pipeline_runs SET {', '.join(set_clauses)} WHERE id = ?",
        values,
    )
    await db.commit()


async def save_chat_message(message_id: str, run_id: str, role: str, content: str) -> None:
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO chat_messages (id, run_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (message_id, run_id, role, content, now),
    )
    await db.commit()


async def get_chat_history(run_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM chat_messages WHERE run_id = ? ORDER BY created_at ASC",
        (run_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
