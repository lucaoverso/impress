from db.core import get_connection


def search_students(term: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE e.ativo = 1
          AND (
              ? = ''
              OR LOWER(e.nome) LIKE LOWER(?)
              OR LOWER(COALESCE(t.nome, '')) LIKE LOWER(?)
          )
        ORDER BY e.nome COLLATE NOCASE
        LIMIT ?
        """,
        (term, f"%{term}%", f"%{term}%", int(limit)),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_student(student_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            e.ativo
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE e.id = ?
        """,
        (int(student_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_reasons(*, include_inactive: bool = False) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    where = "" if include_inactive else "WHERE active = 1"
    cursor.execute(
        f"""
        SELECT id, name, active, created_at, updated_at
        FROM occurrence_reasons
        {where}
        ORDER BY active DESC, name COLLATE NOCASE
        """
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_reason(reason_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, active, created_at, updated_at
        FROM occurrence_reasons
        WHERE id = ?
        """,
        (int(reason_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_reason(name: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO occurrence_reasons (name, active, created_at, updated_at)
        VALUES (?, 1, datetime('now'), datetime('now'))
        """,
        (name,),
    )
    reason_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return get_reason(reason_id)


def update_reason(reason_id: int, *, name: str | None, active: bool | None) -> dict | None:
    assignments = []
    values = []
    if name is not None:
        assignments.append("name = ?")
        values.append(name)
    if active is not None:
        assignments.append("active = ?")
        values.append(1 if active else 0)
    if not assignments:
        return get_reason(reason_id)

    assignments.append("updated_at = datetime('now')")
    values.append(int(reason_id))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE occurrence_reasons
        SET {", ".join(assignments)}
        WHERE id = ?
        """,
        tuple(values),
    )
    conn.commit()
    conn.close()
    return get_reason(reason_id)


def create_pre_registration(
    *,
    student_id: int,
    reason_id: int,
    professor_id: int,
    responsible_contact: str,
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO occurrence_pre_registrations (
            student_id,
            reason_id,
            professor_id,
            responsible_contact,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
        """,
        (student_id, reason_id, professor_id, responsible_contact),
    )
    pre_registration_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return get_pre_registration(pre_registration_id)


def get_pre_registration(pre_registration_id: int) -> dict | None:
    rows = list_pre_registrations(pre_registration_id=pre_registration_id)
    return rows[0] if rows else None


def list_pre_registrations(
    *,
    professor_id: int | None = None,
    status: str | None = None,
    pre_registration_id: int | None = None,
) -> list[dict]:
    clauses = []
    values = []
    if professor_id is not None:
        clauses.append("pr.professor_id = ?")
        values.append(int(professor_id))
    if status:
        clauses.append("pr.status = ?")
        values.append(status)
    if pre_registration_id is not None:
        clauses.append("pr.id = ?")
        values.append(int(pre_registration_id))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT
            pr.id,
            pr.student_id,
            e.nome AS student_name,
            e.turma_id,
            COALESCE(t.nome, '') AS class_name,
            pr.reason_id,
            r.name AS reason_name,
            pr.professor_id,
            u.nome AS professor_name,
            COALESCE(u.email, '') AS professor_email,
            pr.responsible_contact,
            pr.status,
            pr.occurrence_id,
            pr.created_at,
            pr.updated_at,
            pr.completed_at
        FROM occurrence_pre_registrations pr
        JOIN estudantes e ON e.id = pr.student_id
        LEFT JOIN turmas t ON t.id = e.turma_id
        JOIN occurrence_reasons r ON r.id = pr.reason_id
        JOIN usuarios u ON u.id = pr.professor_id
        {where}
        ORDER BY
            CASE pr.status WHEN 'pending' THEN 0 ELSE 1 END,
            pr.created_at DESC,
            pr.id DESC
        """,
        tuple(values),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def complete_pre_registration(pre_registration_id: int, occurrence_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ocorrencias WHERE id = ?", (int(occurrence_id),))
    if not cursor.fetchone():
        conn.close()
        return None
    cursor.execute(
        """
        UPDATE occurrence_pre_registrations
        SET
            status = 'completed',
            occurrence_id = ?,
            completed_at = datetime('now'),
            updated_at = datetime('now')
        WHERE id = ?
          AND (status = 'pending' OR occurrence_id = ?)
        """,
        (int(occurrence_id), int(pre_registration_id), int(occurrence_id)),
    )
    conn.commit()
    conn.close()
    return get_pre_registration(pre_registration_id)


def get_occurrence(occurrence_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, estudante_id FROM ocorrencias WHERE id = ?",
        (int(occurrence_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
