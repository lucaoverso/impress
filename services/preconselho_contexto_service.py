from db.catalogos import listar_disciplinas_ativas, listar_turmas_ativas
from db.ocorrencias import listar_estudantes
from db.usuarios import listar_professores_agendamento
from repositories.preconselho_repository import (
    contar_registros_pre_conselho_por_professor_periodo,
    listar_estudantes_pre_conselho_painel,
    listar_motivos_pre_conselho,
    listar_periodos_pre_conselho,
)
from services.preconselho_service import (
    STATUS_PERIODO_PRE_CONSELHO_ABERTO,
    listar_motivos_pos_pre_conselho,
    listar_niveis_atencao_pre_conselho,
    periodo_editavel_para_cargo,
)
from services.preconselho_validacao_service import (
    opcoes_professor_preconselho,
    resolver_professor_preconselho,
    usuario_eh_admin_preconselho,
    usuario_eh_gestor_preconselho,
    usuario_eh_professor_preconselho,
    validar_disciplina_preconselho,
    validar_escopo_professor_preconselho,
    validar_periodo_preconselho,
    validar_turma_preconselho,
    escopo_professor_preconselho,
    normalizar_cargo_preconselho,
    obter_usuario_id_preconselho,
)


def minhas_turmas_disciplinas_preconselho(periodo_id: int, professor_id: int) -> list[dict]:
    validar_periodo_preconselho(periodo_id)
    escopo = escopo_professor_preconselho(professor_id)
    registros = contar_registros_pre_conselho_por_professor_periodo(
        professor_id=professor_id,
        periodo_id=periodo_id,
    )
    estudantes_por_turma = {
        int(turma["id"]): len(
            listar_estudantes(nome="", incluir_inativos=False, turma_id=int(turma["id"]))
        )
        for turma in escopo["turmas"]
    }
    itens = []
    for combinacao in escopo["combinacoes"]:
        turma_id = int(combinacao["turma_id"])
        disciplina_id = int(combinacao["disciplina_id"])
        total_estudantes = int(estudantes_por_turma.get(turma_id, 0))
        total_sinalizados = int(registros.get((turma_id, disciplina_id), 0))
        itens.append(
            {
                "turma_id": turma_id,
                "turma_nome": combinacao["turma_nome"],
                "turno": combinacao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": combinacao["disciplina_nome"],
                "total_estudantes": total_estudantes,
                "total_sinalizados": total_sinalizados,
                "total_pendentes": max(total_estudantes - total_sinalizados, 0),
            }
        )
    return itens


def obter_contexto_preconselho(usuario: dict) -> dict:
    cargo = normalizar_cargo_preconselho(usuario)
    usuario_id = obter_usuario_id_preconselho(usuario)
    turmas_professor, disciplinas_professor = (
        opcoes_professor_preconselho(usuario_id)
        if usuario_eh_professor_preconselho(usuario)
        else ([], [])
    )
    periodos = listar_periodos_pre_conselho()
    periodo_referencia = next(
        (item for item in periodos if item.get("status") == STATUS_PERIODO_PRE_CONSELHO_ABERTO),
        None,
    )
    minhas_turmas_disciplinas = (
        minhas_turmas_disciplinas_preconselho(int(periodo_referencia["id"]), usuario_id)
        if usuario_eh_professor_preconselho(usuario) and periodo_referencia
        else []
    )
    return {
        "cargo": cargo,
        "pode_configurar": usuario_eh_admin_preconselho(usuario),
        "pode_consolidar": usuario_eh_gestor_preconselho(usuario),
        "pode_relatorio": usuario_eh_gestor_preconselho(usuario),
        "pode_editar_periodo_fechado": usuario_eh_admin_preconselho(usuario),
        "professor_id": usuario_id if usuario_eh_professor_preconselho(usuario) else None,
        "professor_nome": str(usuario.get("nome") or "").strip()
        if usuario_eh_professor_preconselho(usuario)
        else "",
        "periodos": [
            {
                **item,
                "editavel": periodo_editavel_para_cargo(item.get("status"), cargo),
            }
            for item in periodos
        ],
        "turmas": turmas_professor if usuario_eh_professor_preconselho(usuario) else listar_turmas_ativas(),
        "disciplinas": disciplinas_professor
        if usuario_eh_professor_preconselho(usuario)
        else listar_disciplinas_ativas(),
        "motivos": listar_motivos_pre_conselho(
            incluir_inativos=usuario_eh_admin_preconselho(usuario)
        ),
        "professores": [
            {
                "id": int(item["id"]),
                "nome": item["nome"],
                "email": item.get("email", ""),
                "label": (
                    f"{item['nome']} ({item.get('email', '')})"
                    if str(item.get("email", "")).strip()
                    else item["nome"]
                ),
            }
            for item in listar_professores_agendamento()
        ]
        if usuario_eh_gestor_preconselho(usuario)
        else [],
        "niveis_atencao": listar_niveis_atencao_pre_conselho(),
        "motivos_pos_preconselho": listar_motivos_pos_pre_conselho(),
        "minhas_turmas_disciplinas": minhas_turmas_disciplinas,
    }


def listar_estudantes_painel_preconselho(
    *,
    periodo_id: int,
    turma_id: int,
    disciplina_id: int,
    q: str,
    status: str,
    professor_id: int | None,
    usuario: dict,
) -> list[dict]:
    periodo = validar_periodo_preconselho(periodo_id)
    turma = validar_turma_preconselho(turma_id)
    disciplina = validar_disciplina_preconselho(disciplina_id)
    professor = resolver_professor_preconselho(usuario, professor_id, permitir_gestor=True)
    validar_escopo_professor_preconselho(
        int(professor["id"]),
        int(turma["id"]),
        int(disciplina["id"]),
    )
    return listar_estudantes_pre_conselho_painel(
        periodo_id=int(periodo["id"]),
        turma_id=int(turma["id"]),
        disciplina_id=int(disciplina["id"]),
        professor_usuario_id=int(professor["id"]),
        busca_nome=q,
        status=status,
    )
