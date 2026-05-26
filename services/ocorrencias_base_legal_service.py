from repositories.ocorrencias_repository import (
    atualizar_alinea,
    atualizar_artigo,
    atualizar_inciso,
    atualizar_lei,
    buscar_alinea_por_id,
    buscar_artigo_por_id,
    buscar_inciso_por_id,
    buscar_lei_por_id,
    criar_alinea,
    criar_artigo,
    criar_inciso,
    criar_lei,
    listar_alineas,
    listar_artigos,
    listar_incisos,
    listar_leis,
    remover_alinea,
    remover_artigo,
    remover_inciso,
    remover_lei,
)


def _texto_obrigatorio_base_legal(valor: str | None, *, campo: str, max_len: int) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _buscar_ou_levantar(buscar_fn, item_id: int, mensagem: str) -> dict:
    item = buscar_fn(item_id)
    if not item:
        raise LookupError(mensagem)
    return item


def _remover_ou_levantar(remover_fn, item_id: int, mensagem: str) -> None:
    removido = remover_fn(item_id)
    if not removido:
        raise LookupError(mensagem)


def listar_leis_service() -> list[dict]:
    return listar_leis()


def buscar_lei_service(lei_id: int) -> dict:
    return _buscar_ou_levantar(buscar_lei_por_id, lei_id, "Lei nao encontrada.")


def criar_lei_service(*, nome: str) -> dict:
    lei_id = criar_lei(nome=_texto_obrigatorio_base_legal(nome, campo="Nome da lei", max_len=120))
    return buscar_lei_service(lei_id)


def atualizar_lei_service(*, lei_id: int, nome: str) -> dict:
    buscar_lei_service(lei_id)
    alterado = atualizar_lei(
        lei_id=lei_id,
        nome=_texto_obrigatorio_base_legal(nome, campo="Nome da lei", max_len=120),
    )
    if not alterado:
        raise LookupError("Lei nao encontrada.")
    return buscar_lei_service(lei_id)


def remover_lei_service(lei_id: int) -> None:
    _remover_ou_levantar(remover_lei, lei_id, "Lei nao encontrada.")


def listar_artigos_service(*, lei_id: int | None = None) -> list[dict]:
    return listar_artigos(lei_id=lei_id)


def buscar_artigo_service(artigo_id: int) -> dict:
    return _buscar_ou_levantar(buscar_artigo_por_id, artigo_id, "Artigo nao encontrado.")


def criar_artigo_service(*, lei_id: int, numero: str, descricao: str) -> dict:
    buscar_lei_service(lei_id)
    artigo_id = criar_artigo(
        lei_id=lei_id,
        numero=_texto_obrigatorio_base_legal(numero, campo="Numero do artigo", max_len=120),
        descricao=_texto_obrigatorio_base_legal(
            descricao, campo="Descricao do artigo", max_len=5000
        ),
    )
    return buscar_artigo_service(artigo_id)


def atualizar_artigo_service(*, artigo_id: int, lei_id: int, numero: str, descricao: str) -> dict:
    buscar_artigo_service(artigo_id)
    buscar_lei_service(lei_id)
    alterado = atualizar_artigo(
        artigo_id=artigo_id,
        lei_id=lei_id,
        numero=_texto_obrigatorio_base_legal(numero, campo="Numero do artigo", max_len=120),
        descricao=_texto_obrigatorio_base_legal(
            descricao, campo="Descricao do artigo", max_len=5000
        ),
    )
    if not alterado:
        raise LookupError("Artigo nao encontrado.")
    return buscar_artigo_service(artigo_id)


def remover_artigo_service(artigo_id: int) -> None:
    _remover_ou_levantar(remover_artigo, artigo_id, "Artigo nao encontrado.")


def listar_incisos_service(*, artigo_id: int | None = None) -> list[dict]:
    return listar_incisos(artigo_id=artigo_id)


def buscar_inciso_service(inciso_id: int) -> dict:
    return _buscar_ou_levantar(buscar_inciso_por_id, inciso_id, "Inciso nao encontrado.")


def criar_inciso_service(*, artigo_id: int, numero: str, descricao: str) -> dict:
    buscar_artigo_service(artigo_id)
    inciso_id = criar_inciso(
        artigo_id=artigo_id,
        numero=_texto_obrigatorio_base_legal(numero, campo="Numero do inciso", max_len=40),
        descricao=_texto_obrigatorio_base_legal(
            descricao, campo="Descricao do inciso", max_len=5000
        ),
    )
    return buscar_inciso_service(inciso_id)


def atualizar_inciso_service(*, inciso_id: int, artigo_id: int, numero: str, descricao: str) -> dict:
    buscar_inciso_service(inciso_id)
    buscar_artigo_service(artigo_id)
    alterado = atualizar_inciso(
        inciso_id=inciso_id,
        artigo_id=artigo_id,
        numero=_texto_obrigatorio_base_legal(numero, campo="Numero do inciso", max_len=40),
        descricao=_texto_obrigatorio_base_legal(
            descricao, campo="Descricao do inciso", max_len=5000
        ),
    )
    if not alterado:
        raise LookupError("Inciso nao encontrado.")
    return buscar_inciso_service(inciso_id)


def remover_inciso_service(inciso_id: int) -> None:
    _remover_ou_levantar(remover_inciso, inciso_id, "Inciso nao encontrado.")


def listar_alineas_service(*, inciso_id: int | None = None) -> list[dict]:
    return listar_alineas(inciso_id=inciso_id)


def buscar_alinea_service(alinea_id: int) -> dict:
    return _buscar_ou_levantar(buscar_alinea_por_id, alinea_id, "Alinea nao encontrada.")


def criar_alinea_service(*, inciso_id: int, identificador: str, descricao: str) -> dict:
    buscar_inciso_service(inciso_id)
    alinea_id = criar_alinea(
        inciso_id=inciso_id,
        identificador=_texto_obrigatorio_base_legal(
            identificador,
            campo="Identificador da alinea",
            max_len=40,
        ),
        descricao=_texto_obrigatorio_base_legal(
            descricao,
            campo="Descricao da alinea",
            max_len=5000,
        ),
    )
    return buscar_alinea_service(alinea_id)


def atualizar_alinea_service(
    *,
    alinea_id: int,
    inciso_id: int,
    identificador: str,
    descricao: str,
) -> dict:
    buscar_alinea_service(alinea_id)
    buscar_inciso_service(inciso_id)
    alterado = atualizar_alinea(
        alinea_id=alinea_id,
        inciso_id=inciso_id,
        identificador=_texto_obrigatorio_base_legal(
            identificador,
            campo="Identificador da alinea",
            max_len=40,
        ),
        descricao=_texto_obrigatorio_base_legal(
            descricao,
            campo="Descricao da alinea",
            max_len=5000,
        ),
    )
    if not alterado:
        raise LookupError("Alinea nao encontrada.")
    return buscar_alinea_service(alinea_id)


def remover_alinea_service(alinea_id: int) -> None:
    _remover_ou_levantar(remover_alinea, alinea_id, "Alinea nao encontrada.")
