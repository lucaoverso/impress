import re
import unicodedata
from datetime import datetime

from fastapi import HTTPException, UploadFile

from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import (
    STATUS_OCORRENCIA_VALIDOS,
    TIPOS_REGISTRO_OCORRENCIA,
    buscar_alinea_por_id,
    buscar_artigo_por_id,
    buscar_estudante_por_id,
    buscar_inciso_por_id,
    buscar_lei_por_id,
    buscar_ocorrencia_por_id,
    buscar_regimento_item_por_id,
)
from routers.common import usuario_tem_acesso_coordenacao


def _model_to_dict(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _exigir_gestor(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado")
    return usuario


def _texto_obrigatorio(valor: str | None, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise HTTPException(400, f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def _texto_opcional(valor: str | None, *, max_len: int = 255) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > max_len:
        raise HTTPException(400, f"Texto excede o limite de {max_len} caracteres.")
    return texto


def _validar_data_iso(valor: str, campo: str) -> str:
    texto = _texto_obrigatorio(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(400, f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def _validar_data_opcional(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return _validar_data_iso(texto, campo)


def _validar_turma_id(turma_id: int) -> int:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Turma invalida.") from exc
    if turma_id_valor <= 0:
        raise HTTPException(400, "Turma invalida.")

    turma = buscar_turma_por_id(turma_id_valor)
    if not turma:
        raise HTTPException(400, "Turma invalida.")
    return turma_id_valor


def _validar_status(status: str | None) -> str:
    status_normalizado = _texto_obrigatorio(status, "Status", max_len=60).lower()
    if status_normalizado not in STATUS_OCORRENCIA_VALIDOS:
        raise HTTPException(400, "Status invalido.")
    return status_normalizado


def _validar_tipo_registro(tipo_registro: str | None) -> str:
    tipo_normalizado = _texto_obrigatorio(tipo_registro, "Tipo de registro", max_len=60).lower()
    if tipo_normalizado not in TIPOS_REGISTRO_OCORRENCIA:
        raise HTTPException(400, "Tipo de registro invalido.")
    return tipo_normalizado


def _montar_resposta_ocorrencia(ocorrencia_id: int) -> dict:
    ocorrencia = buscar_ocorrencia_por_id(ocorrencia_id)
    if not ocorrencia:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    return ocorrencia


def _slug_ascii(texto: str) -> str:
    texto_normalizado = unicodedata.normalize("NFKD", str(texto or "").strip())
    texto_ascii = texto_normalizado.encode("ascii", "ignore").decode("ascii")
    texto_limpo = re.sub(r"[^A-Za-z0-9]+", "_", texto_ascii).strip("_").lower()
    return texto_limpo or "ocorrencia"


def _nome_arquivo_pdf_ocorrencia(ocorrencia: dict) -> str:
    estudante = _slug_ascii(ocorrencia.get("nome_estudante") or "ocorrencia")
    data = str(ocorrencia.get("data_ocorrencia") or "").strip() or datetime.now().date().isoformat()
    data_limpa = re.sub(r"[^0-9-]+", "", data) or datetime.now().date().isoformat()
    return f"registro_ocorrencia_{estudante}_{data_limpa}.pdf"


def _montar_resposta_estudante(estudante_id: int) -> dict:
    estudante = buscar_estudante_por_id(estudante_id)
    if not estudante:
        raise HTTPException(404, "Estudante nao encontrado.")
    return estudante


def _montar_resposta_regimento_item(regimento_item_id: int) -> dict:
    item = buscar_regimento_item_por_id(regimento_item_id)
    if not item:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return item


def _montar_resposta_lei(lei_id: int) -> dict:
    lei = buscar_lei_por_id(lei_id)
    if not lei:
        raise HTTPException(404, "Lei nao encontrada.")
    return lei


def _montar_resposta_artigo(artigo_id: int) -> dict:
    artigo = buscar_artigo_por_id(artigo_id)
    if not artigo:
        raise HTTPException(404, "Artigo nao encontrado.")
    return artigo


def _montar_resposta_inciso(inciso_id: int) -> dict:
    inciso = buscar_inciso_por_id(inciso_id)
    if not inciso:
        raise HTTPException(404, "Inciso nao encontrado.")
    return inciso


def _montar_resposta_alinea(alinea_id: int) -> dict:
    alinea = buscar_alinea_por_id(alinea_id)
    if not alinea:
        raise HTTPException(404, "Alinea nao encontrada.")
    return alinea


def _normalizar_payload_regimento(payload) -> dict:
    dados_brutos = _model_to_dict(payload, exclude_unset=False)
    lei_nome = (
        _texto_obrigatorio(dados_brutos.get("lei_nome"), "Lei", max_len=120)
        if str(dados_brutos.get("lei_nome") or "").strip()
        else "Base legal"
    )
    artigo_numero = _texto_obrigatorio(
        dados_brutos.get("artigo_numero") or dados_brutos.get("artigo"),
        "Numero do artigo",
        max_len=120,
    )
    artigo_descricao = _texto_obrigatorio(
        dados_brutos.get("artigo_descricao") or dados_brutos.get("descricao"),
        "Descricao do artigo",
        max_len=5000,
    )
    inciso_numero = _texto_opcional(dados_brutos.get("inciso_numero"), max_len=40)
    inciso_descricao = _texto_opcional(dados_brutos.get("inciso_descricao"), max_len=5000)
    alinea_identificador = _texto_opcional(dados_brutos.get("alinea_identificador"), max_len=40)
    alinea_descricao = _texto_opcional(dados_brutos.get("alinea_descricao"), max_len=5000)

    if bool(inciso_numero) != bool(inciso_descricao):
        raise HTTPException(400, "Inciso e descricao do inciso devem ser informados juntos.")
    if alinea_identificador and not inciso_numero:
        raise HTTPException(400, "Informe um inciso antes de cadastrar uma alinea.")
    if bool(alinea_identificador) != bool(alinea_descricao):
        raise HTTPException(400, "Alinea e descricao da alinea devem ser informadas juntas.")

    return {
        "lei_nome": lei_nome,
        "artigo_numero": artigo_numero,
        "artigo_descricao": artigo_descricao,
        "inciso_numero": inciso_numero,
        "inciso_descricao": inciso_descricao,
        "alinea_identificador": alinea_identificador,
        "alinea_descricao": alinea_descricao,
    }


def _ler_upload_estudantes(arquivo: UploadFile) -> tuple[bytes, str, str]:
    nome_arquivo = str(getattr(arquivo, "filename", "") or "").strip()
    if not nome_arquivo:
        raise HTTPException(400, "Arquivo de estudantes nao enviado.")

    tipo_conteudo = str(getattr(arquivo, "content_type", "") or "").lower()
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(
        ".csv"
    )
    tipo_valido = "json" in tipo_conteudo or "csv" in tipo_conteudo or "text/plain" in tipo_conteudo
    if not extensao_valida and not tipo_valido:
        raise HTTPException(400, "Envie um arquivo JSON ou CSV valido.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo de estudantes vazio.")
    return conteudo, nome_arquivo, tipo_conteudo


def _ler_upload_base_legal(arquivo: UploadFile) -> tuple[bytes, str, str]:
    nome_arquivo = str(getattr(arquivo, "filename", "") or "").strip()
    if not nome_arquivo:
        raise HTTPException(400, "Arquivo da base legal nao enviado.")

    tipo_conteudo = str(getattr(arquivo, "content_type", "") or "").lower()
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(
        ".csv"
    )
    tipo_valido = "json" in tipo_conteudo or "csv" in tipo_conteudo or "text/plain" in tipo_conteudo
    if not extensao_valida and not tipo_valido:
        raise HTTPException(400, "Envie um arquivo JSON ou CSV valido.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo da base legal vazio.")
    return conteudo, nome_arquivo, tipo_conteudo
