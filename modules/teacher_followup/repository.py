import json

from db._proxy import get_database_attr


def _get_connection():
    return get_database_attr("get_connection")()


def _active_user_clause(alias: str = "u") -> str:
    return f"(COALESCE({alias}.ativo, 1) = 1)"


def _teacher_clause(alias: str = "u") -> str:
    return f"""
        (
            UPPER(COALESCE({alias}.cargo, '')) = 'PROFESSOR'
            OR (
                TRIM(COALESCE({alias}.cargo, '')) = ''
                AND LOWER(COALESCE({alias}.perfil, '')) = 'professor'
            )
        )
    """


def _decode_text_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    items = []
    for item in parsed:
        text = str(item or "").strip()
        if text and text not in items:
            items.append(text)
    return items


def _map_teacher(row) -> dict:
    item = dict(row)
    item["id"] = int(item["id"])
    item["disciplines"] = _decode_text_list(item.pop("disciplinas_json", "[]"))
    return item


def list_teachers(search: str = "", limit: int = 200) -> list[dict]:
    term = str(search or "").strip().lower()
    params: list[object] = []
    search_sql = ""

    if term:
        like = f"%{term}%"
        search_sql = """
            AND (
                LOWER(COALESCE(u.nome, '')) LIKE ?
                OR LOWER(COALESCE(d.nome, '')) LIKE ?
                OR LOWER(COALESCE(pc.disciplinas, '')) LIKE ?
            )
        """
        params.extend([like, like, like])

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                u.id,
                u.nome,
                u.email,
                COALESCE(pc.disciplinas, '[]') AS disciplinas_json,
                GROUP_CONCAT(DISTINCT d.nome) AS disciplinas_atribuicoes
            FROM usuarios u
            LEFT JOIN professores_carga pc ON pc.usuario_id = u.id
            LEFT JOIN professores_turmas_disciplinas ptd ON ptd.professor_usuario_id = u.id
            LEFT JOIN disciplinas d ON d.id = ptd.disciplina_id
            WHERE {_active_user_clause("u")}
              AND {_teacher_clause("u")}
              {search_sql}
            GROUP BY u.id
            ORDER BY u.nome COLLATE NOCASE ASC, u.id ASC
            LIMIT ?
            """,
            [*params, max(1, int(limit or 200))],
        ).fetchall()
    finally:
        conn.close()

    teachers = []
    for row in rows:
        item = _map_teacher(row)
        for discipline in str(item.pop("disciplinas_atribuicoes") or "").split(","):
            discipline = discipline.strip()
            if discipline and discipline not in item["disciplines"]:
                item["disciplines"].append(discipline)
        teachers.append(item)
    return teachers


def get_teacher(teacher_id: int) -> dict | None:
    teachers = list_teachers(limit=1000)
    for teacher in teachers:
        if int(teacher["id"]) == int(teacher_id):
            return teacher
    return None


def count_records_by_teacher() -> dict[int, dict]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                teacher_id,
                SUM(CASE WHEN record_type = 'positive' THEN 1 ELSE 0 END) AS positives,
                SUM(CASE WHEN record_type = 'attention' THEN 1 ELSE 0 END) AS attention_points,
                COUNT(*) AS total
            FROM teacher_followup_records
            GROUP BY teacher_id
            """
        ).fetchall()
    finally:
        conn.close()
    return {int(row["teacher_id"]): dict(row) for row in rows}


def list_records(teacher_id: int, record_type: str | None = None) -> list[dict]:
    params: list[object] = [int(teacher_id)]
    type_sql = ""
    if record_type:
        type_sql = "AND r.record_type = ?"
        params.append(str(record_type).strip())

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                r.*,
                COALESCE(author.nome, '') AS created_by_name
            FROM teacher_followup_records r
            LEFT JOIN usuarios author ON author.id = r.created_by_user_id
            WHERE r.teacher_id = ?
              {type_sql}
            ORDER BY r.record_date DESC, r.id DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def create_record(
    *,
    teacher_id: int,
    record_type: str,
    category: str,
    description: str,
    record_date: str,
    created_by_user_id: int | None,
) -> dict:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO teacher_followup_records (
                teacher_id,
                record_type,
                category,
                description,
                record_date,
                created_by_user_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                int(teacher_id),
                record_type,
                category,
                description,
                record_date,
                created_by_user_id,
            ),
        )
        record_id = int(cursor.lastrowid)
        conn.commit()
        row = conn.execute(
            """
            SELECT
                r.*,
                COALESCE(author.nome, '') AS created_by_name
            FROM teacher_followup_records r
            LEFT JOIN usuarios author ON author.id = r.created_by_user_id
            WHERE r.id = ?
            """,
            (record_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row)


def list_apc_deadline_rows(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    period_filters = []
    params_all: list[object] = []
    params_selected: list[object] = []
    if date_from:
        period_filters.append("p.data_referencia >= ?")
        params_all.append(date_from)
        params_selected.append(date_from)
    if date_to:
        period_filters.append("p.data_referencia <= ?")
        params_all.append(date_to)
        params_selected.append(date_to)
    period_where = f"AND {' AND '.join(period_filters)}" if period_filters else ""

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"""
            WITH envios_resumo AS (
                SELECT
                    periodo_id,
                    professor_usuario_id,
                    COALESCE(turma_id, 0) AS turma_id,
                    COALESCE(disciplina_id, 0) AS disciplina_id,
                    MIN(COALESCE(NULLIF(TRIM(primeiro_envio_em), ''), enviado_em)) AS delivered_at,
                    MAX(COALESCE(review_status, 'PENDENTE')) AS delivery_status
                FROM apc_envios
                GROUP BY
                    periodo_id,
                    professor_usuario_id,
                    COALESCE(turma_id, 0),
                    COALESCE(disciplina_id, 0)
            ),
            envios_professor_periodo AS (
                SELECT
                    periodo_id,
                    professor_usuario_id,
                    MIN(delivered_at) AS delivered_at,
                    MAX(delivery_status) AS delivery_status
                FROM envios_resumo
                GROUP BY periodo_id, professor_usuario_id
            )
            SELECT
                u.id AS teacher_id,
                p.id AS period_id,
                'all_teachers' AS audience,
                0 AS turma_id,
                0 AS disciplina_id,
                p.titulo,
                p.data_referencia,
                p.prazo_envio,
                e.delivered_at,
                e.delivery_status
            FROM usuarios u
            JOIN apc_periodos p ON p.publico_alvo = 'TODOS_PROFESSORES'
            LEFT JOIN envios_professor_periodo e
                ON e.periodo_id = p.id
               AND e.professor_usuario_id = u.id
            WHERE {_active_user_clause("u")}
              AND {_teacher_clause("u")}
              {period_where}

            UNION ALL

            SELECT
                ad.professor_usuario_id AS teacher_id,
                p.id AS period_id,
                'selected_teacher' AS audience,
                COALESCE(ad.turma_id, 0) AS turma_id,
                COALESCE(ad.disciplina_id, 0) AS disciplina_id,
                p.titulo,
                p.data_referencia,
                p.prazo_envio,
                e.delivered_at,
                e.delivery_status
            FROM apc_periodo_destinatarios ad
            JOIN apc_periodos p ON p.id = ad.periodo_id
            LEFT JOIN envios_resumo e
                ON e.periodo_id = ad.periodo_id
               AND e.professor_usuario_id = ad.professor_usuario_id
               AND COALESCE(e.turma_id, 0) = COALESCE(ad.turma_id, 0)
               AND COALESCE(e.disciplina_id, 0) = COALESCE(ad.disciplina_id, 0)
            WHERE 1 = 1
              {period_where}
            """,
            [*params_all, *params_selected],
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
