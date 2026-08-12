from db._proxy import proxy

get_connection = proxy("get_connection")


def list_batch_recipients(batch_id: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT n.id AS notification_id, n.title, n.recipient_user_id AS user_id,
                   u.nome, u.email, UPPER(u.cargo) AS cargo, n.available_at,
                   n.read_at,
                   COUNT(DISTINCT CASE WHEN s.active = 1 THEN s.id END) AS active_devices
            FROM notifications n
            JOIN usuarios u ON u.id = n.recipient_user_id
            LEFT JOIN push_subscriptions s ON s.user_id = n.recipient_user_id
            WHERE n.batch_id = ?
            GROUP BY n.id, n.title, n.recipient_user_id, u.nome, u.email, u.cargo,
                     n.available_at, n.read_at
            ORDER BY n.read_at IS NULL, u.nome COLLATE NOCASE, n.id
            """,
            (batch_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
