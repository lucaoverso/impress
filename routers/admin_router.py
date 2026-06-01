import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_usuario_logado
from db.catalogos import (
    atualizar_disciplina_dados,
    atualizar_recurso_dados,
    atualizar_status_disciplina,
    atualizar_status_recurso,
    atualizar_status_turma,
    atualizar_turma_dados,
    criar_disciplina,
    criar_recurso,
    criar_turma,
    listar_disciplinas,
    listar_disciplinas_ativas,
    listar_recursos,
    listar_turmas,
    listar_turmas_ativas,
)
from db.docencia import (
    atualizar_turma_disciplina,
    criar_atribuicao_docente,
    criar_ou_atualizar_turma_disciplina,
    excluir_atribuicao_docente,
    excluir_turma_disciplina,
    listar_atribuicoes_docentes,
    listar_turmas_disciplinas_admin,
    salvar_carga_professor,
    sincronizar_atribuicoes_docentes_professor_disciplina,
)
from db.impressao import (
    atualizar_regras_cota,
    atualizar_status_impressao,
    calcular_cotas_mensais_professores,
    gerar_relatorio_impressao,
    gerar_relatorio_uso_recursos,
    gerar_relatorio_uso_recursos_por_professor,
    listar_historico,
    listar_jobs_ativos,
    obter_status_impressao,
    obter_regras_cota,
    recalcular_cotas_mes,
)
from db.usuarios import (
    atualizar_professor,
    atualizar_senha_usuario,
    buscar_usuario_por_id,
    criar_coordenador,
    criar_professor,
    desativar_professor,
    listar_coordenadores_admin,
    listar_professores_admin,
    listar_professores_agendamento,
    promover_professor_para_coordenador,
    revogar_tokens_usuario,
)
from models import (
    CoordenadorCreateIn,
    DisciplinaCreateIn,
    DisciplinaUpdateIn,
    ProfessorCargaIn,
    ProfessorCreateIn,
    ProfessorDisciplinaTurmasSyncIn,
    ProfessorRedefinirSenhaAdminIn,
    ProfessorTurmaDisciplinaCreateIn,
    ProfessorTurmaDisciplinaOut,
    ProfessorUpdateIn,
    ImpressaoStatusIn,
    RecursoCreateIn,
    RecursoStatusIn,
    RecursoUpdateIn,
    RegrasCotaIn,
    TurmaCreateIn,
    TurmaDisciplinaCreateIn,
    TurmaDisciplinaOut,
    TurmaDisciplinaUpdateIn,
    TurmaUpdateIn,
)
from security.nt_hash import generate_nt_hash
from services.atribuicoes_docentes_import_service import importar_atribuicoes_docentes_arquivo
from services.auth_service import hash_senha

from .common import (
    CARGO_PROFESSOR,
    exigir_admin,
    exigir_gestor,
    mes_atual_referencia,
    normalizar_cargo_usuario,
    obter_opcoes_cadastro_professor,
    validar_data_agendamento,
    validar_senha_forte,
    validar_mes_referencia,
    validar_numero_nao_negativo,
    validar_turno,
)
from .professores_common import (
    validar_payload_atualizacao_professor,
    validar_payload_cadastro_coordenador,
    validar_payload_cadastro_professor,
)

router = APIRouter()


def _formatar_data_hora_local(valor: str | None) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    try:
        data_utc = datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return texto
    return data_utc.astimezone().strftime("%d/%m/%Y %H:%M:%S")


def validar_payload_atribuicao_docente(payload: ProfessorTurmaDisciplinaCreateIn):
    professor_id = validar_numero_nao_negativo(payload.professor_id, "Professor")
    turma_id = validar_numero_nao_negativo(payload.turma_id, "Turma")
    disciplina_id = validar_numero_nao_negativo(payload.disciplina_id, "Disciplina")

    if professor_id <= 0:
        raise HTTPException(400, "Professor obrigatorio.")
    if turma_id <= 0:
        raise HTTPException(400, "Turma obrigatoria.")
    if disciplina_id <= 0:
        raise HTTPException(400, "Disciplina obrigatoria.")

    professor = buscar_usuario_por_id(professor_id)
    if not professor or normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor nao encontrado.")

    turma = next((item for item in listar_turmas_ativas() if int(item["id"]) == turma_id), None)
    if not turma:
        raise HTTPException(404, "Turma nao encontrada ou inativa.")

    disciplina = next(
        (item for item in listar_disciplinas_ativas() if int(item["id"]) == disciplina_id),
        None,
    )
    if not disciplina:
        raise HTTPException(404, "Disciplina nao encontrada ou inativa.")

    return {
        "professor_id": professor_id,
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
    }


def validar_payload_atribuicao_docente_lote(payload: ProfessorDisciplinaTurmasSyncIn):
    professor_id = validar_numero_nao_negativo(payload.professor_id, "Professor")
    disciplina_id = validar_numero_nao_negativo(payload.disciplina_id, "Disciplina")

    if professor_id <= 0:
        raise HTTPException(400, "Professor obrigatorio.")
    if disciplina_id <= 0:
        raise HTTPException(400, "Disciplina obrigatoria.")

    professor = buscar_usuario_por_id(professor_id)
    if not professor or normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor nao encontrado.")

    disciplina = next(
        (item for item in listar_disciplinas_ativas() if int(item["id"]) == disciplina_id),
        None,
    )
    if not disciplina:
        raise HTTPException(404, "Disciplina nao encontrada ou inativa.")

    turmas_ativas = {int(item["id"]): item for item in listar_turmas_ativas()}
    turma_ids = []
    for turma_id in payload.turma_ids or []:
        valor = validar_numero_nao_negativo(turma_id, "Turma")
        if valor <= 0:
            continue
        if valor not in turmas_ativas:
            raise HTTPException(404, "Uma ou mais turmas nao foram encontradas ou estao inativas.")
        if valor not in turma_ids:
            turma_ids.append(valor)

    return {
        "professor_id": professor_id,
        "disciplina_id": disciplina_id,
        "turma_ids": turma_ids,
    }


def _validar_professor_opcional_turma_disciplina(professor_id) -> int | None:
    if professor_id in (None, ""):
        return None

    valor = validar_numero_nao_negativo(professor_id, "Professor")
    if valor <= 0:
        return None

    professor = buscar_usuario_por_id(valor)
    if not professor or normalizar_cargo_usuario(professor) != CARGO_PROFESSOR:
        raise HTTPException(404, "Professor nao encontrado.")
    if not bool(int(professor.get("ativo", 1) or 0)):
        raise HTTPException(400, "Professor selecionado esta inativo.")
    return valor


def _buscar_turma_admin_por_id(turma_id: int):
    return next(
        (item for item in listar_turmas(incluir_inativas=True) if int(item["id"]) == int(turma_id)),
        None,
    )


def _buscar_disciplina_admin_por_id(disciplina_id: int):
    return next(
        (
            item
            for item in listar_disciplinas(incluir_inativas=True)
            if int(item["id"]) == int(disciplina_id)
        ),
        None,
    )


def _buscar_disciplina_admin_por_nome(nome: str):
    nome_limpo = str(nome or "").strip().casefold()
    if not nome_limpo:
        return None
    return next(
        (
            item
            for item in listar_disciplinas(incluir_inativas=True)
            if str(item.get("nome") or "").strip().casefold() == nome_limpo
        ),
        None,
    )


def validar_payload_turma_disciplina_create(payload: TurmaDisciplinaCreateIn):
    turma_id = validar_numero_nao_negativo(payload.turma_id, "Turma")
    if turma_id <= 0:
        raise HTTPException(400, "Turma obrigatoria.")

    turma = _buscar_turma_admin_por_id(turma_id)
    if not turma:
        raise HTTPException(404, "Turma nao encontrada.")

    carga_horaria = validar_numero_nao_negativo(payload.carga_horaria, "Carga horaria")
    professor_id = _validar_professor_opcional_turma_disciplina(payload.professor_id)

    disciplina = None
    disciplina_id = None
    if payload.disciplina_id not in (None, ""):
        disciplina_id = validar_numero_nao_negativo(payload.disciplina_id, "Disciplina")
        if disciplina_id <= 0:
            raise HTTPException(400, "Disciplina obrigatoria.")
        disciplina = _buscar_disciplina_admin_por_id(disciplina_id)
        if not disciplina:
            raise HTTPException(404, "Disciplina nao encontrada.")
    else:
        nome = str(payload.disciplina_nome or "").strip()
        if not nome:
            raise HTTPException(
                400, "Selecione uma disciplina existente ou informe o nome de uma nova."
            )
        disciplina = _buscar_disciplina_admin_por_nome(nome)
        if not disciplina:
            try:
                disciplina_id = int(criar_disciplina(nome=nome, aulas_semanais=carga_horaria))
            except sqlite3.IntegrityError as exc:
                disciplina = _buscar_disciplina_admin_por_nome(nome)
                if not disciplina:
                    raise HTTPException(409, "Ja existe uma disciplina com este nome.") from exc
        if disciplina and disciplina_id is None:
            disciplina_id = int(disciplina["id"])

    return {
        "turma_id": turma_id,
        "disciplina_id": int(disciplina_id or disciplina["id"]),
        "carga_horaria": carga_horaria,
        "professor_id": professor_id,
    }


def validar_payload_turma_disciplina_update(payload: TurmaDisciplinaUpdateIn):
    return {
        "carga_horaria": validar_numero_nao_negativo(payload.carga_horaria, "Carga horaria"),
        "professor_id": _validar_professor_opcional_turma_disciplina(payload.professor_id),
    }


def _serializar_contexto_professores(professores: list[dict]) -> list[dict]:
    return [
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
        for item in professores
    ]


@router.get("/admin/fila")
def fila_admin(usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    return listar_jobs_ativos()


@router.get("/admin/impressao/status")
def obter_status_impressao_admin(usuario=Depends(get_usuario_logado)):
    exigir_gestor(usuario)
    return obter_status_impressao()


@router.put("/admin/impressao/status")
def atualizar_status_impressao_admin(
    payload: ImpressaoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    return atualizar_status_impressao(
        sem_papel=bool(payload.sem_papel),
        mensagem=payload.mensagem,
    )


@router.get("/admin/historico")
def historico_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario_id: int = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    historico = listar_historico(data_inicio, data_fim, usuario_id)
    for item in historico:
        item["criado_em"] = _formatar_data_hora_local(item.get("criado_em"))
        item["finalizado_em"] = _formatar_data_hora_local(item.get("finalizado_em"))
    return historico


@router.get("/admin/relatorio")
def relatorio_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None
    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)


@router.get("/admin/relatorio/impressao")
def relatorio_impressao_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None
    return gerar_relatorio_impressao(data_inicio_norm, data_fim_norm)


@router.get("/admin/relatorio/recursos")
def relatorio_recursos_admin(
    data_inicio: str = None,
    data_fim: str = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None
    return {
        "por_recurso": gerar_relatorio_uso_recursos(data_inicio_norm, data_fim_norm),
        "por_professor": gerar_relatorio_uso_recursos_por_professor(
            data_inicio_norm, data_fim_norm
        ),
    }


@router.get("/admin/turmas")
def listar_turmas_admin_api(
    incluir_inativas: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    return listar_turmas(incluir_inativas=incluir_inativas)


@router.post("/admin/turmas")
def criar_turma_admin(
    payload: TurmaCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    turno = validar_turno(payload.turno)
    quantidade_estudantes = validar_numero_nao_negativo(
        payload.quantidade_estudantes,
        "Quantidade de estudantes",
    )

    if not nome:
        raise HTTPException(400, "Nome da turma é obrigatório.")

    try:
        turma_id = criar_turma(
            nome=nome,
            turno=turno,
            quantidade_estudantes=quantidade_estudantes,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe uma turma com este nome.") from exc

    return {"mensagem": "Turma cadastrada com sucesso.", "turma_id": turma_id}


@router.put("/admin/turmas/{turma_id}")
def atualizar_turma_admin(
    turma_id: int,
    payload: TurmaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    turno = validar_turno(payload.turno)
    quantidade_estudantes = validar_numero_nao_negativo(
        payload.quantidade_estudantes,
        "Quantidade de estudantes",
    )

    alterado = atualizar_turma_dados(
        turma_id=turma_id,
        turno=turno,
        quantidade_estudantes=quantidade_estudantes,
    )
    if not alterado:
        raise HTTPException(404, "Turma não encontrada.")
    return {"mensagem": "Dados da turma atualizados com sucesso."}


@router.put("/admin/turmas/{turma_id}/status")
def atualizar_status_turma_admin(
    turma_id: int,
    payload: RecursoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    alterado = atualizar_status_turma(turma_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Turma não encontrada.")
    return {"mensagem": "Status da turma atualizado com sucesso."}


@router.get("/admin/disciplinas")
def listar_disciplinas_admin_api(
    incluir_inativas: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    return listar_disciplinas(incluir_inativas=incluir_inativas)


@router.post("/admin/disciplinas")
def criar_disciplina_admin(
    payload: DisciplinaCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    tem_apc = bool(payload.tem_apc)
    tem_prova_bimestral = bool(payload.tem_prova_bimestral)

    if not nome:
        raise HTTPException(400, "Nome da disciplina é obrigatório.")

    try:
        disciplina_id = criar_disciplina(
            nome=nome,
            aulas_semanais=aulas_semanais,
            tem_apc=tem_apc,
            tem_prova_bimestral=tem_prova_bimestral,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe uma disciplina com este nome.") from exc

    return {"mensagem": "Disciplina cadastrada com sucesso.", "disciplina_id": disciplina_id}


@router.put("/admin/disciplinas/{disciplina_id}")
def atualizar_disciplina_admin(
    disciplina_id: int,
    payload: DisciplinaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    alterado = atualizar_disciplina_dados(
        disciplina_id=disciplina_id,
        aulas_semanais=aulas_semanais,
        tem_apc=bool(payload.tem_apc),
        tem_prova_bimestral=bool(payload.tem_prova_bimestral),
    )
    if not alterado:
        raise HTTPException(404, "Disciplina não encontrada.")
    return {"mensagem": "Dados da disciplina atualizados com sucesso."}


@router.put("/admin/disciplinas/{disciplina_id}/status")
def atualizar_status_disciplina_admin(
    disciplina_id: int,
    payload: RecursoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    alterado = atualizar_status_disciplina(disciplina_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Disciplina não encontrada.")
    return {"mensagem": "Status da disciplina atualizado com sucesso."}


@router.get("/admin/turmas-disciplinas/contexto")
def listar_contexto_turmas_disciplinas_admin(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    professores = listar_professores_agendamento()
    return {
        "professores": _serializar_contexto_professores(professores),
        "turmas": listar_turmas(incluir_inativas=True),
        "disciplinas": listar_disciplinas(incluir_inativas=True),
    }


@router.get("/admin/turmas-disciplinas", response_model=list[TurmaDisciplinaOut])
def listar_turmas_disciplinas_admin_api(
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    professor_id: int | None = None,
    incluir_inativos: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    return listar_turmas_disciplinas_admin(
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        professor_id=professor_id,
        incluir_inativos=incluir_inativos,
    )


@router.post("/admin/turmas-disciplinas", response_model=TurmaDisciplinaOut)
def criar_turma_disciplina_admin_api(
    payload: TurmaDisciplinaCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_turma_disciplina_create(payload)
    return criar_ou_atualizar_turma_disciplina(
        turma_id=dados["turma_id"],
        disciplina_id=dados["disciplina_id"],
        carga_horaria=dados["carga_horaria"],
        professor_usuario_id=dados["professor_id"],
    )


@router.put("/admin/turmas-disciplinas/{turma_disciplina_id}", response_model=TurmaDisciplinaOut)
def atualizar_turma_disciplina_admin_api(
    turma_disciplina_id: int,
    payload: TurmaDisciplinaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_turma_disciplina_update(payload)
    item = atualizar_turma_disciplina(
        turma_disciplina_id,
        carga_horaria=dados["carga_horaria"],
        professor_usuario_id=dados["professor_id"],
    )
    if not item:
        raise HTTPException(404, "Vinculo de turma e disciplina nao encontrado.")
    return item


@router.delete("/admin/turmas-disciplinas/{turma_disciplina_id}")
def excluir_turma_disciplina_admin_api(
    turma_disciplina_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    alterado = excluir_turma_disciplina(turma_disciplina_id)
    if not alterado:
        raise HTTPException(404, "Vinculo de turma e disciplina nao encontrado.")
    return {"mensagem": "Disciplina removida da turma com sucesso."}


@router.get("/admin/professores/opcoes")
def opcoes_professores_admin(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return obter_opcoes_cadastro_professor()


@router.get("/admin/atribuicoes-docentes/contexto")
def listar_contexto_atribuicoes_docentes_admin(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    professores = listar_professores_agendamento()
    return {
        "professores": _serializar_contexto_professores(professores),
        "turmas": listar_turmas_ativas(),
        "disciplinas": listar_disciplinas_ativas(),
    }


@router.get("/admin/atribuicoes-docentes", response_model=list[ProfessorTurmaDisciplinaOut])
def listar_atribuicoes_docentes_admin_api(
    professor_id: int | None = None,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    return listar_atribuicoes_docentes(
        professor_id=professor_id,
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        incluir_inativos=True,
    )


@router.post("/admin/atribuicoes-docentes", response_model=ProfessorTurmaDisciplinaOut)
def criar_atribuicao_docente_admin_api(
    payload: ProfessorTurmaDisciplinaCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_atribuicao_docente(payload)
    try:
        return criar_atribuicao_docente(
            professor_id=dados["professor_id"],
            turma_id=dados["turma_id"],
            disciplina_id=dados["disciplina_id"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Esta atribuicao docente ja esta cadastrada.") from exc


@router.put("/admin/atribuicoes-docentes/lote")
def sincronizar_atribuicoes_docentes_admin_api(
    payload: ProfessorDisciplinaTurmasSyncIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_atribuicao_docente_lote(payload)
    resultado = sincronizar_atribuicoes_docentes_professor_disciplina(
        professor_id=dados["professor_id"],
        disciplina_id=dados["disciplina_id"],
        turma_ids=dados["turma_ids"],
    )
    return {
        **resultado,
        "mensagem": (
            "Atribuicoes atualizadas com sucesso. "
            f"{resultado['criados']} criada(s), {resultado['removidos']} removida(s) e "
            f"{resultado['total_ativo']} turma(s) ativa(s) para esta disciplina."
        ),
    }


@router.post("/admin/atribuicoes-docentes/importar")
def importar_atribuicoes_docentes_admin_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo JSON nao enviado.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo JSON vazio.")

    try:
        return importar_atribuicoes_docentes_arquivo(
            conteudo,
            nome_arquivo=arquivo.filename,
            tipo_conteudo=getattr(arquivo, "content_type", None),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/admin/atribuicoes-docentes/{atribuicao_id}")
def excluir_atribuicao_docente_admin_api(
    atribuicao_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    alterado = excluir_atribuicao_docente(atribuicao_id)
    if not alterado:
        raise HTTPException(404, "Atribuicao docente nao encontrada.")
    return {"mensagem": "Atribuicao docente removida com sucesso."}


@router.get("/admin/professores")
def listar_professores_painel(
    mes: str = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    mes_referencia = validar_mes_referencia(mes) if mes else mes_atual_referencia()
    regras = obter_regras_cota()
    professores = listar_professores_admin(mes_referencia)
    calculos = calcular_cotas_mensais_professores()
    calculos_por_usuario = {int(calculo["usuario_id"]): calculo for calculo in calculos}

    for professor in professores:
        calculo_professor = calculos_por_usuario.get(int(professor["id"]), {})
        professor["peso_total_individual"] = calculo_professor.get("peso_total_individual", 0)
        professor["cota_projetada"] = int(calculo_professor.get("cota_mensal_calculada", 0))

    return {
        "mes_referencia": mes_referencia,
        "regras_cota": regras,
        "professores": professores,
    }


@router.get("/admin/coordenadores")
def listar_coordenadores_painel(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return listar_coordenadores_admin()


@router.post("/admin/coordenadores")
def criar_coordenador_painel(
    payload: CoordenadorCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_cadastro_coordenador(payload)

    try:
        coordenador_id = criar_coordenador(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=hash_senha(dados["senha"]),
            nt_hash=generate_nt_hash(dados["senha"]),
            data_nascimento=dados["data_nascimento"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Coordenador cadastrado com sucesso.", "coordenador_id": coordenador_id}


@router.post("/admin/professores")
def criar_professor_painel(
    payload: ProfessorCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    dados = validar_payload_cadastro_professor(payload)

    try:
        professor_id = criar_professor(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=hash_senha(dados["senha"]),
            nt_hash=generate_nt_hash(dados["senha"]),
            data_nascimento=dados["data_nascimento"],
            aulas_semanais=dados["aulas_semanais"],
            turmas_quantidade=dados["turmas_quantidade"],
            turmas=dados["turmas"],
            disciplinas=dados["disciplinas"],
            acesso_coordenacao=dados["acesso_coordenacao"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    return {"mensagem": "Professor cadastrado com sucesso.", "professor_id": professor_id}


@router.put("/admin/professores/{professor_id}")
def atualizar_professor_painel(
    professor_id: int,
    payload: ProfessorUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor não encontrado.")

    dados = validar_payload_atualizacao_professor(payload)

    try:
        alterado = atualizar_professor(
            usuario_id=professor_id,
            nome=dados["nome"],
            email=dados["email"],
            data_nascimento=dados["data_nascimento"],
            aulas_semanais=dados["aulas_semanais"],
            turmas_quantidade=dados["turmas_quantidade"],
            turmas=dados["turmas"],
            disciplinas=dados["disciplinas"],
            acesso_coordenacao=dados["acesso_coordenacao"],
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um usuário com este email.") from exc

    if not alterado:
        raise HTTPException(404, "Professor não encontrado.")

    return {"mensagem": "Professor atualizado com sucesso."}


@router.put("/admin/professores/{professor_id}/senha")
def redefinir_senha_professor_painel(
    professor_id: int,
    payload: ProfessorRedefinirSenhaAdminIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor nao encontrado.")

    nova_senha = str(payload.nova_senha or "").strip()
    if not nova_senha:
        raise HTTPException(400, "Nova senha e obrigatoria.")

    validar_senha_forte(nova_senha)
    alterado = atualizar_senha_usuario(professor_id, nova_senha)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    revogar_tokens_usuario(professor_id)
    return {"mensagem": "Senha redefinida com sucesso."}


@router.delete("/admin/professores/{professor_id}")
def excluir_professor_painel(
    professor_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id, incluir_inativos=True)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor nao encontrado.")
    if not int(professor.get("ativo", 1)):
        raise HTTPException(400, "Professor ja foi excluido.")

    alterado = desativar_professor(professor_id)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    return {"mensagem": "Professor excluido com sucesso."}


@router.put("/admin/professores/{professor_id}/promover-coordenador")
def promover_professor_para_coordenador_painel(
    professor_id: int,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor nao encontrado.")

    alterado = promover_professor_para_coordenador(professor_id)
    if not alterado:
        raise HTTPException(404, "Professor nao encontrado.")

    return {"mensagem": "Professor promovido para coordenador com sucesso."}


@router.put("/admin/professores/{professor_id}/carga")
def atualizar_carga_professor_painel(
    professor_id: int,
    payload: ProfessorCargaIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    professor = buscar_usuario_por_id(professor_id)
    if not professor or professor["perfil"] != "professor":
        raise HTTPException(404, "Professor não encontrado.")

    aulas_semanais = validar_numero_nao_negativo(payload.aulas_semanais, "Aulas semanais")
    turmas_quantidade = validar_numero_nao_negativo(
        payload.turmas_quantidade,
        "Quantidade de turmas",
    )

    salvar_carga_professor(
        usuario_id=professor_id,
        aulas_semanais=aulas_semanais,
        turmas_quantidade=turmas_quantidade,
    )
    return {"mensagem": "Carga do professor atualizada com sucesso."}


@router.get("/admin/cotas/regras")
def obter_regras_cota_admin(usuario=Depends(get_usuario_logado)):
    exigir_admin(usuario)
    return obter_regras_cota()


@router.put("/admin/cotas/regras")
def atualizar_regras_cota_admin(
    payload: RegrasCotaIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    base_paginas = validar_numero_nao_negativo(payload.base_paginas, "Base de páginas")
    paginas_por_aula = validar_numero_nao_negativo(payload.paginas_por_aula, "Páginas por aula")
    paginas_por_turma = validar_numero_nao_negativo(payload.paginas_por_turma, "Páginas por turma")
    cota_mensal_escola = validar_numero_nao_negativo(
        payload.cota_mensal_escola,
        "Cota mensal da escola",
    )

    atualizar_regras_cota(base_paginas, paginas_por_aula, paginas_por_turma, cota_mensal_escola)
    return {"mensagem": "Regras de cota atualizadas com sucesso."}


@router.post("/admin/cotas/recalcular")
def recalcular_cotas_admin(
    mes: str = None,
    usuario=Depends(get_usuario_logado),
):
    exigir_admin(usuario)
    mes_referencia = validar_mes_referencia(mes) if mes else mes_atual_referencia()
    recalcular_cotas_mes(mes_referencia)
    return {"mensagem": "Cotas recalculadas com sucesso.", "mes_referencia": mes_referencia}


@router.get("/admin/recursos")
def listar_recursos_admin_api(
    incluir_inativos: bool = True,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    return listar_recursos(incluir_inativos=incluir_inativos)


@router.post("/admin/recursos")
def criar_recurso_admin(
    payload: RecursoCreateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    tipo = payload.tipo.strip()
    descricao = (payload.descricao or "").strip()
    quantidade_itens = validar_numero_nao_negativo(payload.quantidade_itens, "Quantidade de itens")

    if not nome:
        raise HTTPException(400, "Nome do recurso é obrigatório.")
    if not tipo:
        raise HTTPException(400, "Tipo do recurso é obrigatório.")
    if quantidade_itens < 1:
        raise HTTPException(400, "Quantidade de itens deve ser no mínimo 1.")

    try:
        recurso_id = criar_recurso(
            nome=nome,
            tipo=tipo,
            descricao=descricao,
            quantidade_itens=quantidade_itens,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um recurso com este nome.") from exc

    return {"mensagem": "Recurso criado com sucesso.", "recurso_id": recurso_id}


@router.put("/admin/recursos/{recurso_id}")
def atualizar_recurso_admin(
    recurso_id: int,
    payload: RecursoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    nome = payload.nome.strip()
    tipo = payload.tipo.strip()
    descricao = (payload.descricao or "").strip()
    quantidade_itens = validar_numero_nao_negativo(payload.quantidade_itens, "Quantidade de itens")
    if not nome:
        raise HTTPException(400, "Nome do recurso é obrigatório.")
    if not tipo:
        raise HTTPException(400, "Tipo do recurso é obrigatório.")
    if quantidade_itens < 1:
        raise HTTPException(400, "Quantidade de itens deve ser no mínimo 1.")

    try:
        alterado = atualizar_recurso_dados(
            recurso_id=recurso_id,
            nome=nome,
            tipo=tipo,
            descricao=descricao,
            quantidade_itens=quantidade_itens,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Já existe um recurso com este nome.") from exc

    if not alterado:
        raise HTTPException(404, "Recurso não encontrado.")
    return {"mensagem": "Recurso atualizado com sucesso."}


@router.put("/admin/recursos/{recurso_id}/status")
def atualizar_status_recurso_admin(
    recurso_id: int,
    payload: RecursoStatusIn,
    usuario=Depends(get_usuario_logado),
):
    exigir_gestor(usuario)
    alterado = atualizar_status_recurso(recurso_id, payload.ativo)
    if not alterado:
        raise HTTPException(404, "Recurso não encontrado.")
    return {"mensagem": "Status do recurso atualizado com sucesso."}
