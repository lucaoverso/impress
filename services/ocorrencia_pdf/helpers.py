from __future__ import annotations

import re
from datetime import datetime

from services.ocorrencia_disciplina_service import (
    inferir_gravidade_ocorrencia,
    rotulo_acao_ocorrencia,
)
from services.ocorrencia_pdf.constants import (
    OFFSET_TURNO,
    STATUS_ROTULOS,
    TIPO_REGISTRO_ESTUDANTE,
    TIPO_REGISTRO_GERAL,
    TIPO_REGISTRO_PROFESSOR,
    TITULO_REGISTRO,
)


def _texto_seguro(valor, padrao: str = "Nao informado") -> str:
    texto = str(valor or "").strip()
    return texto or padrao


def _formatar_data_br(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Nao informada"
    try:
        return datetime.strptime(texto, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return texto


def _formatar_data_hora_br(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return "Nao informado"
    try:
        return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y as %H:%M")
    except ValueError:
        return texto


def _rotulo_acao(valor: str | None) -> str:
    return rotulo_acao_ocorrencia(valor)


def _rotulo_status(valor: str | None) -> str:
    texto = str(valor or "").strip()
    return STATUS_ROTULOS.get(texto, texto or "Nao informado")


def _formatar_aula(ocorrencia: dict, turma: dict | None) -> str:
    texto = str(ocorrencia.get("aula") or "").strip()
    if not texto:
        return "Nao informada"
    if not texto.isdigit():
        return texto

    faixa = int(texto)
    turno = str((turma or {}).get("turno") or "").strip().upper()
    offset = OFFSET_TURNO.get(turno)
    if offset is None:
        return f"Faixa {faixa}"
    if turno == "INTEGRAL":
        if 1 <= faixa <= 5:
            return f"{faixa}a aula"
        if faixa >= 7:
            return f"{faixa - 1}a aula"
        return f"Faixa {faixa}"
    aula_turno = faixa - offset
    return f"{aula_turno}a aula" if aula_turno > 0 else f"Faixa {faixa}"


def _obter_tipo_registro(ocorrencia: dict) -> str:
    tipo = str(ocorrencia.get("tipo_registro") or "").strip().lower()
    if tipo in {TIPO_REGISTRO_ESTUDANTE, TIPO_REGISTRO_PROFESSOR, TIPO_REGISTRO_GERAL}:
        return tipo
    return TIPO_REGISTRO_ESTUDANTE


def _obter_observacao_final(ocorrencia: dict) -> str:
    acao = str(ocorrencia.get("acao_aplicada") or "").strip()
    tipo_registro = _obter_tipo_registro(ocorrencia)
    observacoes = {
        "advertencia_verbal": "OBS.: Aplicada advertencia verbal com orientacao pedagogica, conforme a base legal selecionada.",
        "retirada_sala_orientacao": "OBS.: Aplicada retirada do estudante da sala ou atividade, com encaminhamento para orientacao.",
        "suspensao_extracurricular": "OBS.: Aplicada suspensao temporaria de participacao em programas extracurriculares.",
        "suspensao_orientada_2_dias": "OBS.: Aplicada suspensao orientada das aulas pelo periodo definido pela equipe escolar.",
        "suspensao_aulas_3_dias": "OBS.: Aplicada suspensao das aulas, respeitado o limite previsto na base legal.",
        "transferencia_compulsoria": "OBS.: Aplicada transferencia compulsoria, conforme decisao institucional cabivel ao caso.",
        "orientacao_verbal": "OBS.: O registro fica arquivado para acompanhamento pedagogico e orientacao verbal junto ao estudante.",
        "advertencia": "OBS.: Pela falta de integracao e compromisso e por nao acatar as solicitacoes da docente, recebe esta acao pedagogico-disciplinar de advertencia.",
        "chamada_responsavel": "OBS.: Solicitado o comparecimento do responsavel para alinhamento e acompanhamento conjunto do caso.",
        "encaminhamento_direcao": "OBS.: O registro segue encaminhado a Direcao para providencias e acompanhamento institucional.",
        "registro_informativo": "OBS.: Documento emitido para registro informativo e acompanhamento pedagogico interno.",
        "orientacao_professor": "OBS.: Registro emitido para documentar a orientacao individual feita ao professor, com ciencia formal das partes.",
        "reuniao_alinhamento": "OBS.: Registro emitido para documentar reuniao de alinhamento e pactuacao institucional com o professor.",
        "orientacao_geral_docentes": "OBS.: Registro emitido para documentar orientacao geral apresentada ao corpo docente, com coleta de assinaturas ao final.",
    }
    if acao in observacoes:
        return observacoes[acao]
    if tipo_registro == TIPO_REGISTRO_PROFESSOR:
        return "OBS.: Documento emitido para registro funcional e acompanhamento da orientacao ao professor."
    if tipo_registro == TIPO_REGISTRO_GERAL:
        return "OBS.: Documento emitido para registro institucional de orientacao geral ao corpo docente."
    return f"OBS.: Documento emitido para registro e acompanhamento da acao aplicada: {_rotulo_acao(acao)}."


def _obter_estudantes_vinculados_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("estudantes_vinculados")
    if not isinstance(itens, list):
        return []
    return [
        {
            "estudante_id": item.get("estudante_id"),
            "nome": str(item.get("nome") or "").strip(),
            "turma_id": item.get("turma_id"),
            "turma_nome": str(item.get("turma_nome") or "").strip(),
        }
        for item in itens
        if isinstance(item, dict) and str(item.get("nome") or "").strip()
    ]


def _obter_professores_vinculados_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("professores_vinculados")
    if not isinstance(itens, list):
        return []
    return [
        {
            "professor_id": item.get("professor_id"),
            "nome": str(item.get("nome") or "").strip(),
            "email": str(item.get("email") or "").strip(),
        }
        for item in itens
        if isinstance(item, dict) and str(item.get("nome") or "").strip()
    ]


def _obter_gravidade_ocorrencia(ocorrencia: dict) -> str | None:
    if _obter_tipo_registro(ocorrencia) != TIPO_REGISTRO_ESTUDANTE:
        return None
    from services.ocorrencia_pdf.base_legal import _obter_itens_regimento_ocorrencia

    return inferir_gravidade_ocorrencia(_obter_itens_regimento_ocorrencia(ocorrencia))


def _obter_titulo_documento(ocorrencia: dict) -> str:
    acao = str(ocorrencia.get("acao_aplicada") or "").strip()
    if not acao:
        tipo_registro = _obter_tipo_registro(ocorrencia)
        if tipo_registro == TIPO_REGISTRO_PROFESSOR:
            return "REGISTRO INDIVIDUAL DE PROFESSOR"
        if tipo_registro == TIPO_REGISTRO_GERAL:
            return "REGISTRO GERAL AOS PROFESSORES"
        return TITULO_REGISTRO
    return _rotulo_acao(acao).upper()


def _campos_resumo_registro(ocorrencia: dict, turma: dict | None) -> list[tuple[str, str]]:
    tipo_registro = _obter_tipo_registro(ocorrencia)
    referencia = _texto_seguro(ocorrencia.get("nome_estudante"))
    professor = _texto_seguro(ocorrencia.get("professor_requerente"))
    disciplina = _texto_seguro(ocorrencia.get("disciplina"))
    data = _formatar_data_br(ocorrencia.get("data_ocorrencia"))
    horario = _texto_seguro(ocorrencia.get("horario_ocorrencia"))
    acao = _rotulo_acao(ocorrencia.get("acao_aplicada"))
    status = _rotulo_status(ocorrencia.get("status"))

    if tipo_registro == TIPO_REGISTRO_PROFESSOR:
        total_professores = len(_obter_professores_vinculados_ocorrencia(ocorrencia))
        return [
            ("Professor(es)" if total_professores > 1 else "Professor", professor),
            ("Assunto ou pauta", disciplina),
            ("Data", data),
            ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
            ("Acao aplicada", acao),
            ("Status", status),
        ]
    if tipo_registro == TIPO_REGISTRO_GERAL:
        return [
            ("Registro geral", referencia),
            ("Publico", professor),
            ("Tema ou pauta", disciplina),
            ("Data", data),
            ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
            ("Acao aplicada", acao),
            ("Status", status),
        ]

    turma_nome = _texto_seguro(ocorrencia.get("turma_nome"))
    aula = _formatar_aula(ocorrencia, turma)
    total_estudantes = len(_obter_estudantes_vinculados_ocorrencia(ocorrencia))
    return [
        ("Estudante(s)" if total_estudantes > 1 else "Estudante", referencia),
        ("Turma", turma_nome),
        ("Professor requerente", professor),
        ("Disciplina ou funcao", disciplina),
        ("Data", data),
        ("Aula", aula),
        ("Horario", f"As {horario} h" if horario != "Nao informado" else horario),
        ("Acao aplicada", acao),
        ("Status", status),
    ]
