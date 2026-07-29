import json

from db._proxy import proxy

get_connection = proxy("get_connection")


def _rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def create_notification(data: dict) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO notifications (
                recipient_user_id, category, title, body, action_url, priority,
                source_type, source_id, dedupe_key, batch_id, metadata_json,
                created_by_user_id, available_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["recipient_user_id"],
                data["category"],
                data["title"],
                data["body"],
                data["action_url"],
                data["priority"],
                data.get("source_type", ""),
                data.get("source_id", ""),
                data.get("dedupe_key"),
                data.get("batch_id"),
                json.dumps(data.get("metadata") or {}, ensure_ascii=False),
                data.get("created_by_user_id"),
                data["available_at"],
            ),
        )
        notification_id = int(cursor.lastrowid or 0)
        if not notification_id and data.get("dedupe_key"):
            row = conn.execute(
                """
                SELECT id FROM notifications
                WHERE recipient_user_id = ? AND dedupe_key = ?
                """,
                (data["recipient_user_id"], data["dedupe_key"]),
            ).fetchone()
            notification_id = int(row["id"]) if row else 0
        conn.commit()
        return get_notification(notification_id) or {}
    finally:
        conn.close()


def get_notification(notification_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM notifications WHERE id = ?", (int(notification_id),)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_notifications(
    user_id: int, *, unread_only: bool, limit: int, offset: int
) -> tuple[list[dict], int]:
    conn = get_connection()
    try:
        unread = "AND read_at IS NULL" if unread_only else ""
        where = f"""
            recipient_user_id = ?
            AND cancelled_at IS NULL
            AND available_at <= datetime('now')
            {unread}
        """
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM notifications WHERE {where}", (int(user_id),)
            ).fetchone()[0]
        )
        cursor = conn.execute(
            f"""
            SELECT id, category, title, body, action_url, priority, source_type,
                   source_id, available_at, read_at, created_at
            FROM notifications
            WHERE {where}
            ORDER BY available_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (int(user_id), int(limit), int(offset)),
        )
        return _rows(cursor), total
    finally:
        conn.close()


def unread_count(user_id: int) -> int:
    conn = get_connection()
    try:
        return int(
            conn.execute(
                """
                SELECT COUNT(*) FROM notifications
                WHERE recipient_user_id = ? AND read_at IS NULL
                  AND cancelled_at IS NULL AND available_at <= datetime('now')
                """,
                (int(user_id),),
            ).fetchone()[0]
        )
    finally:
        conn.close()


def mark_read(notification_id: int, user_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE notifications SET read_at = COALESCE(read_at, datetime('now'))
            WHERE id = ? AND recipient_user_id = ? AND cancelled_at IS NULL
            """,
            (int(notification_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def mark_all_read(user_id: int) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE notifications SET read_at = datetime('now')
            WHERE recipient_user_id = ? AND read_at IS NULL
              AND cancelled_at IS NULL AND available_at <= datetime('now')
            """,
            (int(user_id),),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def list_recipients(search: str = "", limit: int = 30) -> list[dict]:
    conn = get_connection()
    try:
        pattern = f"%{search.strip()}%"
        cursor = conn.execute(
            """
            SELECT id, nome, email, UPPER(cargo) AS cargo
            FROM usuarios
            WHERE ativo = 1 AND (nome LIKE ? OR email LIKE ?)
            ORDER BY nome COLLATE NOCASE, id
            LIMIT ?
            """,
            (pattern, pattern, int(limit)),
        )
        return _rows(cursor)
    finally:
        conn.close()


def resolve_audience(audiences: list[str], user_ids: list[int]) -> list[int]:
    filters = []
    params: list = []
    if "all" in audiences:
        filters.append("1 = 1")
    if "teachers" in audiences:
        filters.append("UPPER(cargo) = 'PROFESSOR'")
    if "managers" in audiences:
        filters.append("UPPER(cargo) IN ('ADMIN', 'COORDENADOR')")
    ids = sorted({int(value) for value in user_ids if int(value) > 0})
    if ids:
        filters.append(f"id IN ({','.join('?' for _ in ids)})")
        params.extend(ids)
    if not filters:
        return []
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"""
            SELECT DISTINCT id FROM usuarios
            WHERE ativo = 1 AND ({' OR '.join(filters)})
            ORDER BY id
            """,
            params,
        )
        return [int(row["id"]) for row in cursor.fetchall()]
    finally:
        conn.close()


def list_batches(limit: int = 50) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT n.batch_id, MIN(n.title) AS title, MIN(n.priority) AS priority,
                   MIN(n.available_at) AS scheduled_at, MIN(n.created_at) AS created_at,
                   COUNT(*) AS recipients,
                   SUM(CASE WHEN n.cancelled_at IS NOT NULL THEN 1 ELSE 0 END) AS cancelled,
                   SUM(CASE WHEN n.read_at IS NOT NULL THEN 1 ELSE 0 END) AS read_count,
                   COALESCE(MIN(p.push_sent), 0) AS push_sent,
                   COALESCE(MIN(p.push_failed), 0) AS push_failed
            FROM notifications n
            LEFT JOIN (
                SELECT pn.batch_id,
                       SUM(CASE WHEN d.status = 'sent' THEN 1 ELSE 0 END) AS push_sent,
                       SUM(CASE WHEN d.status IN ('failed', 'dead') THEN 1 ELSE 0 END) AS push_failed
                FROM notification_push_deliveries d
                JOIN notifications pn ON pn.id = d.notification_id
                GROUP BY pn.batch_id
            ) p ON p.batch_id = n.batch_id
            WHERE n.batch_id IS NOT NULL
            GROUP BY n.batch_id
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return _rows(cursor)
    finally:
        conn.close()


def cancel_batch(batch_id: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE notifications SET cancelled_at = datetime('now')
            WHERE batch_id = ? AND cancelled_at IS NULL
              AND available_at > datetime('now')
            """,
            (batch_id,),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def cancel_source(source_type: str, source_id: str, *, future_only: bool = False) -> int:
    conn = get_connection()
    try:
        future = "AND available_at > datetime('now')" if future_only else ""
        cursor = conn.execute(
            f"""
            UPDATE notifications SET cancelled_at = datetime('now')
            WHERE source_type = ? AND source_id = ? AND cancelled_at IS NULL {future}
            """,
            (source_type, str(source_id)),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def cancel_source_except(source_type: str, source_id: str, dedupe_keys: list[str]) -> int:
    conn = get_connection()
    try:
        params: list = [source_type, str(source_id)]
        keep = ""
        if dedupe_keys:
            keep = f"AND dedupe_key NOT IN ({','.join('?' for _ in dedupe_keys)})"
            params.extend(dedupe_keys)
        cursor = conn.execute(
            f"""
            UPDATE notifications SET cancelled_at = datetime('now')
            WHERE source_type = ? AND source_id = ? AND cancelled_at IS NULL
              AND available_at > datetime('now') {keep}
            """,
            params,
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def list_active_source_ids(source_type: str) -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT source_id FROM notifications
            WHERE source_type = ? AND cancelled_at IS NULL
            """,
            (source_type,),
        ).fetchall()
        return [str(row["source_id"]) for row in rows]
    finally:
        conn.close()
