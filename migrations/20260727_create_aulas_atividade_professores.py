import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS aulas_atividade_professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano_letivo INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            dia_semana TEXT,
            aula_numero INTEGER,
            faixa_global INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id),
            CHECK (
                (dia_semana IS NULL AND aula_numero IS NULL AND faixa_global IS NULL)
                OR
                (dia_semana IS NOT NULL AND aula_numero > 0 AND faixa_global > 0)
            )
        )
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_aulas_atividade_professor_slot
        ON aulas_atividade_professores(
            ano_letivo,
            professor_usuario_id,
            dia_semana,
            faixa_global
        )
        WHERE dia_semana IS NOT NULL
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_aulas_atividade_professor_lookup
        ON aulas_atividade_professores(ano_letivo, professor_usuario_id)
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_aulas_atividade_professor_lookup")
    cursor.execute("DROP INDEX IF EXISTS idx_aulas_atividade_professor_slot")
    cursor.execute("DROP TABLE IF EXISTS aulas_atividade_professores")
    conn.commit()
