from contextlib import closing
from sqlite3 import IntegrityError

from db.core import get_connection


def _slot_expression() -> str:
    return "COALESCE(NULLIF(he.faixa_global, 0), CAST(COALESCE(he.aula_numero, 0) AS INTEGER))"


def _map(row) -> dict:
    item = dict(row)
    return {
        "id": int(item["id"]),
        "ano_letivo": int(item["ano_letivo"]),
        "turma_id": int(item["turma_id"]),
        "turma_nome": item.get("turma_nome", "") or "",
        "turno": item.get("turno", "") or "",
        "disciplina_id": int(item["disciplina_id"]),
        "disciplina_nome": item.get("disciplina_nome", "") or "",
        "tem_apc": bool(int(item.get("disciplina_tem_apc", 0) or 0)),
        "tem_prova_bimestral": bool(
            int(item.get("disciplina_tem_prova_bimestral", 0) or 0)
        ),
        "professor_id": int(item["professor_usuario_id"]),
        "professor_nome": item.get("professor_nome", "") or "",
        "professor_email": item.get("professor_email", "") or "",
        "dia_semana": item.get("dia_semana", "") or "",
        "aula_numero": int(item.get("aula_numero") or 0),
        "faixa_global": int(item.get("faixa_global") or 0),
        "criado_em": item.get("criado_em", "") or "",
        "atualizado_em": item.get("atualizado_em", "") or "",
    }


def _query(cursor, filters=None, params=None):
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    cursor.execute(
        f"""
        SELECT
            he.id, he.ano_letivo, he.turma_id, he.disciplina_id,
            he.professor_usuario_id, he.dia_semana, he.aula_numero,
            {_slot_expression()} AS faixa_global, he.criado_em, he.atualizado_em,
            COALESCE(t.nome, '') AS turma_nome, COALESCE(t.turno, '') AS turno,
            COALESCE(d.nome, '') AS disciplina_nome,
            COALESCE(d.tem_apc, 0) AS disciplina_tem_apc,
            COALESCE(d.tem_prova_bimestral, 0) AS disciplina_tem_prova_bimestral,
            COALESCE(u.nome, '') AS professor_nome,
            COALESCE(u.email, '') AS professor_email
        FROM horarios_escolares he
        INNER JOIN turmas t ON t.id = he.turma_id
        INNER JOIN disciplinas d ON d.id = he.disciplina_id
        INNER JOIN usuarios u ON u.id = he.professor_usuario_id
        {where}
        ORDER BY he.ano_letivo DESC, t.nome COLLATE NOCASE ASC,
                 he.dia_semana ASC, faixa_global ASC, he.aula_numero ASC,
                 d.nome COLLATE NOCASE ASC, u.nome COLLATE NOCASE ASC, he.id ASC
        """,
        list(params or []),
    )
    return [_map(row) for row in cursor.fetchall()]


def list_school_years():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT DISTINCT ano_letivo FROM horarios_escolares ORDER BY ano_letivo ASC"
        ).fetchall()
    return [int(row[0]) for row in rows if int(row[0] or 0) > 0]


def list_school_schedules(
    *, ano_letivo=None, turma_id=None, disciplina_id=None, professor_id=None, dia_semana=None
):
    filters, params = [], []
    for column, value in (
        ("he.ano_letivo", ano_letivo),
        ("he.turma_id", turma_id),
        ("he.disciplina_id", disciplina_id),
        ("he.professor_usuario_id", professor_id),
    ):
        if value is not None:
            filters.append(f"{column} = ?")
            params.append(int(value))
    if str(dia_semana or "").strip():
        filters.append("UPPER(he.dia_semana) = ?")
        params.append(str(dia_semana).strip().upper())
    with closing(get_connection()) as conn:
        return _query(conn.cursor(), filters, params)


def get_school_schedule(record_id: int):
    with closing(get_connection()) as conn:
        items = _query(conn.cursor(), ["he.id = ?"], [int(record_id)])
    return items[0] if items else None


def _resolve_slot(lesson_number: int, slot: int | None) -> int:
    resolved = int(slot or 0)
    return resolved if resolved > 0 else int(lesson_number or 0)


def _teacher_conflict(
    cursor, *, year, teacher_id, weekday, slot, ignored_record_id=None
):
    filters = [
        "he.ano_letivo = ?",
        "he.professor_usuario_id = ?",
        "UPPER(he.dia_semana) = ?",
        f"{_slot_expression()} = ?",
    ]
    params = [int(year), int(teacher_id), str(weekday).strip().upper(), int(slot)]
    if ignored_record_id is not None:
        filters.append("he.id <> ?")
        params.append(int(ignored_record_id))
    row = cursor.execute(
        f"""SELECT he.id FROM horarios_escolares he
            INNER JOIN turmas t ON t.id = he.turma_id
            WHERE {' AND '.join(filters)} ORDER BY he.id ASC LIMIT 1""",
        params,
    ).fetchone()
    return int(row["id"]) if row else None


def create_school_schedule(
    *, ano_letivo, turma_id, disciplina_id, professor_usuario_id,
    dia_semana, aula_numero, faixa_global=None
):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        weekday = str(dia_semana or "").strip().upper()
        slot = _resolve_slot(aula_numero, faixa_global)
        if _teacher_conflict(
            cursor, year=ano_letivo, teacher_id=professor_usuario_id,
            weekday=weekday, slot=slot
        ):
            raise IntegrityError("idx_horarios_escolares_professor_faixa_slot")
        cursor.execute(
            """INSERT INTO horarios_escolares (
                   ano_letivo, turma_id, disciplina_id, professor_usuario_id,
                   dia_semana, aula_numero, faixa_global, criado_em, atualizado_em
               ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (int(ano_letivo), int(turma_id), int(disciplina_id), int(professor_usuario_id),
             weekday, int(aula_numero), slot),
        )
        record_id = int(cursor.lastrowid)
        conn.commit()
    return get_school_schedule(record_id)


def update_school_schedule(
    *, registro_id, ano_letivo, turma_id, disciplina_id, professor_usuario_id,
    dia_semana, aula_numero, faixa_global=None
):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        weekday = str(dia_semana or "").strip().upper()
        slot = _resolve_slot(aula_numero, faixa_global)
        if _teacher_conflict(
            cursor, year=ano_letivo, teacher_id=professor_usuario_id,
            weekday=weekday, slot=slot, ignored_record_id=registro_id
        ):
            raise IntegrityError("idx_horarios_escolares_professor_faixa_slot")
        cursor.execute(
            """UPDATE horarios_escolares
               SET ano_letivo = ?, turma_id = ?, disciplina_id = ?,
                   professor_usuario_id = ?, dia_semana = ?, aula_numero = ?,
                   faixa_global = ?, atualizado_em = datetime('now')
               WHERE id = ?""",
            (int(ano_letivo), int(turma_id), int(disciplina_id), int(professor_usuario_id),
             weekday, int(aula_numero), slot, int(registro_id)),
        )
        changed = cursor.rowcount > 0
        conn.commit()
    return get_school_schedule(registro_id) if changed else None


def delete_school_schedule(record_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.execute("DELETE FROM horarios_escolares WHERE id = ?", (int(record_id),))
        conn.commit()
        return cursor.rowcount > 0
