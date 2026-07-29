from contextlib import closing

from db.core import get_connection
from modules.admin.classes.repository import listar_turmas_ativas
from modules.admin.resources.repository import buscar_recurso_por_id, listar_recursos_ativos
from modules.scheduling.models import SchedulingReservation, SchedulingResource

STATUS_ACTIVE = "ATIVO"
STATUS_CANCELLED = "CANCELADO"
USER_ROLE_TEACHER = "PROFESSOR"


def get_reservation(agendamento_id: int):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM agendamentos WHERE id = ?",
            (int(agendamento_id),),
        ).fetchone()
    return SchedulingReservation.from_dict(dict(row) if row else None)


def cancel_reservation(agendamento_id: int):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE agendamentos
            SET status = ?, cancelado_em = datetime('now')
            WHERE id = ? AND status = ?
            """,
            (STATUS_CANCELLED, int(agendamento_id), STATUS_ACTIVE),
        )
        conn.commit()
        return cursor.rowcount > 0


def count_active_reservations_in_slot(recurso_id: int, data: str, faixa_global: int):
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM agendamentos
            WHERE recurso_id = ? AND data = ? AND faixa_global = ? AND status = ?
            """,
            (int(recurso_id), data, int(faixa_global), STATUS_ACTIVE),
        ).fetchone()
    return int(row["total"] if row else 0)


def create_reservation(
    *,
    recurso_id: int,
    usuario_id: int,
    data: str,
    turno: str,
    aula: str,
    faixa_global: int,
    turma: str,
    tema_aula: str,
    observacao: str = "",
):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO agendamentos (
                recurso_id, usuario_id, data, turno, aula, faixa_global,
                turma, tema_aula, observacao, status, criado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                int(recurso_id),
                int(usuario_id),
                data,
                turno,
                aula,
                int(faixa_global),
                turma,
                tema_aula,
                observacao,
                STATUS_ACTIVE,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_reservations(
    *,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    recurso_id: int | None = None,
    usuario_id: int | None = None,
    incluir_cancelados: bool = False,
):
    query = """
        SELECT
            a.id, a.recurso_id, r.nome AS recurso_nome, r.tipo AS recurso_tipo,
            a.usuario_id, u.nome AS professor_nome, a.data, a.turno, a.aula,
            a.faixa_global, a.turma, COALESCE(a.tema_aula, '') AS tema_aula,
            COALESCE(a.observacao, '') AS observacao, a.status,
            a.criado_em, a.cancelado_em
        FROM agendamentos a
        JOIN recursos r ON r.id = a.recurso_id
        JOIN usuarios u ON u.id = a.usuario_id
        WHERE 1 = 1
    """
    params = []
    if not incluir_cancelados:
        query += " AND a.status = ?"
        params.append(STATUS_ACTIVE)
    if data_inicio:
        query += " AND a.data >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND a.data <= ?"
        params.append(data_fim)
    if recurso_id:
        query += " AND a.recurso_id = ?"
        params.append(recurso_id)
    if usuario_id:
        query += " AND a.usuario_id = ?"
        params.append(usuario_id)
    query += " ORDER BY a.data ASC, CAST(a.faixa_global AS INTEGER) ASC, r.nome ASC"

    with closing(get_connection()) as conn:
        rows = conn.execute(query, params).fetchall()
    return [SchedulingReservation.from_dict(dict(row)) for row in rows]


def get_resource(recurso_id: int):
    return SchedulingResource.from_dict(buscar_recurso_por_id(recurso_id))


def list_active_resources():
    return [SchedulingResource.from_dict(item) for item in listar_recursos_ativos()]


def list_active_classes():
    return listar_turmas_ativas()


def _map_lesson_configuration(row) -> dict:
    item = dict(row)
    lesson_number = item.get("aula_numero")
    return {
        "id": int(item["id"]),
        "ordem_visual": int(item.get("ordem_visual") or 0),
        "tipo": str(item.get("tipo") or "AULA").strip().upper(),
        "aula_numero": int(lesson_number) if lesson_number not in (None, "") else None,
        "nome": str(item.get("nome") or "").strip(),
        "horario_inicio": str(item.get("horario_inicio") or "").strip(),
        "horario_fim": str(item.get("horario_fim") or "").strip(),
        "ativo": bool(int(item.get("ativo", 1) or 0)),
        "criado_em": str(item.get("criado_em") or "").strip(),
        "atualizado_em": str(item.get("atualizado_em") or "").strip(),
    }


def list_lesson_configurations(*, include_inactive: bool = True):
    query = """
        SELECT id, ordem_visual, tipo, aula_numero, nome, horario_inicio,
               horario_fim, ativo, criado_em, atualizado_em
        FROM configuracao_aulas
    """
    if not include_inactive:
        query += " WHERE ativo = 1"
    query += " ORDER BY ordem_visual ASC, id ASC"
    with closing(get_connection()) as conn:
        rows = conn.execute(query).fetchall()
    return [_map_lesson_configuration(row) for row in rows]


def get_lesson_configuration(configuration_id: int):
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT id, ordem_visual, tipo, aula_numero, nome, horario_inicio,
                   horario_fim, ativo, criado_em, atualizado_em
            FROM configuracao_aulas WHERE id = ?
            """,
            (int(configuration_id),),
        ).fetchone()
    return _map_lesson_configuration(row) if row else None


def create_lesson_configuration(
    *,
    visual_order: int,
    entry_type: str,
    lesson_number: int | None,
    name: str,
    start_time: str,
    end_time: str,
    active: bool = True,
):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO configuracao_aulas (
                ordem_visual, tipo, aula_numero, nome, horario_inicio,
                horario_fim, ativo, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                int(visual_order),
                str(entry_type).strip().upper(),
                int(lesson_number) if lesson_number not in (None, "") else None,
                str(name or "").strip(),
                str(start_time or "").strip(),
                str(end_time or "").strip(),
                1 if active else 0,
            ),
        )
        configuration_id = int(cursor.lastrowid)
        conn.commit()
    return get_lesson_configuration(configuration_id)


def update_lesson_configuration(
    *,
    configuration_id: int,
    visual_order: int,
    entry_type: str,
    lesson_number: int | None,
    name: str,
    start_time: str,
    end_time: str,
    active: bool,
):
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE configuracao_aulas
            SET ordem_visual = ?, tipo = ?, aula_numero = ?, nome = ?,
                horario_inicio = ?, horario_fim = ?, ativo = ?,
                atualizado_em = datetime('now')
            WHERE id = ?
            """,
            (
                int(visual_order),
                str(entry_type).strip().upper(),
                int(lesson_number) if lesson_number not in (None, "") else None,
                str(name or "").strip(),
                str(start_time or "").strip(),
                str(end_time or "").strip(),
                1 if active else 0,
                int(configuration_id),
            ),
        )
        conn.commit()
        changed = cursor.rowcount > 0
    return get_lesson_configuration(configuration_id) if changed else None


def list_scheduling_teachers():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, nome, email
            FROM usuarios
            WHERE (
                    UPPER(COALESCE(cargo, '')) = ?
                    OR (TRIM(COALESCE(cargo, '')) = ''
                        AND LOWER(COALESCE(perfil, '')) = 'professor')
                  )
              AND (COALESCE(ativo, 1) = 1
                   OR LOWER(CAST(COALESCE(ativo, 1) AS TEXT)) = 'true')
            ORDER BY nome COLLATE NOCASE ASC
            """,
            (USER_ROLE_TEACHER,),
        ).fetchall()
    return [dict(row) for row in rows]
