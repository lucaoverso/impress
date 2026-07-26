from db._proxy import proxy

get_connection = proxy("get_connection")


def upsert_subscription(user_id: int, endpoint: str, p256dh: str, auth: str, user_agent: str):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO push_subscriptions (
                user_id, endpoint, p256dh, auth, user_agent, active
            ) VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(endpoint) DO UPDATE SET
                user_id = excluded.user_id,
                p256dh = excluded.p256dh,
                auth = excluded.auth,
                user_agent = excluded.user_agent,
                active = 1,
                failures = 0,
                disabled_at = NULL,
                updated_at = datetime('now')
            """,
            (int(user_id), endpoint, p256dh, auth, user_agent[:500]),
        )
        conn.commit()
    finally:
        conn.close()


def deactivate_subscription(user_id: int, endpoint: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE push_subscriptions
            SET active = 0, disabled_at = datetime('now'), updated_at = datetime('now')
            WHERE user_id = ? AND endpoint = ?
            """,
            (int(user_id), endpoint),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def active_subscription_count(user_id: int) -> int:
    conn = get_connection()
    try:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM push_subscriptions WHERE user_id = ? AND active = 1",
                (int(user_id),),
            ).fetchone()[0]
        )
    finally:
        conn.close()


def seed_due_deliveries() -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO notification_push_deliveries (
                notification_id, subscription_id, next_attempt_at
            )
            SELECT n.id, s.id, datetime('now')
            FROM notifications n
            JOIN push_subscriptions s ON s.user_id = n.recipient_user_id
            WHERE n.cancelled_at IS NULL
              AND n.available_at <= datetime('now')
              AND s.active = 1
              AND s.created_at <= n.available_at
            """
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def claim_delivery() -> dict | None:
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = 'failed', claimed_at = NULL
            WHERE status = 'processing'
              AND claimed_at < datetime('now', '-10 minutes')
            """
        )
        row = conn.execute(
            """
            SELECT d.id, d.attempts, n.id AS notification_id, n.title, n.body,
                   n.action_url, n.priority, s.id AS subscription_id,
                   s.endpoint, s.p256dh, s.auth
            FROM notification_push_deliveries d
            JOIN notifications n ON n.id = d.notification_id
            JOIN push_subscriptions s ON s.id = d.subscription_id
            WHERE d.status IN ('pending', 'failed')
              AND d.next_attempt_at <= datetime('now')
              AND d.attempts < 5
              AND n.cancelled_at IS NULL AND s.active = 1
            ORDER BY d.next_attempt_at, d.id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.commit()
            return None
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = 'processing', claimed_at = datetime('now'), attempts = attempts + 1
            WHERE id = ?
            """,
            (int(row["id"]),),
        )
        conn.commit()
        result = dict(row)
        result["attempts"] = int(result["attempts"]) + 1
        return result
    finally:
        conn.close()


def mark_sent(delivery_id: int, subscription_id: int):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = 'sent', sent_at = datetime('now'), claimed_at = NULL, last_error = ''
            WHERE id = ?
            """,
            (int(delivery_id),),
        )
        conn.execute(
            """
            UPDATE push_subscriptions
            SET failures = 0, last_success_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?
            """,
            (int(subscription_id),),
        )
        conn.commit()
    finally:
        conn.close()


def mark_retry(delivery_id: int, *, attempts: int, delay_seconds: int, error: str):
    status = "dead" if attempts >= 5 else "failed"
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = ?, claimed_at = NULL, last_error = ?,
                next_attempt_at = datetime('now', ?)
            WHERE id = ?
            """,
            (status, error[:300], f"+{int(delay_seconds)} seconds", int(delivery_id)),
        )
        conn.commit()
    finally:
        conn.close()


def mark_dead(delivery_id: int, error: str):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = 'dead', claimed_at = NULL, last_error = ?
            WHERE id = ?
            """,
            (error[:300], int(delivery_id)),
        )
        conn.commit()
    finally:
        conn.close()


def disable_subscription(subscription_id: int, delivery_id: int, error: str):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE push_subscriptions
            SET active = 0, failures = failures + 1, disabled_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (int(subscription_id),),
        )
        conn.execute(
            """
            UPDATE notification_push_deliveries
            SET status = 'dead', claimed_at = NULL, last_error = ?
            WHERE id = ?
            """,
            (error[:300], int(delivery_id)),
        )
        conn.commit()
    finally:
        conn.close()


def purge_old(days: int = 180) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
