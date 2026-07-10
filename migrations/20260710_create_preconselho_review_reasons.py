#!/usr/bin/env python3
import sqlite3


DEFAULTS = {
    "recuperado": (
        ("participou_e_avancou_recuperacao", "Participou da recuperação paralela e apresentou avanços"),
        ("retomou_conteudos_essenciais", "Retomou os conteúdos essenciais da disciplina"),
        ("melhorou_resultados_avaliativos", "Melhorou os resultados nas atividades e avaliações de recuperação"),
        ("ampliou_participacao_compromisso", "Demonstrou mais participação, compromisso e entrega das atividades"),
    ),
    "nao_recuperado": (
        ("manteve_baixo_rendimento", "Manteve baixo rendimento mesmo após a recuperação paralela"),
        ("nao_concluiu_atividades_recuperacao", "Não concluiu as atividades propostas na recuperação paralela"),
        ("baixa_frequencia_recuperacao", "Apresentou baixa frequência nos momentos de recuperação"),
        ("dificuldades_persistem_conteudos", "As dificuldades nos conteúdos essenciais persistem"),
    ),
}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pre_conselho_motivos_reavaliacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resultado TEXT NOT NULL,
            codigo TEXT NOT NULL UNIQUE,
            descricao TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    for resultado, motivos in DEFAULTS.items():
        for ordem, (codigo, descricao) in enumerate(motivos, start=1):
            cursor.execute(
                """INSERT OR IGNORE INTO pre_conselho_motivos_reavaliacao
                   (resultado, codigo, descricao, ativo, ordem) VALUES (?, ?, ?, 1, ?)""",
                (resultado, codigo, descricao, ordem * 10),
            )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS pre_conselho_motivos_reavaliacao")
    conn.commit()
