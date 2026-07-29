from contextlib import closing
from sqlite3 import IntegrityError

from db.core import get_connection
from modules.scheduling.school_schedule_repository import _teacher_conflict


def _map(row) -> dict:
    item = dict(row)
    return {
        "id": int(item["id"]),
        "ano_letivo": int(item["ano_letivo"]),
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
        SELECT aa.id, aa.ano_letivo, aa.professor_usuario_id,
               aa.dia_semana, aa.aula_numero, aa.faixa_global,
               aa.criado_em, aa.atualizado_em,
               COALESCE(u.nome, '') AS professor_nome,
               COALESCE(u.email, '') AS professor_email
        FROM aulas_atividade_professores aa
        INNER JOIN usuarios u ON u.id = aa.professor_usuario_id
        {where}
        ORDER BY aa.ano_letivo DESC, u.nome COLLATE NOCASE ASC,
                 aa.dia_semana IS NULL DESC, aa.dia_semana ASC,
                 aa.faixa_global ASC, aa.id ASC
        """,
        list(params or []),
    )
    return [_map(row) for row in cursor.fetchall()]


def list_teacher_activities(*, ano_letivo=None, professor_id=None, dia_semana=None):
    filters, params = [], []
    if ano_letivo is not None:
        filters.append("aa.ano_letivo = ?")
        params.append(int(ano_letivo))
    if professor_id is not None:
        filters.append("aa.professor_usuario_id = ?")
        params.append(int(professor_id))
    if str(dia_semana or "").strip():
        filters.append("(UPPER(aa.dia_semana) = ? OR aa.dia_semana IS NULL)")
        params.append(str(dia_semana).strip().upper())
    with closing(get_connection()) as conn:
        return _query(conn.cursor(), filters, params)


def get_teacher_activity(record_id: int):
    with closing(get_connection()) as conn:
        items = _query(conn.cursor(), ["aa.id = ?"], [int(record_id)])
    return items[0] if items else None


def create_teacher_activity(*, ano_letivo: int, professor_usuario_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """INSERT INTO aulas_atividade_professores (
                   ano_letivo, professor_usuario_id, dia_semana,
                   aula_numero, faixa_global, criado_em, atualizado_em
               ) VALUES (?, ?, NULL, NULL, NULL, datetime('now'), datetime('now'))""",
            (int(ano_letivo), int(professor_usuario_id)),
        )
        record_id = int(cursor.lastrowid)
        conn.commit()
    return get_teacher_activity(record_id)


def update_teacher_activity(
    *, registro_id: int, dia_semana: str | None,
    aula_numero: int | None, faixa_global: int | None
):
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        current = cursor.execute(
            """SELECT id, ano_letivo, professor_usuario_id
               FROM aulas_atividade_professores WHERE id = ?""",
            (int(registro_id),),
        ).fetchone()
        if not current:
            return None

        weekday = str(dia_semana or "").strip().upper() or None
        lesson = int(aula_numero or 0) or None
        slot = int(faixa_global or 0) or None
        if weekday and _teacher_conflict(
            cursor,
            year=current["ano_letivo"],
            teacher_id=current["professor_usuario_id"],
            weekday=weekday,
            slot=slot,
        ):
            raise IntegrityError("idx_aulas_atividade_professor_slot")

        cursor.execute(
            """UPDATE aulas_atividade_professores
               SET dia_semana = ?, aula_numero = ?, faixa_global = ?,
                   atualizado_em = datetime('now')
               WHERE id = ?""",
            (weekday, lesson, slot, int(registro_id)),
        )
        conn.commit()
    return get_teacher_activity(registro_id)


def delete_teacher_activity(record_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "DELETE FROM aulas_atividade_professores WHERE id = ?",
            (int(record_id),),
        )
        conn.commit()
        return cursor.rowcount > 0
