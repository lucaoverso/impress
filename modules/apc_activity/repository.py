from database import get_connection
from db.apc import atualizar_apc_envio, criar_apc_envio


def save_submission(*, existing: dict | None, values: dict) -> dict:
    if existing:
        update_values = {
            key: values[key]
            for key in (
                "arquivo_nome_cliente",
                "arquivo_nome_original",
                "arquivo_path",
                "arquivo_tamanho",
                "arquivo_tipo",
            )
        }
        return atualizar_apc_envio(envio_id=int(existing["id"]), **update_values)
    return criar_apc_envio(**values)


def upsert_generated_activity(*, envio_id: int, values: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO apc_generated_activities (
            envio_id, habilidade_codigo_snapshot, habilidade_descricao_snapshot,
            conteudo_descricao_snapshot, introducao_html, atividades_html,
            activity_columns, criado_em, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(envio_id) DO UPDATE SET
            habilidade_codigo_snapshot = excluded.habilidade_codigo_snapshot,
            habilidade_descricao_snapshot = excluded.habilidade_descricao_snapshot,
            conteudo_descricao_snapshot = excluded.conteudo_descricao_snapshot,
            introducao_html = excluded.introducao_html,
            atividades_html = excluded.atividades_html,
            activity_columns = excluded.activity_columns,
            atualizado_em = datetime('now')
        """,
        (
            int(envio_id),
            "",
            values["habilidade"],
            values["conteudo"],
            "",
            values["corpo_html"],
            int(values["activity_columns"]),
        ),
    )
    conn.commit()
    cursor.execute("SELECT * FROM apc_generated_activities WHERE envio_id = ?", (int(envio_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_generated_activity(envio_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apc_generated_activities WHERE envio_id = ?", (int(envio_id),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
