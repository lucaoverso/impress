from db.core import get_connection


def search_students(term: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id, e.nome, e.turma_id, COALESCE(t.nome, '') AS turma_nome
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


def get_students(student_ids: list[int]) -> list[dict]:
    ids = list(dict.fromkeys(int(item) for item in student_ids if int(item) > 0))
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT
            e.id,
            e.nome,
            e.turma_id,
            COALESCE(t.nome, '') AS turma_nome,
            COALESCE(t.turno, '') AS turno,
            e.ativo
        FROM estudantes e
        LEFT JOIN turmas t ON t.id = e.turma_id
        WHERE e.id IN ({placeholders})
        """,
        tuple(ids),
    )
    rows_by_id = {int(row["id"]): dict(row) for row in cursor.fetchall()}
    conn.close()
    return [rows_by_id[item] for item in ids if item in rows_by_id]


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


def get_reasons(reason_ids: list[int]) -> list[dict]:
    ids = list(dict.fromkeys(int(item) for item in reason_ids if int(item) > 0))
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT id, name, active, created_at, updated_at
        FROM occurrence_reasons
        WHERE id IN ({placeholders})
        """,
        tuple(ids),
    )
    rows_by_id = {int(row["id"]): dict(row) for row in cursor.fetchall()}
    conn.close()
    return [rows_by_id[item] for item in ids if item in rows_by_id]


def list_teacher_schedule(
    professor_id: int,
    *,
    year: int,
    weekday: str,
    class_ids: list[int],
) -> list[dict]:
    ids = list(dict.fromkeys(int(item) for item in class_ids if int(item) > 0))
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT
            he.turma_id,
            he.aula_numero,
            COALESCE(t.turno, '') AS turno,
            COALESCE(d.nome, '') AS disciplina_nome
        FROM horarios_escolares he
        JOIN turmas t ON t.id = he.turma_id
        JOIN disciplinas d ON d.id = he.disciplina_id
        WHERE he.professor_usuario_id = ?
          AND he.ano_letivo = ?
          AND UPPER(he.dia_semana) = ?
          AND he.turma_id IN ({placeholders})
        ORDER BY he.aula_numero, he.id
        """,
        (int(professor_id), int(year), weekday, *ids),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def list_teacher_disciplines(professor_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT d.id, d.nome AS name
        FROM professores_turmas_disciplinas ptd
        JOIN disciplinas d ON d.id = ptd.disciplina_id
        WHERE ptd.professor_usuario_id = ?
          AND COALESCE(d.ativo, 1) = 1
        ORDER BY d.nome COLLATE NOCASE
        """,
        (int(professor_id),),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


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
