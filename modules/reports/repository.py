from __future__ import annotations

import database


def get_management_dashboard(data_inicio: str, data_fim: str) -> dict:
    return database.gerar_dashboard_relatorios(data_inicio, data_fim)


def get_attachments_report(data_inicio: str, data_fim: str) -> dict:
    return database.gerar_relatorio_anexos(data_inicio, data_fim)


def list_teacher_recipients() -> list[dict]:
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nome, email
            FROM usuarios
            WHERE LOWER(COALESCE(perfil, '')) = 'professor'
              AND COALESCE(ativo, 1) = 1
            ORDER BY nome ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_teacher(professor_id: int) -> dict | None:
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nome, email, perfil, cargo
            FROM usuarios
            WHERE id = ?
              AND LOWER(COALESCE(perfil, '')) = 'professor'
              AND COALESCE(ativo, 1) = 1
            """,
            (int(professor_id),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_teacher_printing_summary(professor_id: int, data_inicio: str, data_fim: str) -> dict:
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(j.id) AS total_jobs,
                COALESCE(SUM(j.paginas_totais), 0) AS total_paginas,
                COALESCE(AVG(j.paginas_totais), 0) AS media_paginas
            FROM jobs j
            WHERE j.usuario_id = ?
              AND j.status IN (?, ?)
              AND date(j.criado_em) >= ?
              AND date(j.criado_em) <= ?
            """,
            (
                int(professor_id),
                database.STATUS_CONCLUIDO,
                database.STATUS_FINALIZADO_LEGADO,
                data_inicio,
                data_fim,
            ),
        )
        row = dict(cursor.fetchone() or {})
        cursor.execute(
            """
            SELECT arquivo, paginas_totais, copias, criado_em, tags_json
            FROM jobs
            WHERE usuario_id = ?
              AND status IN (?, ?)
              AND date(criado_em) >= ?
              AND date(criado_em) <= ?
            ORDER BY criado_em DESC, id DESC
            LIMIT 12
            """,
            (
                int(professor_id),
                database.STATUS_CONCLUIDO,
                database.STATUS_FINALIZADO_LEGADO,
                data_inicio,
                data_fim,
            ),
        )
        recentes = [dict(item) for item in cursor.fetchall()]
        return {
            "total_jobs": int(row.get("total_jobs") or 0),
            "total_paginas": int(row.get("total_paginas") or 0),
            "media_paginas": round(float(row.get("media_paginas") or 0), 1),
            "recentes": recentes,
        }
    finally:
        conn.close()


def get_teacher_resource_summary(professor_id: int, data_inicio: str, data_fim: str) -> dict:
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(a.id) AS total_reservas,
                COUNT(DISTINCT a.recurso_id) AS recursos_utilizados
            FROM agendamentos a
            WHERE a.usuario_id = ?
              AND a.status = ?
              AND a.data >= ?
              AND a.data <= ?
            """,
            (int(professor_id), database.STATUS_AGENDAMENTO_ATIVO, data_inicio, data_fim),
        )
        row = dict(cursor.fetchone() or {})
        cursor.execute(
            """
            SELECT
                a.data,
                a.turno,
                a.aula,
                a.turma,
                a.tema_aula,
                r.nome AS recurso_nome
            FROM agendamentos a
            JOIN recursos r ON r.id = a.recurso_id
            WHERE a.usuario_id = ?
              AND a.status = ?
              AND a.data >= ?
              AND a.data <= ?
            ORDER BY a.data DESC, a.turno ASC, CAST(a.aula AS INTEGER) ASC
            LIMIT 12
            """,
            (int(professor_id), database.STATUS_AGENDAMENTO_ATIVO, data_inicio, data_fim),
        )
        recentes = [dict(item) for item in cursor.fetchall()]
        return {
            "total_reservas": int(row.get("total_reservas") or 0),
            "recursos_utilizados": int(row.get("recursos_utilizados") or 0),
            "recentes": recentes,
        }
    finally:
        conn.close()
