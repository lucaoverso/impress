#!/usr/bin/env python3
import sqlite3


DEFAULT_SEGMENTS = (
    ("MATUTINO", "MATUTINO", 1, 5, 1),
    ("VESPERTINO", "VESPERTINO", 6, 10, 1),
    ("VESPERTINO_EM", "VESPERTINO", 6, 11, 1),
    ("INTEGRAL", "MATUTINO", 1, 5, 1),
    ("INTEGRAL", "VESPERTINO", 7, 9, 2),
)


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracao_turnos_segmentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turno TEXT NOT NULL,
            periodo TEXT NOT NULL,
            faixa_inicial INTEGER NOT NULL,
            faixa_final INTEGER NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 1,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(turno, periodo)
        )
        """
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO configuracao_turnos_segmentos (
            turno, periodo, faixa_inicial, faixa_final, ordem, ativo
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        DEFAULT_SEGMENTS,
    )

    # Ajusta somente o valor padrao legado. Horarios e agendamentos existentes
    # permanecem intactos para evitar qualquer perda ou remapeamento ambiguo.
    cursor.execute(
        """
        UPDATE turmas
        SET aula_final = 9
        WHERE UPPER(COALESCE(turno, '')) = 'INTEGRAL'
          AND aula_inicial = 1
          AND aula_final = 8
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS configuracao_turnos_segmentos")
    conn.commit()
