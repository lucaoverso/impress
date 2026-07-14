from db.core import get_connection


def email_belongs_to_another_user(email: str, user_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM usuarios WHERE LOWER(email) = LOWER(?) AND id != ?",
            (email, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def update_profile(
    user_id: int,
    name: str,
    email: str,
    *,
    password_hash: str | None = None,
    nt_hash: str | None = None,
) -> bool:
    conn = get_connection()
    try:
        if password_hash and nt_hash:
            cursor = conn.execute(
                "UPDATE usuarios SET nome = ?, email = ?, senha_hash = ?, nt_hash = ? WHERE id = ?",
                (name, email, password_hash, nt_hash, user_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE usuarios SET nome = ?, email = ? WHERE id = ?",
                (name, email, user_id),
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
