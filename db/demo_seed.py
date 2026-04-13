from __future__ import annotations

import argparse
import importlib
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from services.preconselho_service import gerar_texto_pre_conselho_individual

DEMO_SUFFIX = " - Demo"
DEMO_PASSWORD = "demo123"
COORDENACAO_PASSWORD = "coord123"
ADMIN_PASSWORD = "admin123"
PROFESSOR_PASSWORD = "prof123"
MES_ATUAL_FMT = "%Y-%m"
OBSERVACAO_AGENDAMENTO = "Reserva criada para visualizacao local."

DEMO_USUARIOS = (
    {
        "nome": "Ana Ribeiro",
        "email": "ana.demo@escola",
        "perfil": "professor",
        "cargo": "PROFESSOR",
        "senha": DEMO_PASSWORD,
        "data_nascimento": "1990-03-14",
    },
    {
        "nome": "Bruno Costa",
        "email": "bruno.demo@escola",
        "perfil": "professor",
        "cargo": "PROFESSOR",
        "senha": DEMO_PASSWORD,
        "data_nascimento": "1988-08-09",
    },
    {
        "nome": "Carla Mendes",
        "email": "carla.demo@escola",
        "perfil": "professor",
        "cargo": "PROFESSOR",
        "senha": DEMO_PASSWORD,
        "data_nascimento": "1992-11-22",
    },
    {
        "nome": "Mariana Souza",
        "email": "coordenacao.demo@escola",
        "perfil": "coordenador",
        "cargo": "COORDENADOR",
        "senha": COORDENACAO_PASSWORD,
        "data_nascimento": "1985-05-30",
    },
)

DEMO_TURMAS = (
    {"nome": f"7 Ano A{DEMO_SUFFIX}", "turno": "MATUTINO", "quantidade_estudantes": 28},
    {"nome": f"8 Ano B{DEMO_SUFFIX}", "turno": "VESPERTINO", "quantidade_estudantes": 31},
    {"nome": f"1 EM A{DEMO_SUFFIX}", "turno": "MATUTINO", "quantidade_estudantes": 34},
)

DEMO_DISCIPLINAS = (
    {"nome": f"Portugues{DEMO_SUFFIX}", "aulas_semanais": 5},
    {"nome": f"Matematica{DEMO_SUFFIX}", "aulas_semanais": 5},
    {"nome": f"Ciencias{DEMO_SUFFIX}", "aulas_semanais": 4},
    {"nome": f"Historia{DEMO_SUFFIX}", "aulas_semanais": 3},
    {"nome": f"Biologia{DEMO_SUFFIX}", "aulas_semanais": 3},
)

DEMO_ESTUDANTES = {
    f"7 Ano A{DEMO_SUFFIX}": (
        "Ana Clara Santos",
        "Pedro Henrique Lima",
        "Laura Beatriz Souza",
        "Gabriel Oliveira",
    ),
    f"8 Ano B{DEMO_SUFFIX}": (
        "Mariana Costa",
        "Joao Vitor Alves",
        "Sophia Fernandes",
        "Lucas Martins",
    ),
    f"1 EM A{DEMO_SUFFIX}": (
        "Camila Rocha",
        "Rafael Gomes",
        "Isabela Nunes",
        "Thiago Moreira",
    ),
}

DEMO_ATRIBUICOES = (
    {
        "email": "professor@escola",
        "turma": f"7 Ano A{DEMO_SUFFIX}",
        "disciplina": f"Portugues{DEMO_SUFFIX}",
        "carga_horaria": 5,
    },
    {
        "email": "ana.demo@escola",
        "turma": f"7 Ano A{DEMO_SUFFIX}",
        "disciplina": f"Matematica{DEMO_SUFFIX}",
        "carga_horaria": 5,
    },
    {
        "email": "ana.demo@escola",
        "turma": f"8 Ano B{DEMO_SUFFIX}",
        "disciplina": f"Matematica{DEMO_SUFFIX}",
        "carga_horaria": 5,
    },
    {
        "email": "bruno.demo@escola",
        "turma": f"8 Ano B{DEMO_SUFFIX}",
        "disciplina": f"Historia{DEMO_SUFFIX}",
        "carga_horaria": 3,
    },
    {
        "email": "carla.demo@escola",
        "turma": f"7 Ano A{DEMO_SUFFIX}",
        "disciplina": f"Ciencias{DEMO_SUFFIX}",
        "carga_horaria": 4,
    },
    {
        "email": "carla.demo@escola",
        "turma": f"1 EM A{DEMO_SUFFIX}",
        "disciplina": f"Biologia{DEMO_SUFFIX}",
        "carga_horaria": 3,
    },
)

DEMO_PROFESSORES_CARGA = (
    {
        "email": "professor@escola",
        "aulas_semanais": 12,
        "turmas": [f"7 Ano A{DEMO_SUFFIX}"],
        "disciplinas": [f"Portugues{DEMO_SUFFIX}"],
    },
    {
        "email": "ana.demo@escola",
        "aulas_semanais": 18,
        "turmas": [f"7 Ano A{DEMO_SUFFIX}", f"8 Ano B{DEMO_SUFFIX}"],
        "disciplinas": [f"Matematica{DEMO_SUFFIX}"],
    },
    {
        "email": "bruno.demo@escola",
        "aulas_semanais": 16,
        "turmas": [f"8 Ano B{DEMO_SUFFIX}"],
        "disciplinas": [f"Historia{DEMO_SUFFIX}"],
    },
    {
        "email": "carla.demo@escola",
        "aulas_semanais": 14,
        "turmas": [f"7 Ano A{DEMO_SUFFIX}", f"1 EM A{DEMO_SUFFIX}"],
        "disciplinas": [f"Ciencias{DEMO_SUFFIX}", f"Biologia{DEMO_SUFFIX}"],
    },
)

DEMO_PCPI_DESCRICOES = (
    "Planejamento de apoio para Matematica da turma demo.",
    "Impressao de roteiros avaliativos para visualizacao local.",
    "Orientacao docente sobre uso de recursos em aula pratica.",
)

DEMO_JOB_ARQUIVOS = (
    "demo-roteiro-portugues.pdf",
    "demo-lista-matematica.pdf",
    "demo-simulado-interdisciplinar.pdf",
)


def _configure_db_path_env(db_path: str | None) -> None:
    if db_path:
        os.environ["DB_PATH"] = str(Path(db_path).expanduser())


def _import_database_module(*, reload_module: bool = False):
    if "database" in sys.modules:
        if reload_module:
            return importlib.reload(sys.modules["database"])
        return sys.modules["database"]
    return importlib.import_module("database")


def _get_database(db_path: str | None = None):
    _configure_db_path_env(db_path)
    return _import_database_module(reload_module=db_path is not None)


def _atualizar_status_ativo_por_email(database, email: str) -> None:
    conn = database.get_connection()
    try:
        conn.execute(
            """
            UPDATE usuarios
            SET ativo = 1
            WHERE email = ?
            """,
            (email,),
        )
        conn.commit()
    finally:
        conn.close()


def _upsert_usuario(
    database,
    *,
    nome: str,
    email: str,
    perfil: str,
    cargo: str,
    senha: str,
    data_nascimento: str = "",
) -> int:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM usuarios
        WHERE email = ?
        LIMIT 1
        """,
        (email,),
    )
    row = cursor.fetchone()
    senha_hash = database.hash_senha(senha)
    nt_hash = database.generate_nt_hash(senha)

    if row:
        usuario_id = int(row["id"])
        cursor.execute(
            """
            UPDATE usuarios
            SET nome = ?,
                senha_hash = ?,
                nt_hash = ?,
                perfil = ?,
                cargo = ?,
                data_nascimento = ?,
                ativo = 1
            WHERE id = ?
            """,
            (
                nome,
                senha_hash,
                nt_hash,
                perfil,
                cargo,
                data_nascimento or None,
                usuario_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO usuarios (
                nome,
                email,
                senha_hash,
                nt_hash,
                perfil,
                cargo,
                data_nascimento,
                ativo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                nome,
                email,
                senha_hash,
                nt_hash,
                perfil,
                cargo,
                data_nascimento or None,
            ),
        )
        usuario_id = int(cursor.lastrowid)

    conn.commit()
    conn.close()
    return usuario_id


def _upsert_professor_carga(
    database,
    *,
    usuario_id: int,
    aulas_semanais: int,
    turmas: list[str],
    disciplinas: list[str],
) -> None:
    conn = database.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO professores_carga (
                usuario_id,
                aulas_semanais,
                turmas_quantidade,
                turmas,
                disciplinas,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(usuario_id) DO UPDATE SET
                aulas_semanais = excluded.aulas_semanais,
                turmas_quantidade = excluded.turmas_quantidade,
                turmas = excluded.turmas,
                disciplinas = excluded.disciplinas,
                atualizado_em = datetime('now')
            """,
            (
                int(usuario_id),
                int(aulas_semanais),
                len(turmas),
                database._serializar_lista_texto(turmas),
                database._serializar_lista_texto(disciplinas),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _ensure_turma(database, *, nome: str, turno: str, quantidade_estudantes: int) -> int:
    turma = database.buscar_turma_por_nome(nome, incluir_inativas=True)
    if turma:
        turma_id = int(turma["id"])
        database.atualizar_turma_dados(turma_id, turno, quantidade_estudantes)
        database.atualizar_status_turma(turma_id, True)
        return turma_id
    return int(database.criar_turma(nome, turno, quantidade_estudantes))


def _ensure_disciplina(database, *, nome: str, aulas_semanais: int) -> int:
    disciplina = database.buscar_disciplina_por_nome(nome, incluir_inativas=True)
    if disciplina:
        disciplina_id = int(disciplina["id"])
        database.atualizar_disciplina_dados(disciplina_id, aulas_semanais)
        database.atualizar_status_disciplina(disciplina_id, True)
        return disciplina_id
    return int(database.criar_disciplina(nome, aulas_semanais))


def _ensure_estudante(database, *, nome: str, turma_id: int) -> int:
    estudante_id, _criado = database.criar_ou_atualizar_estudante_por_nome_turma(
        nome=nome,
        turma_id=int(turma_id),
        ativo=True,
    )
    return int(estudante_id)


def _obter_periodo_pre_conselho_ativo(database) -> dict:
    periodos = database.listar_periodos_pre_conselho()
    for periodo in periodos:
        if str(periodo.get("status") or "").upper() == "ABERTO":
            return periodo

    ano_atual = date.today().year
    periodo = database.buscar_periodo_pre_conselho_por_ano_etapa(ano_atual, 1)
    if periodo:
        database.atualizar_status_periodo_pre_conselho(int(periodo["id"]), "ABERTO")
        return database.buscar_periodo_pre_conselho_por_id(int(periodo["id"]))

    periodo_id = database.criar_periodo_pre_conselho(
        nome=f"1o Bimestre {ano_atual}",
        ano_letivo=ano_atual,
        etapa=1,
        data_inicio=f"{ano_atual}-01-20",
        data_fim=f"{ano_atual}-04-30",
        status="ABERTO",
    )
    return database.buscar_periodo_pre_conselho_por_id(int(periodo_id))


def _sync_agendamentos(database, recursos: dict[str, int], usuarios: dict[str, int]) -> None:
    hoje = date.today()
    itens = (
        {
            "recurso_nome": "Projetor Sala Multiuso",
            "usuario_email": "professor@escola",
            "data": (hoje + timedelta(days=1)).isoformat(),
            "turno": "MATUTINO",
            "aula": "2",
            "faixa_global": 2,
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "tema_aula": "Leitura orientada e revisao textual",
        },
        {
            "recurso_nome": "Laboratório Maker",
            "usuario_email": "ana.demo@escola",
            "data": (hoje + timedelta(days=2)).isoformat(),
            "turno": "VESPERTINO",
            "aula": "4",
            "faixa_global": 9,
            "turma": f"8 Ano B{DEMO_SUFFIX}",
            "tema_aula": "Resolucao colaborativa de problemas",
        },
        {
            "recurso_nome": "Kit Tablets",
            "usuario_email": "carla.demo@escola",
            "data": (hoje + timedelta(days=3)).isoformat(),
            "turno": "MATUTINO",
            "aula": "3",
            "faixa_global": 3,
            "turma": f"1 EM A{DEMO_SUFFIX}",
            "tema_aula": "Pesquisa guiada para seminario de biologia",
        },
    )

    conn = database.get_connection()
    cursor = conn.cursor()
    for item in itens:
        recurso_id = int(recursos[item["recurso_nome"]])
        usuario_id = int(usuarios[item["usuario_email"]])
        cursor.execute(
            """
            SELECT id
            FROM agendamentos
            WHERE recurso_id = ?
              AND usuario_id = ?
              AND data = ?
              AND faixa_global = ?
            LIMIT 1
            """,
            (
                recurso_id,
                usuario_id,
                item["data"],
                int(item["faixa_global"]),
            ),
        )
        existente = cursor.fetchone()
        params = (
            recurso_id,
            usuario_id,
            item["data"],
            item["turno"],
            item["aula"],
            int(item["faixa_global"]),
            item["turma"],
            item["tema_aula"],
            OBSERVACAO_AGENDAMENTO,
        )
        if existente:
            cursor.execute(
                """
                UPDATE agendamentos
                SET recurso_id = ?,
                    usuario_id = ?,
                    data = ?,
                    turno = ?,
                    aula = ?,
                    faixa_global = ?,
                    turma = ?,
                    tema_aula = ?,
                    observacao = ?,
                    status = 'ATIVO',
                    cancelado_em = NULL
                WHERE id = ?
                """,
                params + (int(existente["id"]),),
            )
        else:
            cursor.execute(
                """
                INSERT INTO agendamentos (
                    recurso_id,
                    usuario_id,
                    data,
                    turno,
                    aula,
                    faixa_global,
                    turma,
                    tema_aula,
                    observacao,
                    status,
                    criado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVO', datetime('now'))
                """,
                params,
            )
    conn.commit()
    conn.close()


def _sync_pcpi(database, usuarios: dict[str, int]) -> None:
    hoje = date.today()
    itens = (
        {
            "data": hoje.isoformat(),
            "turno": "MATUTINO",
            "tipo_acao": "planejamento",
            "descricao_curta": DEMO_PCPI_DESCRICOES[0],
            "professor_nome": "Ana Ribeiro",
            "componente": f"Matematica{DEMO_SUFFIX}",
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "observacoes": "Ajuste de roteiro com apoio visual e atividades em duplas.",
            "usuario_email": "coordenacao.demo@escola",
        },
        {
            "data": hoje.isoformat(),
            "turno": "MATUTINO",
            "tipo_acao": "impressao",
            "descricao_curta": DEMO_PCPI_DESCRICOES[1],
            "professor_nome": "Professor Teste",
            "componente": f"Portugues{DEMO_SUFFIX}",
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "observacoes": "Separacao de materiais para avaliacao formativa da semana.",
            "usuario_email": "coordenacao.demo@escola",
        },
        {
            "data": (hoje + timedelta(days=1)).isoformat(),
            "turno": "VESPERTINO",
            "tipo_acao": "orientacao",
            "descricao_curta": DEMO_PCPI_DESCRICOES[2],
            "professor_nome": "Bruno Costa",
            "componente": f"Historia{DEMO_SUFFIX}",
            "turma": f"8 Ano B{DEMO_SUFFIX}",
            "observacoes": "Combinados para uso do laboratorio maker em atividade interdisciplinar.",
            "usuario_email": "coordenacao.demo@escola",
        },
    )

    conn = database.get_connection()
    cursor = conn.cursor()
    for item in itens:
        cursor.execute(
            """
            SELECT id
            FROM pcpi_registros_manuais
            WHERE data = ?
              AND turno = ?
              AND tipo_acao = ?
              AND descricao_curta = ?
            LIMIT 1
            """,
            (
                item["data"],
                item["turno"],
                item["tipo_acao"],
                item["descricao_curta"],
            ),
        )
        existente = cursor.fetchone()
        params = (
            item["data"],
            item["turno"],
            item["tipo_acao"],
            item["professor_nome"],
            item["componente"],
            item["turma"],
            item["descricao_curta"],
            item["observacoes"],
            int(usuarios[item["usuario_email"]]),
            int(usuarios[item["usuario_email"]]),
        )
        if existente:
            cursor.execute(
                """
                UPDATE pcpi_registros_manuais
                SET data = ?,
                    turno = ?,
                    tipo_acao = ?,
                    professor_nome = ?,
                    componente = ?,
                    turma = ?,
                    descricao_curta = ?,
                    observacoes = ?,
                    criado_por_usuario_id = ?,
                    atualizado_por_usuario_id = ?,
                    atualizado_em = datetime('now')
                WHERE id = ?
                """,
                params + (int(existente["id"]),),
            )
        else:
            cursor.execute(
                """
                INSERT INTO pcpi_registros_manuais (
                    data,
                    turno,
                    tipo_acao,
                    professor_nome,
                    componente,
                    turma,
                    descricao_curta,
                    observacoes,
                    criado_por_usuario_id,
                    atualizado_por_usuario_id,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                params,
            )
    conn.commit()
    conn.close()


def _sync_pre_conselho(
    database,
    *,
    periodo: dict,
    usuarios: dict[str, int],
    turmas: dict[str, int],
    disciplinas: dict[str, int],
    estudantes: dict[tuple[str, str], int],
) -> None:
    motivos = {
        "nao_entregou_trabalho": int(
            database.buscar_motivo_pre_conselho_por_codigo("nao_entregou_trabalho")["id"]
        ),
        "baixa_participacao_aula": int(
            database.buscar_motivo_pre_conselho_por_codigo("baixa_participacao_aula")["id"]
        ),
        "faltas_frequentes": int(
            database.buscar_motivo_pre_conselho_por_codigo("faltas_frequentes")["id"]
        ),
        "dificuldade_leitura_interpretacao": int(
            database.buscar_motivo_pre_conselho_por_codigo(
                "dificuldade_leitura_interpretacao"
            )["id"]
        ),
        "nota_abaixo_esperado": int(
            database.buscar_motivo_pre_conselho_por_codigo("nota_abaixo_esperado")["id"]
        ),
        "dificuldade_calculos_basicos": int(
            database.buscar_motivo_pre_conselho_por_codigo("dificuldade_calculos_basicos")["id"]
        ),
        "nao_realiza_atividades_casa": int(
            database.buscar_motivo_pre_conselho_por_codigo("nao_realiza_atividades_casa")["id"]
        ),
        "pouco_engajamento_atividades": int(
            database.buscar_motivo_pre_conselho_por_codigo("pouco_engajamento_atividades")["id"]
        ),
    }

    itens = (
        {
            "email": "professor@escola",
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "disciplina": f"Portugues{DEMO_SUFFIX}",
            "estudante": "Pedro Henrique Lima",
            "motivo_ids": [
                motivos["nao_entregou_trabalho"],
                motivos["baixa_participacao_aula"],
            ],
            "nivel_atencao": "medio",
            "observacao": "precisa de acompanhamento mais proximo com relacao a prazos",
        },
        {
            "email": "professor@escola",
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "disciplina": f"Portugues{DEMO_SUFFIX}",
            "estudante": "Laura Beatriz Souza",
            "motivo_ids": [
                motivos["faltas_frequentes"],
                motivos["dificuldade_leitura_interpretacao"],
            ],
            "nivel_atencao": "alto",
            "observacao": "apresenta lacunas de leitura e precisa retomar combinados de estudo",
        },
        {
            "email": "ana.demo@escola",
            "turma": f"8 Ano B{DEMO_SUFFIX}",
            "disciplina": f"Matematica{DEMO_SUFFIX}",
            "estudante": "Mariana Costa",
            "motivo_ids": [
                motivos["nota_abaixo_esperado"],
                motivos["dificuldade_calculos_basicos"],
            ],
            "nivel_atencao": "medio",
            "observacao": "beneficia-se de retomadas curtas e exercicios graduais",
        },
        {
            "email": "carla.demo@escola",
            "turma": f"1 EM A{DEMO_SUFFIX}",
            "disciplina": f"Biologia{DEMO_SUFFIX}",
            "estudante": "Rafael Gomes",
            "motivo_ids": [
                motivos["nao_realiza_atividades_casa"],
                motivos["pouco_engajamento_atividades"],
            ],
            "nivel_atencao": "baixo",
            "observacao": "precisa fortalecer rotina de estudo e participacao nas aulas",
        },
    )

    for item in itens:
        motivo_objs = database.buscar_motivos_pre_conselho_por_ids(item["motivo_ids"])
        texto = gerar_texto_pre_conselho_individual(
            motivos=motivo_objs,
            observacao_professor=item["observacao"],
            nivel_atencao=item["nivel_atencao"],
            estudante_nome=item["estudante"],
            disciplina_nome=item["disciplina"],
        )["texto"]
        database.criar_ou_atualizar_registro_pre_conselho(
            periodo_id=int(periodo["id"]),
            turma_id=int(turmas[item["turma"]]),
            disciplina_id=int(disciplinas[item["disciplina"]]),
            professor_usuario_id=int(usuarios[item["email"]]),
            estudante_id=int(estudantes[(item["turma"], item["estudante"])]),
            ano_letivo=int(periodo["ano_letivo"]),
            etapa=int(periodo["etapa"]),
            disciplina_nome=item["disciplina"],
            motivo_ids=item["motivo_ids"],
            texto_gerado=texto,
            observacao_professor=item["observacao"],
            nivel_atencao=item["nivel_atencao"],
        )


def _sync_ocorrencias(
    database,
    *,
    usuarios: dict[str, int],
    turmas: dict[str, int],
    estudantes: dict[tuple[str, str], int],
) -> None:
    item_leve = database.criar_regimento_item(
        lei_nome="Regimento Interno",
        artigo_numero="76",
        artigo_descricao="Dos deveres do estudante.",
        inciso_numero="VII",
        inciso_descricao="Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.",
    )
    item_grave = database.criar_regimento_item(
        lei_nome="Regimento Interno",
        artigo_numero="81",
        artigo_descricao="Das faltas disciplinares.",
        inciso_numero="II",
        inciso_descricao="Ausentar-se da sala ou recusar orientacao da equipe escolar.",
    )
    itens = (
        {
            "nome_estudante": "Gabriel Oliveira",
            "turma": f"7 Ano A{DEMO_SUFFIX}",
            "professor_email": "professor@escola",
            "disciplina": f"Portugues{DEMO_SUFFIX}",
            "data_ocorrencia": (date.today() - timedelta(days=3)).isoformat(),
            "aula": "2",
            "horario": "07:30",
            "descricao": "Conversas paralelas recorrentes e interrupcao da explicacao.",
            "acao": "advertencia_verbal",
            "status": "registrado",
            "regimento_item_ids": [item_leve],
        },
        {
            "nome_estudante": "Mariana Costa",
            "turma": f"8 Ano B{DEMO_SUFFIX}",
            "professor_email": "bruno.demo@escola",
            "disciplina": f"Historia{DEMO_SUFFIX}",
            "data_ocorrencia": (date.today() - timedelta(days=6)).isoformat(),
            "aula": "4",
            "horario": "15:20",
            "descricao": "Recusa em realizar atividade e saida sem autorizacao.",
            "acao": "suspensao_orientada_2_dias",
            "status": "em_acompanhamento",
            "regimento_item_ids": [item_grave],
        },
        {
            "nome_estudante": "Camila Rocha",
            "turma": f"1 EM A{DEMO_SUFFIX}",
            "professor_email": "carla.demo@escola",
            "disciplina": f"Biologia{DEMO_SUFFIX}",
            "data_ocorrencia": (date.today() - timedelta(days=1)).isoformat(),
            "aula": "3",
            "horario": "09:50",
            "descricao": "Uso indevido de celular durante avaliacao diagnostica.",
            "acao": "registro_informativo",
            "status": "aguardando_responsavel",
            "regimento_item_ids": [item_leve],
        },
    )

    estudante_ids = [
        int(estudantes[(item["turma"], item["nome_estudante"])])
        for item in itens
    ]
    placeholders = ",".join("?" for _ in estudante_ids)
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT id
        FROM ocorrencias
        WHERE estudante_id IN ({placeholders})
        """,
        estudante_ids,
    )
    ocorrencia_ids = [int(row["id"]) for row in cursor.fetchall()]
    if ocorrencia_ids:
        ocorrencia_placeholders = ",".join("?" for _ in ocorrencia_ids)
        cursor.execute(
            f"""
            DELETE FROM ocorrencia_regimento_itens
            WHERE ocorrencia_id IN ({ocorrencia_placeholders})
            """,
            ocorrencia_ids,
        )
        cursor.execute(
            f"""
            DELETE FROM ocorrencias
            WHERE id IN ({ocorrencia_placeholders})
            """,
            ocorrencia_ids,
        )
    conn.commit()
    conn.close()

    for item in itens:
        database.criar_ocorrencia(
            nome_estudante=item["nome_estudante"],
            estudante_id=int(estudantes[(item["turma"], item["nome_estudante"])]),
            turma_id=int(turmas[item["turma"]]),
            professor_requerente=database.buscar_usuario_por_email(
                item["professor_email"],
                incluir_inativos=True,
            )["nome"],
            professor_requerente_id=int(usuarios[item["professor_email"]]),
            disciplina=item["disciplina"],
            data_ocorrencia=item["data_ocorrencia"],
            aula=item["aula"],
            horario_ocorrencia=item["horario"],
            descricao=item["descricao"],
            acao_aplicada=item["acao"],
            status=item["status"],
            regimento_item_ids=item["regimento_item_ids"],
        )


def _sync_jobs(database, usuarios: dict[str, int]) -> None:
    hoje = date.today()
    itens = (
        {
            "usuario_email": "professor@escola",
            "arquivo": DEMO_JOB_ARQUIVOS[0],
            "arquivo_path": "spool/demo-roteiro-portugues.pdf",
            "copias": 2,
            "paginas_por_folha": 1,
            "duplex": 1,
            "orientacao": "retrato",
            "intervalo_paginas": "",
            "cups_options": "{}",
            "printer_name": "Visualizacao Local",
            "cups_job_id": 101,
            "erro_mensagem": None,
            "paginas_totais": 24,
            "status": "CONCLUIDO",
            "prioridade": 0,
            "criado_em": f"{(hoje - timedelta(days=5)).isoformat()} 08:15:00",
            "finalizado_em": f"{(hoje - timedelta(days=5)).isoformat()} 08:16:30",
        },
        {
            "usuario_email": "ana.demo@escola",
            "arquivo": DEMO_JOB_ARQUIVOS[1],
            "arquivo_path": "spool/demo-lista-matematica.pdf",
            "copias": 1,
            "paginas_por_folha": 2,
            "duplex": 0,
            "orientacao": "paisagem",
            "intervalo_paginas": "1-9",
            "cups_options": "{}",
            "printer_name": "Visualizacao Local",
            "cups_job_id": 102,
            "erro_mensagem": None,
            "paginas_totais": 18,
            "status": "CONCLUIDO",
            "prioridade": 0,
            "criado_em": f"{(hoje - timedelta(days=3)).isoformat()} 14:05:00",
            "finalizado_em": f"{(hoje - timedelta(days=3)).isoformat()} 14:06:05",
        },
        {
            "usuario_email": "professor@escola",
            "arquivo": DEMO_JOB_ARQUIVOS[2],
            "arquivo_path": "spool/demo-simulado-interdisciplinar.pdf",
            "copias": 1,
            "paginas_por_folha": 1,
            "duplex": 1,
            "orientacao": "retrato",
            "intervalo_paginas": "",
            "cups_options": "{}",
            "printer_name": "Visualizacao Local",
            "cups_job_id": None,
            "erro_mensagem": None,
            "paginas_totais": 30,
            "status": "PROCESSANDO",
            "prioridade": 1,
            "criado_em": f"{hoje.isoformat()} 10:20:00",
            "finalizado_em": None,
        },
    )

    conn = database.get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in DEMO_JOB_ARQUIVOS)
    cursor.execute(
        f"""
        DELETE FROM jobs
        WHERE arquivo IN ({placeholders})
        """,
        list(DEMO_JOB_ARQUIVOS),
    )
    cursor.executemany(
        """
        INSERT INTO jobs (
            usuario_id,
            arquivo,
            arquivo_path,
            copias,
            paginas_por_folha,
            duplex,
            orientacao,
            intervalo_paginas,
            cups_options,
            printer_name,
            cups_job_id,
            erro_mensagem,
            paginas_totais,
            status,
            prioridade,
            criado_em,
            finalizado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                int(usuarios[item["usuario_email"]]),
                item["arquivo"],
                item["arquivo_path"],
                int(item["copias"]),
                int(item["paginas_por_folha"]),
                int(item["duplex"]),
                item["orientacao"],
                item["intervalo_paginas"],
                item["cups_options"],
                item["printer_name"],
                item["cups_job_id"],
                item["erro_mensagem"],
                int(item["paginas_totais"]),
                item["status"],
                int(item["prioridade"]),
                item["criado_em"],
                item["finalizado_em"],
            )
            for item in itens
        ],
    )
    conn.commit()
    conn.close()


def _sync_cotas(database, usuarios: dict[str, int]) -> None:
    mes_referencia = date.today().strftime(MES_ATUAL_FMT)
    database.recalcular_cotas_mes(mes_referencia)

    usos = {
        "professor@escola": 24,
        "ana.demo@escola": 18,
        "bruno.demo@escola": 0,
        "carla.demo@escola": 0,
    }
    conn = database.get_connection()
    cursor = conn.cursor()
    for email, usadas_paginas in usos.items():
        usuario_id = int(usuarios[email])
        cursor.execute(
            """
            UPDATE cotas
            SET usadas_paginas = ?
            WHERE usuario_id = ?
              AND mes = ?
            """,
            (int(usadas_paginas), usuario_id, mes_referencia),
        )
        if cursor.rowcount == 0:
            limite = int(database.calcular_limite_cota_usuario(usuario_id))
            cursor.execute(
                """
                INSERT INTO cotas (usuario_id, mes, limite_paginas, usadas_paginas)
                VALUES (?, ?, ?, ?)
                """,
                (usuario_id, mes_referencia, limite, int(usadas_paginas)),
            )
    conn.commit()
    conn.close()


def _montar_sumario(database) -> dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    demo_emails = [item["email"] for item in DEMO_USUARIOS]
    turma_nomes = [item["nome"] for item in DEMO_TURMAS]
    disciplina_nomes = [item["nome"] for item in DEMO_DISCIPLINAS]
    pcpi_descricoes = list(DEMO_PCPI_DESCRICOES)
    placeholders_emails = ",".join("?" for _ in demo_emails)
    placeholders_turmas = ",".join("?" for _ in turma_nomes)
    placeholders_disciplinas = ",".join("?" for _ in disciplina_nomes)
    placeholders_jobs = ",".join("?" for _ in DEMO_JOB_ARQUIVOS)
    placeholders_pcpi = ",".join("?" for _ in pcpi_descricoes)

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM usuarios
        WHERE email IN ({placeholders_emails})
        """,
        demo_emails,
    )
    usuarios_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM turmas
        WHERE nome IN ({placeholders_turmas})
        """,
        turma_nomes,
    )
    turmas_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM disciplinas
        WHERE nome IN ({placeholders_disciplinas})
        """,
        disciplina_nomes,
    )
    disciplinas_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM estudantes
        WHERE turma_id IN (
            SELECT id
            FROM turmas
            WHERE nome IN ({placeholders_turmas})
        )
        """,
        turma_nomes,
    )
    estudantes_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM professores_turmas_disciplinas
        WHERE turma_id IN (
            SELECT id
            FROM turmas
            WHERE nome IN ({placeholders_turmas})
        )
        """,
        turma_nomes,
    )
    atribuicoes_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE turma IN ({placeholders_turmas})
          AND observacao = ?
        """,
        turma_nomes + [OBSERVACAO_AGENDAMENTO],
    )
    agendamentos_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM pcpi_registros_manuais
        WHERE descricao_curta IN ({placeholders_pcpi})
        """,
        pcpi_descricoes,
    )
    pcpi_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM pre_conselho_registros
        WHERE turma_id IN (
            SELECT id
            FROM turmas
            WHERE nome IN ({placeholders_turmas})
        )
        """,
        turma_nomes,
    )
    pre_conselho_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM ocorrencias
        WHERE turma_id IN (
            SELECT id
            FROM turmas
            WHERE nome IN ({placeholders_turmas})
        )
        """,
        turma_nomes,
    )
    ocorrencias_demo = int(cursor.fetchone()["total"])

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE arquivo IN ({placeholders_jobs})
        """,
        list(DEMO_JOB_ARQUIVOS),
    )
    jobs_demo = int(cursor.fetchone()["total"])
    conn.close()

    return {
        "db_path": str(database.DB_PATH),
        "usuarios_demo": usuarios_demo,
        "turmas_demo": turmas_demo,
        "disciplinas_demo": disciplinas_demo,
        "estudantes_demo": estudantes_demo,
        "atribuicoes_demo": atribuicoes_demo,
        "agendamentos_demo": agendamentos_demo,
        "pcpi_demo": pcpi_demo,
        "pre_conselho_demo": pre_conselho_demo,
        "ocorrencias_demo": ocorrencias_demo,
        "jobs_demo": jobs_demo,
    }


def seed_demo_data(db_path: str | None = None) -> dict:
    database = _get_database(db_path)
    database.criar_tabelas()

    database.criar_usuario_se_nao_existir(
        nome="Administrador",
        email="admin@escola",
        senha_hash=database.hash_senha(ADMIN_PASSWORD),
        senha_plana=ADMIN_PASSWORD,
        perfil="admin",
        cargo="ADMIN",
    )
    database.criar_usuario_se_nao_existir(
        nome="Professor Teste",
        email="professor@escola",
        senha_hash=database.hash_senha(PROFESSOR_PASSWORD),
        senha_plana=PROFESSOR_PASSWORD,
        perfil="professor",
        cargo="PROFESSOR",
    )
    database.seed_recursos_padrao()

    _atualizar_status_ativo_por_email(database, "admin@escola")
    _atualizar_status_ativo_por_email(database, "professor@escola")

    usuarios = {
        "admin@escola": int(
            database.buscar_usuario_por_email("admin@escola", incluir_inativos=True)["id"]
        ),
        "professor@escola": int(
            database.buscar_usuario_por_email("professor@escola", incluir_inativos=True)["id"]
        ),
    }

    for item in DEMO_USUARIOS:
        usuarios[item["email"]] = _upsert_usuario(database, **item)

    for item in DEMO_PROFESSORES_CARGA:
        _upsert_professor_carga(
            database,
            usuario_id=int(usuarios[item["email"]]),
            aulas_semanais=int(item["aulas_semanais"]),
            turmas=list(item["turmas"]),
            disciplinas=list(item["disciplinas"]),
        )

    turmas = {
        item["nome"]: _ensure_turma(database, **item)
        for item in DEMO_TURMAS
    }
    disciplinas = {
        item["nome"]: _ensure_disciplina(database, **item)
        for item in DEMO_DISCIPLINAS
    }

    estudantes: dict[tuple[str, str], int] = {}
    for turma_nome, nomes_estudantes in DEMO_ESTUDANTES.items():
        turma_id = int(turmas[turma_nome])
        for estudante_nome in nomes_estudantes:
            estudantes[(turma_nome, estudante_nome)] = _ensure_estudante(
                database,
                nome=estudante_nome,
                turma_id=turma_id,
            )

    for atribuicao in DEMO_ATRIBUICOES:
        database.criar_ou_atualizar_turma_disciplina(
            turma_id=int(turmas[atribuicao["turma"]]),
            disciplina_id=int(disciplinas[atribuicao["disciplina"]]),
            carga_horaria=int(atribuicao["carga_horaria"]),
            professor_usuario_id=int(usuarios[atribuicao["email"]]),
        )

    recursos = {
        item["nome"]: int(item["id"])
        for item in database.listar_recursos_ativos()
    }
    periodo = _obter_periodo_pre_conselho_ativo(database)

    _sync_agendamentos(database, recursos, usuarios)
    _sync_pcpi(database, usuarios)
    _sync_pre_conselho(
        database,
        periodo=periodo,
        usuarios=usuarios,
        turmas=turmas,
        disciplinas=disciplinas,
        estudantes=estudantes,
    )
    _sync_ocorrencias(
        database,
        usuarios=usuarios,
        turmas=turmas,
        estudantes=estudantes,
    )
    _sync_jobs(database, usuarios)
    _sync_cotas(database, usuarios)

    return _montar_sumario(database)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Popula o banco local com dados de demonstracao idempotentes."
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_PATH", "").strip() or None,
        help="Caminho opcional para o banco SQLite.",
    )
    args = parser.parse_args()

    resumo = seed_demo_data(args.db)
    print(f"Banco populado para visualizacao local em: {resumo['db_path']}")
    print(f"- Usuarios demo: {resumo['usuarios_demo']}")
    print(f"- Turmas demo: {resumo['turmas_demo']}")
    print(f"- Disciplinas demo: {resumo['disciplinas_demo']}")
    print(f"- Estudantes demo: {resumo['estudantes_demo']}")
    print(f"- Atribuicoes demo: {resumo['atribuicoes_demo']}")
    print(f"- Agendamentos demo: {resumo['agendamentos_demo']}")
    print(f"- Registros PCPI demo: {resumo['pcpi_demo']}")
    print(f"- Registros pre-conselho demo: {resumo['pre_conselho_demo']}")
    print(f"- Ocorrencias demo: {resumo['ocorrencias_demo']}")
    print(f"- Jobs demo: {resumo['jobs_demo']}")
    print("Logins uteis:")
    print(f"- admin@escola / {ADMIN_PASSWORD}")
    print(f"- professor@escola / {PROFESSOR_PASSWORD}")
    print(f"- coordenacao.demo@escola / {COORDENACAO_PASSWORD}")
    print(f"- ana.demo@escola / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
