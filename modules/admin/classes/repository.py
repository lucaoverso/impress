import importlib


def _get_connection():
    return importlib.import_module("database").get_connection()


def listar_turmas(incluir_inativas: bool = False):
    conn = _get_connection()
    query = """
        SELECT id, nome, turno, aula_inicial, aula_final, quantidade_estudantes, ativo, criado_em
        FROM turmas
    """
    if not incluir_inativas:
        query += " WHERE ativo = 1"
    query += " ORDER BY nome COLLATE NOCASE ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def listar_turmas_ativas():
    return listar_turmas(incluir_inativas=False)


def buscar_turma_por_id(turma_id: int):
    conn = _get_connection()
    row = conn.execute(
        """SELECT id, nome, turno, aula_inicial, aula_final, quantidade_estudantes, ativo, criado_em
           FROM turmas WHERE id = ?""",
        (int(turma_id),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_turma_por_nome(nome: str, incluir_inativas: bool = True):
    nome_limpo = str(nome or "").strip()
    if not nome_limpo:
        return None
    conn = _get_connection()
    query = """SELECT id, nome, turno, aula_inicial, aula_final, quantidade_estudantes, ativo, criado_em
               FROM turmas WHERE nome = ? COLLATE NOCASE"""
    if not incluir_inativas:
        query += " AND ativo = 1"
    row = conn.execute(query + " ORDER BY id ASC LIMIT 1", (nome_limpo,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _class_values(turno, quantidade_estudantes, aula_inicial, aula_final):
    from modules.scheduling.lesson_config import lesson_window_from_turn

    turno_limpo = str(turno or "").strip().upper()
    inicio_padrao, fim_padrao = lesson_window_from_turn(turno_limpo)
    inicio = int(aula_inicial or 0) if aula_inicial is not None else inicio_padrao
    fim = int(aula_final or 0) if aula_final is not None else fim_padrao
    quantidade = int(quantidade_estudantes or 0)
    if inicio <= 0 or fim < inicio:
        raise ValueError("Janela de aulas da turma é inválida.")
    if quantidade < 0:
        raise ValueError("Quantidade de estudantes não pode ser negativa.")
    return turno_limpo, inicio, fim, quantidade


def criar_turma(nome, turno="", quantidade_estudantes=0, aula_inicial=None, aula_final=None):
    nome_limpo = str(nome or "").strip()
    if not nome_limpo:
        raise ValueError("Nome da turma é obrigatório.")
    turno_limpo, inicio, fim, quantidade = _class_values(
        turno, quantidade_estudantes, aula_inicial, aula_final
    )
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO turmas
           (nome, turno, aula_inicial, aula_final, quantidade_estudantes, ativo, criado_em)
           VALUES (?, ?, ?, ?, ?, 1, datetime('now'))""",
        (nome_limpo, turno_limpo, inicio, fim, quantidade),
    )
    turma_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return turma_id


def atualizar_turma_dados(
    turma_id, turno, quantidade_estudantes, aula_inicial=None, aula_final=None
):
    turno_limpo, inicio, fim, quantidade = _class_values(
        turno, quantidade_estudantes, aula_inicial, aula_final
    )
    conn = _get_connection()
    cursor = conn.execute(
        """UPDATE turmas
           SET turno = ?, aula_inicial = ?, aula_final = ?, quantidade_estudantes = ?
           WHERE id = ?""",
        (turno_limpo, inicio, fim, quantidade, turma_id),
    )
    alterado = cursor.rowcount > 0
    if alterado:
        conn.execute(
            """UPDATE horarios_escolares
               SET faixa_global = CAST(COALESCE(aula_numero, 0) AS INTEGER)
               WHERE turma_id = ?""",
            (int(turma_id),),
        )
    conn.commit()
    conn.close()
    return alterado


def atualizar_status_turma(turma_id: int, ativo: bool):
    conn = _get_connection()
    cursor = conn.execute("UPDATE turmas SET ativo = ? WHERE id = ?", (1 if ativo else 0, turma_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
