from db._proxy import get_database_attr


def _get_connection():
    return get_database_attr("get_connection")()


def get_submission(submission_id: int) -> dict | None:
    return get_database_attr("buscar_apc_envio_por_id")(int(submission_id))


def update_review(
    *,
    submission_id: int,
    status: str,
    message: str,
    reviewer_user_id: int | None,
) -> dict | None:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        reviewed = status != "PENDENTE"
        cursor.execute(
            """
            UPDATE apc_envios
            SET review_status = ?,
                review_message = ?,
                reviewed_by_user_id = ?,
                reviewed_at = CASE WHEN ? THEN datetime('now') ELSE NULL END,
                atualizado_em = datetime('now')
            WHERE id = ?
            """,
            (
                status,
                message,
                reviewer_user_id if reviewed else None,
                int(reviewed),
                int(submission_id),
            ),
        )
        conn.commit()
        changed = cursor.rowcount > 0
    finally:
        conn.close()
    return get_submission(submission_id) if changed else None
