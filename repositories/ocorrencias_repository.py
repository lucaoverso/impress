from db.ocorrencias import (
    ACAO_OCORRENCIA_VALIDAS,
    STATUS_OCORRENCIA_REGISTRADO,
    STATUS_OCORRENCIA_VALIDOS,
    TIPOS_REGISTRO_OCORRENCIA,
    atualizar_alinea as _atualizar_alinea,
    atualizar_artigo as _atualizar_artigo,
    atualizar_estudante as _atualizar_estudante,
    atualizar_inciso as _atualizar_inciso,
    atualizar_lei as _atualizar_lei,
    atualizar_ocorrencia as _atualizar_ocorrencia,
    atualizar_regimento_item as _atualizar_regimento_item,
    atualizar_status_estudante as _atualizar_status_estudante,
    atualizar_status_regimento_item as _atualizar_status_regimento_item,
    buscar_alinea_por_id as _buscar_alinea_por_id,
    buscar_artigo_por_id as _buscar_artigo_por_id,
    buscar_estudante_por_id as _buscar_estudante_por_id,
    buscar_estudantes_ocorrencia as _buscar_estudantes_ocorrencia,
    buscar_inciso_por_id as _buscar_inciso_por_id,
    buscar_lei_por_id as _buscar_lei_por_id,
    buscar_ocorrencia_por_id as _buscar_ocorrencia_por_id,
    buscar_professor_por_id_ocorrencia as _buscar_professor_por_id_ocorrencia,
    buscar_professores_ocorrencia as _buscar_professores_ocorrencia,
    buscar_regimento_item_por_id as _buscar_regimento_item_por_id,
    buscar_regimento_itens_por_ids as _buscar_regimento_itens_por_ids,
    criar_alinea as _criar_alinea,
    criar_artigo as _criar_artigo,
    criar_estudante as _criar_estudante,
    criar_inciso as _criar_inciso,
    criar_lei as _criar_lei,
    criar_ocorrencia as _criar_ocorrencia,
    criar_regimento_item as _criar_regimento_item,
    listar_alineas as _listar_alineas,
    listar_artigos as _listar_artigos,
    listar_estudantes as _listar_estudantes,
    listar_incisos as _listar_incisos,
    listar_leis as _listar_leis,
    listar_ocorrencias as _listar_ocorrencias,
    listar_regimento_itens as _listar_regimento_itens,
    remover_alinea as _remover_alinea,
    remover_artigo as _remover_artigo,
    remover_estudante as _remover_estudante,
    remover_inciso as _remover_inciso,
    remover_lei as _remover_lei,
    remover_ocorrencia as _remover_ocorrencia,
    remover_regimento_item as _remover_regimento_item,
    salvar_ocorrencia_estudantes_vinculados as _salvar_ocorrencia_estudantes_vinculados,
    salvar_ocorrencia_professores_vinculados as _salvar_ocorrencia_professores_vinculados,
    salvar_regimento_itens_ocorrencia as _salvar_regimento_itens_ocorrencia,
)


def atualizar_alinea(alinea_id: int, **dados):
    return _atualizar_alinea(alinea_id, **dados)


def atualizar_artigo(artigo_id: int, **dados):
    return _atualizar_artigo(artigo_id, **dados)


def atualizar_estudante(estudante_id: int, **dados):
    return _atualizar_estudante(estudante_id, **dados)


def atualizar_inciso(inciso_id: int, **dados):
    return _atualizar_inciso(inciso_id, **dados)


def atualizar_lei(lei_id: int, **dados):
    return _atualizar_lei(lei_id, **dados)


def atualizar_ocorrencia(ocorrencia_id: int, dados: dict | None = None, **campos):
    dados_atualizacao = dict(dados or {})
    if campos:
        dados_atualizacao.update(campos)
    return _atualizar_ocorrencia(ocorrencia_id, dados_atualizacao)


def atualizar_regimento_item(regimento_item_id: int, **dados):
    return _atualizar_regimento_item(regimento_item_id, **dados)


def atualizar_status_estudante(estudante_id: int, ativo: bool):
    return _atualizar_status_estudante(estudante_id, ativo)


def atualizar_status_regimento_item(regimento_item_id: int, ativo: bool):
    return _atualizar_status_regimento_item(regimento_item_id, ativo)


def buscar_alinea_por_id(alinea_id: int):
    return _buscar_alinea_por_id(alinea_id)


def buscar_artigo_por_id(artigo_id: int):
    return _buscar_artigo_por_id(artigo_id)


def buscar_estudante_por_id(estudante_id: int):
    return _buscar_estudante_por_id(estudante_id)


def buscar_estudantes_ocorrencia(*, termo: str, limite: int = 20):
    return _buscar_estudantes_ocorrencia(termo=termo, limite=limite)


def buscar_inciso_por_id(inciso_id: int):
    return _buscar_inciso_por_id(inciso_id)


def buscar_lei_por_id(lei_id: int):
    return _buscar_lei_por_id(lei_id)


def buscar_ocorrencia_por_id(ocorrencia_id: int):
    return _buscar_ocorrencia_por_id(ocorrencia_id)


def buscar_professor_por_id_ocorrencia(professor_id: int):
    return _buscar_professor_por_id_ocorrencia(professor_id)


def buscar_professores_ocorrencia(*, termo: str, limite: int = 20):
    return _buscar_professores_ocorrencia(termo=termo, limite=limite)


def buscar_regimento_item_por_id(regimento_item_id: int):
    return _buscar_regimento_item_por_id(regimento_item_id)


def buscar_regimento_itens_por_ids(regimento_item_ids: list[int]):
    return _buscar_regimento_itens_por_ids(regimento_item_ids)


def criar_alinea(**dados):
    return _criar_alinea(**dados)


def criar_artigo(**dados):
    return _criar_artigo(**dados)


def criar_estudante(**dados):
    return _criar_estudante(**dados)


def criar_inciso(**dados):
    return _criar_inciso(**dados)


def criar_lei(**dados):
    return _criar_lei(**dados)


def criar_ocorrencia(**dados):
    return _criar_ocorrencia(**dados)


def criar_regimento_item(**dados):
    return _criar_regimento_item(**dados)


def listar_alineas(*, inciso_id: int | None = None):
    return _listar_alineas(inciso_id=inciso_id)


def listar_artigos(*, lei_id: int | None = None):
    return _listar_artigos(lei_id=lei_id)


def listar_estudantes(**filtros):
    return _listar_estudantes(**filtros)


def listar_incisos(*, artigo_id: int | None = None):
    return _listar_incisos(artigo_id=artigo_id)


def listar_leis():
    return _listar_leis()


def listar_ocorrencias(**filtros):
    return _listar_ocorrencias(**filtros)


def listar_regimento_itens(*, incluir_inativos: bool = True):
    return _listar_regimento_itens(incluir_inativos=incluir_inativos)


def remover_alinea(alinea_id: int):
    return _remover_alinea(alinea_id)


def remover_artigo(artigo_id: int):
    return _remover_artigo(artigo_id)


def remover_estudante(estudante_id: int):
    return _remover_estudante(estudante_id)


def remover_inciso(inciso_id: int):
    return _remover_inciso(inciso_id)


def remover_lei(lei_id: int):
    return _remover_lei(lei_id)


def remover_ocorrencia(ocorrencia_id: int):
    return _remover_ocorrencia(ocorrencia_id)


def remover_regimento_item(regimento_item_id: int):
    return _remover_regimento_item(regimento_item_id)


def salvar_ocorrencia_estudantes_vinculados(ocorrencia_id: int, estudantes: list[dict]):
    return _salvar_ocorrencia_estudantes_vinculados(ocorrencia_id, estudantes)


def salvar_ocorrencia_professores_vinculados(ocorrencia_id: int, professores: list[dict]):
    return _salvar_ocorrencia_professores_vinculados(ocorrencia_id, professores)


def salvar_regimento_itens_ocorrencia(ocorrencia_id: int, regimento_item_ids: list[int]):
    return _salvar_regimento_itens_ocorrencia(ocorrencia_id, regimento_item_ids)


__all__ = [
    "ACAO_OCORRENCIA_VALIDAS",
    "STATUS_OCORRENCIA_REGISTRADO",
    "STATUS_OCORRENCIA_VALIDOS",
    "TIPOS_REGISTRO_OCORRENCIA",
    "atualizar_alinea",
    "atualizar_artigo",
    "atualizar_estudante",
    "atualizar_inciso",
    "atualizar_lei",
    "atualizar_ocorrencia",
    "atualizar_regimento_item",
    "atualizar_status_estudante",
    "atualizar_status_regimento_item",
    "buscar_alinea_por_id",
    "buscar_artigo_por_id",
    "buscar_estudante_por_id",
    "buscar_estudantes_ocorrencia",
    "buscar_inciso_por_id",
    "buscar_lei_por_id",
    "buscar_ocorrencia_por_id",
    "buscar_professor_por_id_ocorrencia",
    "buscar_professores_ocorrencia",
    "buscar_regimento_item_por_id",
    "buscar_regimento_itens_por_ids",
    "criar_alinea",
    "criar_artigo",
    "criar_estudante",
    "criar_inciso",
    "criar_lei",
    "criar_ocorrencia",
    "criar_regimento_item",
    "listar_alineas",
    "listar_artigos",
    "listar_estudantes",
    "listar_incisos",
    "listar_leis",
    "listar_ocorrencias",
    "listar_regimento_itens",
    "remover_alinea",
    "remover_artigo",
    "remover_estudante",
    "remover_inciso",
    "remover_lei",
    "remover_ocorrencia",
    "remover_regimento_item",
    "salvar_ocorrencia_estudantes_vinculados",
    "salvar_ocorrencia_professores_vinculados",
    "salvar_regimento_itens_ocorrencia",
]
