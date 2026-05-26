from repositories.ocorrencias_repository import (
    atualizar_regimento_item,
    atualizar_status_regimento_item,
    buscar_regimento_item_por_id,
    criar_regimento_item,
    listar_regimento_itens,
    remover_regimento_item,
)
from services.csv_import_service import importar_base_legal_arquivo


def _texto_obrigatorio_regimento(valor: str | None, *, campo: str, max_len: int) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional_regimento(valor: str | None, *, max_len: int) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > max_len:
        raise ValueError(f"Texto excede o limite de {max_len} caracteres.")
    return texto


def _model_to_dict_regimento(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=False)
    if hasattr(model, "dict"):
        return model.dict(exclude_unset=False)
    return dict(model)


def _normalizar_payload_regimento(payload) -> dict:
    dados_brutos = _model_to_dict_regimento(payload)
    lei_nome = (
        _texto_obrigatorio_regimento(dados_brutos.get("lei_nome"), campo="Lei", max_len=120)
        if str(dados_brutos.get("lei_nome") or "").strip()
        else "Base legal"
    )
    artigo_numero = _texto_obrigatorio_regimento(
        dados_brutos.get("artigo_numero") or dados_brutos.get("artigo"),
        campo="Numero do artigo",
        max_len=120,
    )
    artigo_descricao = _texto_obrigatorio_regimento(
        dados_brutos.get("artigo_descricao") or dados_brutos.get("descricao"),
        campo="Descricao do artigo",
        max_len=5000,
    )
    inciso_numero = _texto_opcional_regimento(dados_brutos.get("inciso_numero"), max_len=40)
    inciso_descricao = _texto_opcional_regimento(
        dados_brutos.get("inciso_descricao"),
        max_len=5000,
    )
    alinea_identificador = _texto_opcional_regimento(
        dados_brutos.get("alinea_identificador"),
        max_len=40,
    )
    alinea_descricao = _texto_opcional_regimento(
        dados_brutos.get("alinea_descricao"),
        max_len=5000,
    )

    if bool(inciso_numero) != bool(inciso_descricao):
        raise ValueError("Inciso e descricao do inciso devem ser informados juntos.")
    if alinea_identificador and not inciso_numero:
        raise ValueError("Informe um inciso antes de cadastrar uma alinea.")
    if bool(alinea_identificador) != bool(alinea_descricao):
        raise ValueError("Alinea e descricao da alinea devem ser informadas juntas.")

    return {
        "lei_nome": lei_nome,
        "artigo_numero": artigo_numero,
        "artigo_descricao": artigo_descricao,
        "inciso_numero": inciso_numero,
        "inciso_descricao": inciso_descricao,
        "alinea_identificador": alinea_identificador,
        "alinea_descricao": alinea_descricao,
    }


def listar_regimento_itens_service(*, incluir_inativos: bool = True) -> list[dict]:
    return listar_regimento_itens(incluir_inativos=incluir_inativos)


def buscar_regimento_item_service(regimento_item_id: int) -> dict:
    item = buscar_regimento_item_por_id(regimento_item_id)
    if not item:
        raise LookupError("Item do regimento nao encontrado.")
    return item


def criar_regimento_item_service(payload) -> dict:
    dados = _normalizar_payload_regimento(payload)
    regimento_item_id = criar_regimento_item(
        lei_nome=dados["lei_nome"],
        artigo_numero=dados["artigo_numero"],
        artigo_descricao=dados["artigo_descricao"],
        inciso_numero=dados["inciso_numero"],
        inciso_descricao=dados["inciso_descricao"],
        alinea_identificador=dados["alinea_identificador"],
        alinea_descricao=dados["alinea_descricao"],
    )
    return buscar_regimento_item_service(regimento_item_id)


def importar_regimento_itens_arquivo_service(
    *,
    conteudo: bytes,
    nome_arquivo: str,
    tipo_conteudo: str,
) -> dict:
    return importar_base_legal_arquivo(
        conteudo,
        nome_arquivo=nome_arquivo,
        tipo_conteudo=tipo_conteudo,
    )


def atualizar_regimento_item_service(*, regimento_item_id: int, payload) -> dict:
    buscar_regimento_item_service(regimento_item_id)
    dados = _normalizar_payload_regimento(payload)
    alterado = atualizar_regimento_item(
        regimento_item_id=regimento_item_id,
        lei_nome=dados["lei_nome"],
        artigo_numero=dados["artigo_numero"],
        artigo_descricao=dados["artigo_descricao"],
        inciso_numero=dados["inciso_numero"],
        inciso_descricao=dados["inciso_descricao"],
        alinea_identificador=dados["alinea_identificador"],
        alinea_descricao=dados["alinea_descricao"],
        ativo=bool(payload.ativo),
    )
    if not alterado:
        raise LookupError("Item do regimento nao encontrado.")
    return buscar_regimento_item_service(regimento_item_id)


def atualizar_status_regimento_item_service(*, regimento_item_id: int, ativo: bool) -> None:
    alterado = atualizar_status_regimento_item(regimento_item_id, ativo)
    if not alterado:
        raise LookupError("Item do regimento nao encontrado.")


def remover_regimento_item_service(regimento_item_id: int) -> None:
    removido = remover_regimento_item(regimento_item_id)
    if not removido:
        raise LookupError("Item do regimento nao encontrado.")
