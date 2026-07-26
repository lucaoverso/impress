from db.core import get_connection


def email_belongs_to_another_user(email: str, user_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM usuarios WHERE LOWER(email) = LOWER(?) AND id != ?",
            (email, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_profile_identity(user_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nome, email, perfil, cargo, data_nascimento
            FROM usuarios
            WHERE id = ? AND ativo = 1
            """,
            (int(user_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_teacher_links(user_id: int, school_year: int):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            WITH vinculos AS (
                SELECT ptd.turma_id, ptd.disciplina_id
                FROM professores_turmas_disciplinas ptd
                WHERE ptd.professor_usuario_id = ?

                UNION

                SELECT he.turma_id, he.disciplina_id
                FROM horarios_escolares he
                WHERE he.professor_usuario_id = ? AND he.ano_letivo = ?
            )
            SELECT DISTINCT
                t.id AS turma_id,
                t.nome AS turma_nome,
                d.id AS disciplina_id,
                d.nome AS disciplina_nome
            FROM vinculos v
            INNER JOIN turmas t ON t.id = v.turma_id AND t.ativo = 1
            INNER JOIN disciplinas d ON d.id = v.disciplina_id AND d.ativo = 1
            ORDER BY
                t.nome COLLATE NOCASE,
                d.nome COLLATE NOCASE,
                t.id,
                d.id
            """,
            (int(user_id), int(user_id), int(school_year)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_schedule_slots():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT aula_numero, ordem_visual, nome, horario_inicio, horario_fim
            FROM configuracao_aulas
            WHERE ativo = 1 AND tipo = 'AULA' AND aula_numero IS NOT NULL
            ORDER BY ordem_visual, aula_numero, id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_teacher_schedule(user_id: int, school_year: int):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                he.id,
                he.dia_semana,
                he.aula_numero,
                COALESCE(NULLIF(he.faixa_global, 0), he.aula_numero) AS faixa_global,
                he.turma_id,
                t.nome AS turma_nome,
                COALESCE(t.turno, '') AS turno,
                he.disciplina_id,
                d.nome AS disciplina_nome
            FROM horarios_escolares he
            INNER JOIN turmas t ON t.id = he.turma_id AND t.ativo = 1
            INNER JOIN disciplinas d ON d.id = he.disciplina_id AND d.ativo = 1
            WHERE he.professor_usuario_id = ? AND he.ano_letivo = ?
            ORDER BY
                he.dia_semana,
                faixa_global,
                he.aula_numero,
                t.nome COLLATE NOCASE,
                d.nome COLLATE NOCASE
            """,
            (int(user_id), int(school_year)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_teacher_student_supports(user_id: int, school_year: int):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            WITH turmas_professor AS (
                SELECT ptd.turma_id
                FROM professores_turmas_disciplinas ptd
                INNER JOIN turmas t ON t.id = ptd.turma_id AND t.ativo = 1
                INNER JOIN disciplinas d ON d.id = ptd.disciplina_id AND d.ativo = 1
                WHERE ptd.professor_usuario_id = ?

                UNION

                SELECT he.turma_id
                FROM horarios_escolares he
                INNER JOIN turmas t ON t.id = he.turma_id AND t.ativo = 1
                WHERE he.professor_usuario_id = ? AND he.ano_letivo = ?
            )
            SELECT
                e.id AS estudante_id,
                e.nome AS estudante_nome,
                e.turma_id,
                t.nome AS turma_nome,
                COALESCE(l.recomendacoes_pedagogicas, '') AS recomendacoes_pedagogicas,
                COALESCE(a.nome, '') AS apoio_nome
            FROM estudantes e
            INNER JOIN turmas_professor tp ON tp.turma_id = e.turma_id
            INNER JOIN turmas t ON t.id = e.turma_id AND t.ativo = 1
            LEFT JOIN estudante_laudos l ON l.estudante_id = e.id AND l.ativo = 1
            LEFT JOIN estudante_laudo_apoios la ON la.laudo_id = l.id
            LEFT JOIN estudante_apoios_catalogo a ON a.id = la.apoio_id AND a.ativo = 1
            WHERE e.ativo = 1
              AND (
                  e.possui_necessidade_especial = 1
                  OR EXISTS (
                      SELECT 1
                      FROM estudante_laudos laudo_ativo
                      WHERE laudo_ativo.estudante_id = e.id AND laudo_ativo.ativo = 1
                  )
              )
            ORDER BY
                t.nome COLLATE NOCASE,
                e.nome COLLATE NOCASE,
                e.id,
                a.nome COLLATE NOCASE
            """,
            (int(user_id), int(user_id), int(school_year)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_recent_apc_submissions(user_id: int, limit: int = 3):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                ae.id,
                COALESCE(NULLIF(ae.arquivo_nome_cliente, ''), ae.arquivo_nome_original) AS arquivo,
                COALESCE(t.nome, '') AS turma_nome,
                COALESCE(d.nome, '') AS disciplina_nome,
                COALESCE(ae.enviado_em, '') AS enviado_em,
                COALESCE(NULLIF(ae.review_status, ''), 'PENDENTE') AS status
            FROM apc_envios ae
            LEFT JOIN turmas t ON t.id = ae.turma_id
            LEFT JOIN disciplinas d ON d.id = ae.disciplina_id
            WHERE ae.professor_usuario_id = ?
            ORDER BY ae.enviado_em DESC, ae.id DESC
            LIMIT ?
            """,
            (int(user_id), max(int(limit), 0)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_recent_print_jobs(user_id: int, limit: int = 3):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, arquivo, copias, paginas_totais, criado_em, status
            FROM jobs
            WHERE usuario_id = ?
            ORDER BY criado_em DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), max(int(limit), 0)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_upcoming_bookings(user_id: int, limit: int = 3):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                a.id,
                r.nome AS recurso_nome,
                COALESCE(r.tipo, '') AS recurso_tipo,
                a.data,
                COALESCE(a.aula, '') AS aula,
                COALESCE(ca.horario_inicio, '') AS horario_inicio,
                COALESCE(ca.horario_fim, '') AS horario_fim,
                COALESCE(a.turma, '') AS turma,
                COALESCE(a.tema_aula, '') AS tema_aula,
                a.status
            FROM agendamentos a
            INNER JOIN recursos r ON r.id = a.recurso_id
            LEFT JOIN configuracao_aulas ca
                ON ca.aula_numero = COALESCE(NULLIF(a.faixa_global, 0), CAST(a.aula AS INTEGER))
                AND ca.ativo = 1
            WHERE a.usuario_id = ?
              AND a.status = 'ATIVO'
              AND a.data >= date('now', 'localtime')
              AND (
                  a.data > date('now', 'localtime')
                  OR COALESCE(NULLIF(ca.horario_fim, ''), '23:59') >= time('now', 'localtime')
              )
            ORDER BY
                a.data,
                COALESCE(NULLIF(a.faixa_global, 0), CAST(a.aula AS INTEGER)),
                a.id
            LIMIT ?
            """,
            (int(user_id), max(int(limit), 0)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_profile(
    user_id: int,
    name: str,
    email: str,
    *,
    password_hash: str | None = None,
    nt_hash: str | None = None,
) -> bool:
    conn = get_connection()
    try:
        if password_hash and nt_hash:
            cursor = conn.execute(
                "UPDATE usuarios SET nome = ?, email = ?, senha_hash = ?, nt_hash = ? WHERE id = ?",
                (name, email, password_hash, nt_hash, user_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE usuarios SET nome = ?, email = ? WHERE id = ?",
                (name, email, user_id),
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
