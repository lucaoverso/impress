from db.core import get_connection


def _one(row) -> dict | None:
    return dict(row) if row else None


def _many(rows) -> list[dict]:
    return [dict(row) for row in rows]


def _attach_files(conn, transactions: list[dict]) -> list[dict]:
    if not transactions:
        return transactions
    ids = [int(item["id"]) for item in transactions]
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT id, transaction_id, token, original_name, media_type, size_bytes, created_at
        FROM finance_attachments
        WHERE transaction_id IN ({placeholders})
        ORDER BY id ASC
        """,
        ids,
    ).fetchall()
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(int(item["transaction_id"]), []).append(item)
    for transaction in transactions:
        transaction["attachments"] = grouped.get(int(transaction["id"]), [])
    return transactions


def create_transaction(*, created_by_user_id: int, values: dict) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO finance_transactions (
                created_by_user_id, transaction_type, occurred_on, description,
                category, amount_cents, counterparty, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(created_by_user_id),
                values["transaction_type"],
                values["occurred_on"],
                values["description"],
                values["category"],
                int(values["amount_cents"]),
                values["counterparty"],
                values["notes"],
            ),
        )
        transaction_id = int(cursor.lastrowid)
        conn.commit()
        item = _one(
            conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
        ) or {}
        return _attach_files(conn, [item])[0]
    finally:
        conn.close()


def get_transaction(transaction_id: int) -> dict | None:
    conn = get_connection()
    try:
        item = _one(
            conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?", (int(transaction_id),)
            ).fetchone()
        )
        return _attach_files(conn, [item])[0] if item else None
    finally:
        conn.close()


def list_transactions(*, month: str, status: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        query = """
            SELECT * FROM finance_transactions
            WHERE substr(occurred_on, 1, 7) = ?
        """
        params: list = [month]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY occurred_on DESC, id DESC"
        return _attach_files(conn, _many(conn.execute(query, params).fetchall()))
    finally:
        conn.close()


def update_transaction(transaction_id: int, values: dict) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE finance_transactions
            SET transaction_type = ?, occurred_on = ?, description = ?, category = ?,
                amount_cents = ?, counterparty = ?, notes = ?, updated_at = datetime('now')
            WHERE id = ? AND status = 'ACTIVE'
            """,
            (
                values["transaction_type"],
                values["occurred_on"],
                values["description"],
                values["category"],
                int(values["amount_cents"]),
                values["counterparty"],
                values["notes"],
                int(transaction_id),
            ),
        )
        if cursor.rowcount <= 0:
            conn.rollback()
            return None
        conn.commit()
        item = _one(
            conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?", (int(transaction_id),)
            ).fetchone()
        ) or {}
        return _attach_files(conn, [item])[0]
    finally:
        conn.close()


def cancel_transaction(
    transaction_id: int, *, canceled_by_user_id: int, reason: str
) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE finance_transactions
            SET status = 'CANCELED', cancellation_reason = ?, canceled_by_user_id = ?,
                canceled_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ? AND status = 'ACTIVE'
            """,
            (reason, int(canceled_by_user_id), int(transaction_id)),
        )
        if cursor.rowcount <= 0:
            conn.rollback()
            return None
        conn.commit()
        item = _one(
            conn.execute(
                "SELECT * FROM finance_transactions WHERE id = ?", (int(transaction_id),)
            ).fetchone()
        ) or {}
        return _attach_files(conn, [item])[0]
    finally:
        conn.close()


def get_month_summary(month: str) -> dict:
    conn = get_connection()
    try:
        totals = dict(
            conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN transaction_type = 'INCOME' AND status = 'ACTIVE'
                        THEN amount_cents ELSE 0 END), 0) AS income_cents,
                    COALESCE(SUM(CASE WHEN transaction_type = 'EXPENSE' AND status = 'ACTIVE'
                        THEN amount_cents ELSE 0 END), 0) AS expense_cents,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_count,
                    SUM(CASE WHEN status = 'CANCELED' THEN 1 ELSE 0 END) AS canceled_count
                FROM finance_transactions
                WHERE substr(occurred_on, 1, 7) = ?
                """,
                (month,),
            ).fetchone()
        )
        categories = _many(
            conn.execute(
                """
                SELECT transaction_type, category, SUM(amount_cents) AS total_cents,
                       COUNT(*) AS transaction_count
                FROM finance_transactions
                WHERE substr(occurred_on, 1, 7) = ? AND status = 'ACTIVE'
                GROUP BY transaction_type, category
                ORDER BY transaction_type, total_cents DESC, category COLLATE NOCASE
                """,
                (month,),
            ).fetchall()
        )
        totals["balance_cents"] = int(totals["income_cents"]) - int(totals["expense_cents"])
        totals["categories"] = categories
        return totals
    finally:
        conn.close()


def create_attachment(transaction_id: int, values: dict) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO finance_attachments (
                transaction_id, token, stored_name, original_name, media_type, size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(transaction_id), values["token"], values["stored_name"],
                values["original_name"], values["media_type"], int(values["size_bytes"]),
            ),
        )
        attachment_id = int(cursor.lastrowid)
        conn.commit()
        return _one(
            conn.execute(
                "SELECT * FROM finance_attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
        ) or {}
    finally:
        conn.close()


def get_attachment_by_token(token: str) -> dict | None:
    conn = get_connection()
    try:
        return _one(
            conn.execute(
                "SELECT * FROM finance_attachments WHERE token = ?", (token,)
            ).fetchone()
        )
    finally:
        conn.close()


def delete_attachment(transaction_id: int, attachment_id: int) -> dict | None:
    conn = get_connection()
    try:
        item = _one(
            conn.execute(
                "SELECT * FROM finance_attachments WHERE id = ? AND transaction_id = ?",
                (int(attachment_id), int(transaction_id)),
            ).fetchone()
        )
        if not item:
            return None
        conn.execute("DELETE FROM finance_attachments WHERE id = ?", (int(attachment_id),))
        conn.commit()
        return item
    finally:
        conn.close()
