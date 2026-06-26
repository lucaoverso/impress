from db.core import get_connection


def create_pre_registration(
    *,
    student_ids: list[int],
    reason_ids: list[int],
    professor_id: int,
    responsible_contact: str,
    discipline: str,
    lesson: str,
    complementary_report: str,
    occurred_at: str,
) -> dict:
    primary_student_id = int(student_ids[0])
    primary_reason_id = int(reason_ids[0])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO occurrence_pre_registrations (
            student_id,
            reason_id,
            professor_id,
            responsible_contact,
            discipline,
            lesson,
            complementary_report,
            occurred_at,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'))
        """,
        (
            primary_student_id,
            primary_reason_id,
            professor_id,
            responsible_contact,
            discipline,
            lesson,
            complementary_report,
            occurred_at,
        ),
    )
    pre_registration_id = int(cursor.lastrowid)
    cursor.executemany(
        """
        INSERT INTO occurrence_pre_registration_students (
            pre_registration_id, student_id, position
        )
        VALUES (?, ?, ?)
        """,
        [
            (pre_registration_id, int(student_id), position)
            for position, student_id in enumerate(student_ids, start=1)
        ],
    )
    cursor.executemany(
        """
        INSERT INTO occurrence_pre_registration_reasons (
            pre_registration_id, reason_id, position
        )
        VALUES (?, ?, ?)
        """,
        [
            (pre_registration_id, int(reason_id), position)
            for position, reason_id in enumerate(reason_ids, start=1)
        ],
    )
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
            pr.discipline,
            pr.lesson,
            COALESCE(pr.complementary_report, '') AS complementary_report,
            COALESCE(NULLIF(pr.occurred_at, ''), pr.created_at) AS occurred_at,
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
    pre_registration_ids = [int(row["id"]) for row in rows]
    students_by_pre_registration = _list_pre_registration_students(
        cursor,
        pre_registration_ids,
    )
    reasons_by_pre_registration = _list_pre_registration_reasons(
        cursor,
        pre_registration_ids,
    )
    for row in rows:
        pre_registration_id = int(row["id"])
        row["students"] = students_by_pre_registration.get(pre_registration_id, [])
        row["reasons"] = reasons_by_pre_registration.get(pre_registration_id, [])
        row["student_ids"] = [item["student_id"] for item in row["students"]]
        row["reason_ids"] = [item["reason_id"] for item in row["reasons"]]
    conn.close()
    return rows


def _list_pre_registration_students(cursor, pre_registration_ids: list[int]) -> dict:
    if not pre_registration_ids:
        return {}
    placeholders = ", ".join("?" for _ in pre_registration_ids)
    cursor.execute(
        f"""
        SELECT
            prs.pre_registration_id,
            prs.student_id,
            e.nome AS name,
            e.turma_id AS class_id,
            COALESCE(t.nome, '') AS class_name
        FROM occurrence_pre_registration_students prs
        JOIN estudantes e ON e.id = prs.student_id
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE prs.pre_registration_id IN ({placeholders})
        ORDER BY prs.pre_registration_id, prs.position, prs.student_id
        """,
        tuple(pre_registration_ids),
    )
    result = {}
    for row in cursor.fetchall():
        item = dict(row)
        result.setdefault(int(item["pre_registration_id"]), []).append(item)
    return result


def _list_pre_registration_reasons(cursor, pre_registration_ids: list[int]) -> dict:
    if not pre_registration_ids:
        return {}
    placeholders = ", ".join("?" for _ in pre_registration_ids)
    cursor.execute(
        f"""
        SELECT
            prr.pre_registration_id,
            prr.reason_id,
            r.name
        FROM occurrence_pre_registration_reasons prr
        JOIN occurrence_reasons r ON r.id = prr.reason_id
        WHERE prr.pre_registration_id IN ({placeholders})
        ORDER BY prr.pre_registration_id, prr.position, prr.reason_id
        """,
        tuple(pre_registration_ids),
    )
    result = {}
    for row in cursor.fetchall():
        item = dict(row)
        result.setdefault(int(item["pre_registration_id"]), []).append(item)
    return result


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


def cancel_pre_registration(pre_registration_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE occurrence_pre_registrations
        SET
            status = 'cancelled',
            updated_at = datetime('now')
        WHERE id = ?
          AND status = 'pending'
        """,
        (int(pre_registration_id),),
    )
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return get_pre_registration(pre_registration_id) if changed else None


def get_occurrence(occurrence_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, estudante_id FROM ocorrencias WHERE id = ?",
        (int(occurrence_id),),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    occurrence = dict(row)
    cursor.execute(
        """
        SELECT estudante_id
        FROM ocorrencia_estudantes
        WHERE ocorrencia_id = ? AND estudante_id IS NOT NULL
        ORDER BY ordem, estudante_id
        """,
        (int(occurrence_id),),
    )
    occurrence["student_ids"] = [
        int(item["estudante_id"]) for item in cursor.fetchall()
    ]
    if not occurrence["student_ids"] and occurrence.get("estudante_id"):
        occurrence["student_ids"] = [int(occurrence["estudante_id"])]
    conn.close()
    return occurrence
