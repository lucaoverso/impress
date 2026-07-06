from db._proxy import get_database_attr


def _get_connection():
    return get_database_attr("get_connection")()


def _slug(value: str) -> str:
    text = "".join(
        char.lower() if char.isalnum() else "_"
        for char in str(value or "").strip()
    )
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_") or "item"


def _unique_code(cursor, table: str, base: str) -> str:
    code = _slug(base)
    candidate = code
    suffix = 2
    while cursor.execute(f"SELECT 1 FROM {table} WHERE code = ?", (candidate,)).fetchone():
        candidate = f"{code}_{suffix}"
        suffix += 1
    return candidate


def list_catalog() -> dict:
    conn = _get_connection()
    try:
        dimensions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM teacher_followup_dimensions
                ORDER BY sort_order ASC, name COLLATE NOCASE ASC, id ASC
                """
            ).fetchall()
        ]
        criteria = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    c.*,
                    d.name AS dimension_name,
                    d.code AS dimension_code
                FROM teacher_followup_criteria c
                INNER JOIN teacher_followup_dimensions d ON d.id = c.dimension_id
                ORDER BY d.sort_order ASC, c.sort_order ASC, c.name COLLATE NOCASE ASC, c.id ASC
                """
            ).fetchall()
        ]
        models = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM teacher_followup_models
                ORDER BY target_role ASC, name COLLATE NOCASE ASC, id ASC
                """
            ).fetchall()
        ]
        links = [
            dict(row)
            for row in conn.execute(
                """
                SELECT model_id, criterion_id
                FROM teacher_followup_model_criteria
                """
            ).fetchall()
        ]
    finally:
        conn.close()
    return {
        "dimensions": dimensions,
        "criteria": criteria,
        "models": models,
        "model_criteria": links,
    }


def get_criterion(criterion_id: int) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                c.*,
                d.name AS dimension_name,
                d.code AS dimension_code
            FROM teacher_followup_criteria c
            INNER JOIN teacher_followup_dimensions d ON d.id = c.dimension_id
            WHERE c.id = ?
            """,
            (int(criterion_id),),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def create_dimension(*, name: str, description: str, active: bool = True) -> dict:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        code = _unique_code(cursor, "teacher_followup_dimensions", name)
        cursor.execute(
            """
            INSERT INTO teacher_followup_dimensions (
                code, name, description, active, sort_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 100, datetime('now'), datetime('now'))
            """,
            (code, name, description, 1 if active else 0),
        )
        dimension_id = int(cursor.lastrowid)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM teacher_followup_dimensions WHERE id = ?",
            (dimension_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row)


def create_criterion(
    *,
    dimension_id: int,
    name: str,
    description: str,
    record_type: str,
    mode: str,
    target_role: str,
    active: bool = True,
) -> dict:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        code = _unique_code(cursor, "teacher_followup_criteria", name)
        cursor.execute(
            """
            INSERT INTO teacher_followup_criteria (
                dimension_id, code, name, description, record_type, mode,
                target_role, active, sort_order, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 100, datetime('now'), datetime('now'))
            """,
            (
                int(dimension_id),
                code,
                name,
                description,
                record_type,
                mode,
                target_role,
                1 if active else 0,
            ),
        )
        criterion_id = int(cursor.lastrowid)
        conn.commit()
    finally:
        conn.close()
    return get_criterion(criterion_id)


def update_criterion(
    criterion_id: int,
    *,
    dimension_id: int,
    name: str,
    description: str,
    record_type: str,
    mode: str,
    target_role: str,
    active: bool,
) -> dict | None:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE teacher_followup_criteria
            SET dimension_id = ?,
                name = ?,
                description = ?,
                record_type = ?,
                mode = ?,
                target_role = ?,
                active = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                int(dimension_id),
                name,
                description,
                record_type,
                mode,
                target_role,
                1 if active else 0,
                int(criterion_id),
            ),
        )
        changed = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    return get_criterion(criterion_id) if changed else None


def create_model(
    *,
    name: str,
    target_role: str,
    description: str,
    criterion_ids: list[int],
    active: bool = True,
) -> dict:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        code = _unique_code(cursor, "teacher_followup_models", f"{target_role}_{name}")
        cursor.execute(
            """
            INSERT INTO teacher_followup_models (
                code, name, target_role, description, active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (code, name, target_role, description, 1 if active else 0),
        )
        model_id = int(cursor.lastrowid)
        for criterion_id in criterion_ids:
            cursor.execute(
                """
                INSERT OR IGNORE INTO teacher_followup_model_criteria (model_id, criterion_id)
                VALUES (?, ?)
                """,
                (model_id, int(criterion_id)),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM teacher_followup_models WHERE id = ?",
            (model_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row)
