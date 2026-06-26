#!/usr/bin/env python3


def upgrade(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ocorrencia_rascunhos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'discarded')),
            ocorrencia_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(ocorrencia_id) REFERENCES ocorrencias(id)
        )
        """
    )
    conn.commit()


def downgrade(conn):
    conn.commit()
