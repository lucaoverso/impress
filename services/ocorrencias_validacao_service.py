from __future__ import annotations

import re
from datetime import datetime

from db.catalogos import buscar_turma_por_id
from repositories.ocorrencias_repository import (
    ACAO_OCORRENCIA_VALIDAS,
    STATUS_OCORRENCIA_VALIDOS,
    TIPOS_REGISTRO_OCORRENCIA,
    buscar_regimento_itens_por_ids,
)
from services.ocorrencia_disciplina_service import acao_permitida_para_tipo_registro

TIPO_REGISTRO_ESTUDANTE = "estudante"
TIPO_REGISTRO_PROFESSOR = "professor"
TIPO_REGISTRO_GERAL = "geral"

_HORARIO_REGEX = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
_TURNOS_CONFIG = {
    "INTEGRAL": {"nome": "Periodo integral", "aulas": 8},
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 6},
    "VESPERTINO_EM": {"nome": "Vespertino E.M.", "aulas": 6},
}
_FAIXA_GLOBAL_OFFSET_POR_TURNO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}


def model_to_dict_ocorrencia(model, *, exclude_unset: bool = False) -> dict:
    if isinstance(model, dict):
        return dict(model)
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    if hasattr(model, "dict"):
        return model.dict(exclude_unset=exclude_unset)
    return {
        chave: valor
        for chave, valor in vars(model).items()
        if not exclude_unset or valor is not None
    }


def texto_obrigatorio_ocorrencia(valor: str | None, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def texto_opcional_ocorrencia(valor: str | None, *, max_len: int = 255) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if len(texto) > max_len:
        raise ValueError(f"Texto excede o limite de {max_len} caracteres.")
    return texto


def validar_data_iso_ocorrencia(valor: str, campo: str) -> str:
    texto = texto_obrigatorio_ocorrencia(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def validar_horario_ocorrencia_service(valor: str) -> str:
    texto = texto_obrigatorio_ocorrencia(valor, "Horario da ocorrencia", max_len=30)
    if _HORARIO_REGEX.match(texto):
        formato = "%H:%M:%S" if texto.count(":") == 2 else "%H:%M"
        try:
            datetime.strptime(texto, formato)
        except ValueError as exc:
            raise ValueError("Horario da ocorrencia invalido.") from exc
    return texto


def validar_status_ocorrencia(valor: str) -> str:
    status = str(valor or "").strip()
    if status not in STATUS_OCORRENCIA_VALIDOS:
        raise ValueError("Status invalido.")
    return status


def validar_acao_aplicada_ocorrencia(valor: str) -> str:
    acao = str(valor or "").strip()
    if acao not in ACAO_OCORRENCIA_VALIDAS:
        raise ValueError("Acao aplicada invalida.")
    return acao


def validar_acao_aplicada_para_tipo_ocorrencia(acao: str, tipo_registro: str) -> str:
    acao_valida = validar_acao_aplicada_ocorrencia(acao)
    if not acao_permitida_para_tipo_registro(acao_valida, tipo_registro):
        raise ValueError("Acao aplicada invalida para o tipo de registro selecionado.")
    return acao_valida


def validar_tipo_registro_ocorrencia(valor: str | None) -> str:
    tipo = str(valor or TIPO_REGISTRO_ESTUDANTE).strip().lower()
    if tipo not in TIPOS_REGISTRO_OCORRENCIA:
        raise ValueError("Tipo de registro invalido.")
    return tipo


def registro_exige_base_legal_ocorrencia(tipo_registro: str) -> bool:
    return tipo_registro == TIPO_REGISTRO_ESTUDANTE


def registro_exige_aula_ocorrencia(tipo_registro: str) -> bool:
    return tipo_registro == TIPO_REGISTRO_ESTUDANTE


def validar_turma_id_ocorrencia(turma_id: int) -> int:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Turma invalida.") from exc
    if turma_id_valor <= 0:
        raise ValueError("Turma invalida.")
    if not buscar_turma_por_id(turma_id_valor):
        raise ValueError("Turma invalida.")
    return turma_id_valor


def _normalizar_turno_turma_ocorrencia(valor: str | None) -> str:
    return str(valor or "").strip().upper()


def _faixa_global_por_turno_e_aula_ocorrencia(turno: str, aula_turno: int) -> int:
    faixa_global = int(aula_turno) + _FAIXA_GLOBAL_OFFSET_POR_TURNO[turno]
    if turno == "INTEGRAL" and int(aula_turno) > 5:
        faixa_global += 1
    return faixa_global


def _faixas_disponiveis_turno_ocorrencia(turno: str) -> list[int]:
    turno_normalizado = _normalizar_turno_turma_ocorrencia(turno)
    config_turno = _TURNOS_CONFIG.get(turno_normalizado)
    if not config_turno:
        return []
    faixas = []
    total_aulas = int(config_turno["aulas"])
    for aula_turno in range(1, total_aulas + 1):
        faixas.append(_faixa_global_por_turno_e_aula_ocorrencia(turno_normalizado, aula_turno))
    return faixas


def validar_faixa_aula_por_turma_ocorrencia(aula: str | None, turma_id: int) -> str:
    texto_aula = texto_obrigatorio_ocorrencia(aula, "Aula", max_len=20)
    if not texto_aula.isdigit():
        raise ValueError("Aula invalida. Selecione uma faixa valida.")
    faixa_global = int(texto_aula)
    if faixa_global <= 0:
        raise ValueError("Aula invalida. Selecione uma faixa valida.")
    turma = buscar_turma_por_id(turma_id)
    if not turma:
        raise ValueError("Turma invalida.")
    turno_turma = _normalizar_turno_turma_ocorrencia(turma.get("turno"))
    config_turno = _TURNOS_CONFIG.get(turno_turma)
    if not config_turno:
        raise ValueError("Turma sem turno configurado. Atualize o cadastro da turma.")
    if faixa_global not in set(_faixas_disponiveis_turno_ocorrencia(turno_turma)):
        raise ValueError("Faixa de aula invalida para o turno da turma selecionada.")
    return str(faixa_global)


def validar_estudante_id_ocorrencia(estudante_id: int | None) -> int | None:
    if estudante_id is None:
        return None
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Estudante invalido.") from exc
    if estudante_id_valor <= 0:
        raise ValueError("Estudante invalido.")
    return estudante_id_valor


def validar_professor_id_ocorrencia(
    professor_id: int | None, *, campo: str = "Professor requerente"
) -> int | None:
    if professor_id is None:
        return None
    try:
        professor_id_valor = int(professor_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{campo} invalido.") from exc
    if professor_id_valor <= 0:
        raise ValueError(f"{campo} invalido.")
    return professor_id_valor


def normalizar_regimento_item_ids_ocorrencia(valores: list[int] | None) -> list[int]:
    ids_norm = []
    vistos = set()
    for valor in valores or []:
        try:
            regimento_item_id = int(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError("Item do regimento invalido.") from exc
        if regimento_item_id <= 0:
            raise ValueError("Item do regimento invalido.")
        if regimento_item_id in vistos:
            continue
        vistos.add(regimento_item_id)
        ids_norm.append(regimento_item_id)
    if not ids_norm:
        return []
    itens = buscar_regimento_itens_por_ids(ids_norm)
    if len(itens) != len(ids_norm):
        raise ValueError("Um ou mais itens do regimento nao foram encontrados.")
    return ids_norm


def exigir_regimento_item_ids_ocorrencia(ids_norm: list[int]) -> list[int]:
    if not ids_norm:
        raise ValueError("Selecione ao menos uma base legal para vincular a ocorrencia.")
    return ids_norm
