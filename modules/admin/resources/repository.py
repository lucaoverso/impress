import importlib


def _get_connection():
    return importlib.import_module("database").get_connection()


def listar_recursos_ativos():
    return listar_recursos(incluir_inativos=False)


def listar_recursos(incluir_inativos: bool = False):
    conn = _get_connection()
    query = """
        SELECT
            id,
            nome,
            tipo,
            COALESCE(descricao, '') AS descricao,
            CASE WHEN COALESCE(quantidade_itens, 1) < 1 THEN 1 ELSE quantidade_itens END AS quantidade_itens,
            COALESCE(imagem_capa, '') AS imagem_capa,
            ativo
        FROM recursos
    """
    if not incluir_inativos:
        query += " WHERE ativo = 1"
    query += " ORDER BY nome ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def criar_recurso(
    nome: str,
    tipo: str,
    descricao: str = "",
    quantidade_itens: int = 1,
    imagem_capa: str = "",
):
    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO recursos (nome, tipo, descricao, quantidade_itens, imagem_capa, ativo)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (nome, tipo, descricao, max(int(quantidade_itens or 0), 1), imagem_capa),
    )
    recurso_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recurso_id


def atualizar_recurso_dados(
    recurso_id: int,
    nome: str,
    tipo: str,
    descricao: str = "",
    quantidade_itens: int = 1,
    imagem_capa: str = "",
):
    conn = _get_connection()
    cursor = conn.execute(
        """
        UPDATE recursos
        SET nome = ?, tipo = ?, descricao = ?, quantidade_itens = ?, imagem_capa = ?
        WHERE id = ?
        """,
        (nome, tipo, descricao, max(int(quantidade_itens or 0), 1), imagem_capa, recurso_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def atualizar_recurso_quantidade_itens(recurso_id: int, quantidade_itens: int):
    conn = _get_connection()
    cursor = conn.execute(
        "UPDATE recursos SET quantidade_itens = ? WHERE id = ?",
        (max(int(quantidade_itens or 0), 1), recurso_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def atualizar_status_recurso(recurso_id: int, ativo: bool):
    conn = _get_connection()
    cursor = conn.execute(
        "UPDATE recursos SET ativo = ? WHERE id = ?",
        (1 if ativo else 0, recurso_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def buscar_recurso_por_id(recurso_id: int):
    conn = _get_connection()
    row = conn.execute(
        """
        SELECT
            id,
            nome,
            tipo,
            COALESCE(descricao, '') AS descricao,
            CASE WHEN COALESCE(quantidade_itens, 1) < 1 THEN 1 ELSE quantidade_itens END AS quantidade_itens,
            COALESCE(imagem_capa, '') AS imagem_capa,
            ativo
        FROM recursos
        WHERE id = ?
        """,
        (recurso_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
