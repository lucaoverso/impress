from repositories.pcpi_repository import (
    criar_e_buscar_registro_pcpi_manual,
    listar_agendamentos_pcpi_por_data,
    listar_cargas_professores_pcpi_por_usuario_ids,
    listar_registros_pcpi_manuais_por_data,
)
from services.pcpi_common_service import (
    GRUPO_AUTOMATICO_APOIO,
    GRUPO_AUTOMATICO_AUDIOVISUAL,
    GRUPO_AUTOMATICO_STE,
    GRUPO_AUTOMATICO_TECNOLOGIA,
    TIPOS_ACAO_PCPI,
    TURNOS_AGENDAMENTO_POR_TURNO_PCPI,
    TURNOS_PCPI_CONFIG,
    FECHAMENTO_PCPI_PADRAO,
    agendamento_pertence_ao_turno_pcpi,
    nome_turno_pcpi,
    obter_usuario_id_pcpi,
    turno_agendamento_pertence_ao_turno_pcpi,
    validar_data_pcpi,
    validar_texto_obrigatorio_pcpi,
    validar_texto_opcional_pcpi,
    validar_turno_pcpi,
)
from services.pcpi_sugestoes_service import (
    classificar_categoria_uso,
    filtrar_itens_automaticos_pcpi,
    montar_contexto_pcpi,
    montar_listagem_registros_manuais_pcpi,
    montar_sugestoes_pcpi,
    normalizar_agendamento_pcpi,
    normalizar_registros_manuais_pcpi,
)
from services.pcpi_texto_service import (
    gerar_frases_automaticas_pcpi,
    gerar_frases_registros_manuais_pcpi,
    gerar_texto_base_pcpi,
    gerar_texto_pcpi,
)


def carregar_contexto_pcpi(data: str, turno: str) -> tuple[dict, list[dict]]:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    agendamentos_dia = listar_agendamentos_pcpi_por_data(data_norm)
    cargas = listar_cargas_professores_pcpi_por_usuario_ids(
        [
            int(item.get("usuario_id") or 0)
            for item in agendamentos_dia
            if agendamento_pertence_ao_turno_pcpi(item, turno_norm)
        ]
    )
    registros = listar_registros_pcpi_manuais_por_data(data=data_norm)
    return montar_contexto_pcpi(data_norm, turno_norm, agendamentos_dia, cargas, registros)


def listar_registros_manuais_pcpi(data: str, turno: str) -> dict:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    registros = listar_registros_pcpi_manuais_por_data(data=data_norm)
    return montar_listagem_registros_manuais_pcpi(data_norm, turno_norm, registros)


def criar_registro_manual_pcpi(payload, usuario: dict) -> dict:
    data_norm = validar_data_pcpi(payload.data)
    turno_norm = validar_turno_pcpi(payload.turno)
    professor_nome = validar_texto_opcional_pcpi(
        payload.professor_nome,
        "Professor ou setor",
        max_len=160,
    )
    componente = validar_texto_opcional_pcpi(
        payload.componente,
        "Componente ou recurso",
        max_len=160,
    )
    turma = validar_texto_opcional_pcpi(payload.turma, "Turma", max_len=120)
    descricao_curta = validar_texto_obrigatorio_pcpi(
        payload.descricao_curta,
        "Descricao curta",
        max_len=500,
    )
    observacoes = validar_texto_opcional_pcpi(payload.observacoes, "Observacoes", max_len=2000)
    usuario_id = obter_usuario_id_pcpi(usuario)

    return criar_e_buscar_registro_pcpi_manual(
        data=data_norm,
        turno=turno_norm,
        tipo_acao=str(payload.tipo_acao).strip(),
        professor_nome=professor_nome,
        componente=componente,
        turma=turma,
        descricao_curta=descricao_curta,
        observacoes=observacoes,
        criado_por_usuario_id=usuario_id,
        atualizado_por_usuario_id=usuario_id,
    )


def gerar_texto_completo_pcpi(data: str, turno: str) -> dict:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    sugestoes, registros = carregar_contexto_pcpi(data_norm, turno_norm)
    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=sugestoes.get("itens") or [],
        registros_manuais=registros,
    )


def gerar_texto_preview_pcpi(data: str, turno: str, agendamento_ids: list[int] | None) -> dict:
    data_norm = validar_data_pcpi(data)
    turno_norm = validar_turno_pcpi(turno)
    sugestoes, registros = carregar_contexto_pcpi(data_norm, turno_norm)
    itens_automaticos = filtrar_itens_automaticos_pcpi(
        sugestoes.get("itens") or [],
        agendamento_ids,
    )
    return gerar_texto_pcpi(
        data=data_norm,
        turno=turno_norm,
        itens_automaticos=itens_automaticos,
        registros_manuais=registros,
    )
