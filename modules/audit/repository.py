import json

from db._proxy import get_database_attr


def _get_connection():
    return get_database_attr("get_connection")()


def create_event(
    *,
    category: str,
    action: str,
    outcome: str,
    actor_user_id: int | None,
    actor_name: str,
    actor_email: str,
    description: str,
    entity_type: str,
    entity_id: str,
    metadata: dict,
) -> int:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_events (
                category,
                action,
                outcome,
                actor_user_id,
                actor_name,
                actor_email,
                description,
                entity_type,
                entity_id,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                action,
                outcome,
                actor_user_id,
                actor_name,
                actor_email,
                description,
                entity_type,
                entity_id,
                json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def delete_events_older_than(days: int) -> int:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM audit_events
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{int(days)} days",),
        )
        conn.commit()
        return int(cursor.rowcount)
    finally:
        conn.close()


def list_events(
    *,
    date_from: str | None,
    date_to: str | None,
    category: str | None,
    outcome: str | None,
    actor_user_id: int | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    clauses = []
    params = []

    if date_from:
        clauses.append("created_at >= ?")
        params.append(f"{date_from} 00:00:00")
    if date_to:
        clauses.append("created_at <= ?")
        params.append(f"{date_to} 23:59:59")
    if category:
        clauses.append("category = ?")
        params.append(category)
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if actor_user_id is not None:
        clauses.append("actor_user_id = ?")
        params.append(actor_user_id)
    if search:
        clauses.append(
            """
            (
                description LIKE ?
                OR actor_name LIKE ?
                OR actor_email LIKE ?
                OR action LIKE ?
            )
            """
        )
        term = f"%{search}%"
        params.extend([term, term, term, term])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = _get_connection()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM audit_events {where_sql}",
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT *
            FROM audit_events
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
        return [dict(row) for row in rows], int(total)
    finally:
        conn.close()
