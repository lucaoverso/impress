#!/usr/bin/env python3
import sqlite3


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def _columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cursor.fetchall()}


def upgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if not _table_exists(cursor, "apc_envios"):
        conn.commit()
        return

    columns = _columns(cursor, "apc_envios")
    if "primeiro_envio_em" not in columns:
        cursor.execute(
            "ALTER TABLE apc_envios ADD COLUMN primeiro_envio_em TEXT NOT NULL DEFAULT ''"
        )

    cursor.execute(
        """
        UPDATE apc_envios
        SET primeiro_envio_em = COALESCE(NULLIF(TRIM(enviado_em), ''), datetime('now'))
        WHERE TRIM(COALESCE(primeiro_envio_em, '')) = ''
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS apc_envio_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            envio_id INTEGER NOT NULL,
            periodo_id INTEGER NOT NULL,
            professor_usuario_id INTEGER NOT NULL,
            turma_id INTEGER NOT NULL DEFAULT 0,
            disciplina_id INTEGER NOT NULL DEFAULT 0,
            arquivo_nome_cliente TEXT NOT NULL DEFAULT '',
            arquivo_nome_original TEXT NOT NULL DEFAULT '',
            arquivo_path TEXT NOT NULL DEFAULT '',
            arquivo_tamanho INTEGER NOT NULL DEFAULT 0,
            arquivo_tipo TEXT NOT NULL DEFAULT '',
            acao TEXT NOT NULL DEFAULT 'ENVIO',
            enviado_em TEXT NOT NULL DEFAULT (datetime('now')),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(envio_id) REFERENCES apc_envios(id) ON DELETE CASCADE,
            FOREIGN KEY(periodo_id) REFERENCES apc_periodos(id),
            FOREIGN KEY(professor_usuario_id) REFERENCES usuarios(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envio_historico_envio
        ON apc_envio_historico(envio_id, enviado_em)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apc_envio_historico_periodo
        ON apc_envio_historico(periodo_id, professor_usuario_id, turma_id, disciplina_id)
        """
    )
    cursor.execute(
        """
        INSERT INTO apc_envio_historico (
            envio_id,
            periodo_id,
            professor_usuario_id,
            turma_id,
            disciplina_id,
            arquivo_nome_cliente,
            arquivo_nome_original,
            arquivo_path,
            arquivo_tamanho,
            arquivo_tipo,
            acao,
            enviado_em,
            criado_em
        )
        SELECT
            ae.id,
            ae.periodo_id,
            ae.professor_usuario_id,
            COALESCE(ae.turma_id, 0),
            COALESCE(ae.disciplina_id, 0),
            COALESCE(ae.arquivo_nome_cliente, ae.arquivo_nome_original, ''),
            COALESCE(ae.arquivo_nome_original, ''),
            COALESCE(ae.arquivo_path, ''),
            COALESCE(ae.arquivo_tamanho, 0),
            COALESCE(ae.arquivo_tipo, ''),
            'ENVIO',
            COALESCE(NULLIF(TRIM(ae.primeiro_envio_em), ''), NULLIF(TRIM(ae.enviado_em), ''), datetime('now')),
            COALESCE(NULLIF(TRIM(ae.primeiro_envio_em), ''), NULLIF(TRIM(ae.enviado_em), ''), datetime('now'))
        FROM apc_envios ae
        WHERE NOT EXISTS (
            SELECT 1
            FROM apc_envio_historico ah
            WHERE ah.envio_id = ae.id
        )
        """
    )
    conn.commit()


def downgrade(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envio_historico_periodo")
    cursor.execute("DROP INDEX IF EXISTS idx_apc_envio_historico_envio")
    cursor.execute("DROP TABLE IF EXISTS apc_envio_historico")
    conn.commit()
