from db.apc import buscar_apc_periodo_por_id, listar_apc_envios, listar_apc_periodos
from db._proxy import proxy

get_connection = proxy("get_connection")


def get_period(period_id: int):
    return buscar_apc_periodo_por_id(int(period_id))


def list_periods():
    return listar_apc_periodos()


def list_submissions(period_id: int, teacher_id: int):
    return listar_apc_envios(
        periodo_id=int(period_id), professor_id=int(teacher_id)
    )


def list_due_reminders(period_id: int, teacher_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, available_at FROM notifications
            WHERE source_type = 'apc_period' AND source_id = ?
              AND recipient_user_id = ? AND dedupe_key LIKE '%h:%'
              AND cancelled_at IS NULL
            """,
            (str(period_id), int(teacher_id)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def cancel_notification(notification_id: int):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE notifications SET cancelled_at = datetime('now') WHERE id = ?",
            (int(notification_id),),
        )
        conn.commit()
    finally:
        conn.close()
