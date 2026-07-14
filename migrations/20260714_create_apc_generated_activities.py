#!/usr/bin/env python3
import sqlite3


def upgrade(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS apc_generated_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            envio_id INTEGER NOT NULL UNIQUE,
            habilidade_codigo_snapshot TEXT NOT NULL DEFAULT '',
            habilidade_descricao_snapshot TEXT NOT NULL,
            conteudo_descricao_snapshot TEXT NOT NULL,
            introducao_html TEXT NOT NULL DEFAULT '',
            atividades_html TEXT NOT NULL,
            activity_columns INTEGER NOT NULL DEFAULT 1 CHECK(activity_columns IN (1, 2)),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(envio_id) REFERENCES apc_envios(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_apc_generated_activities_envio ON apc_generated_activities(envio_id)"
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    conn.execute("DROP INDEX IF EXISTS idx_apc_generated_activities_envio")
    conn.execute("DROP TABLE IF EXISTS apc_generated_activities")
    conn.commit()

