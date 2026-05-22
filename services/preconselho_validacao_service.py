from datetime import datetime

from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_turma_por_id,
    listar_disciplinas_ativas,
    listar_turmas_ativas,
)
from db.docencia import listar_atribuicoes_docentes_por_usuario_ids
from db.ocorrencias import buscar_estudante_por_id
from db.usuarios import (
    buscar_usuario_por_id,
    listar_cargas_professores_por_usuario_ids,
)
from repositories.preconselho_repository import (
    buscar_motivos_pre_conselho_por_ids,
    buscar_periodo_pre_conselho_por_id,
)
from services.preconselho_service import periodo_editavel_para_cargo


def normalizar_cargo_preconselho(usuario: dict) -> str:
    cargo = str((usuario or {}).get("cargo") or "").strip().upper()
    if cargo in {"ADMIN", "COORDENADOR", "PROFESSOR"}:
        return cargo

    perfil = str((usuario or {}).get("perfil") or "").strip().lower()
    if perfil == "admin":
        return "ADMIN"
    if perfil == "coordenador":
        return "COORDENADOR"
    return "PROFESSOR"


def obter_usuario_id_preconselho(usuario: dict) -> int:
    try:
        valor = int((usuario or {}).get("id"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Usuario invalido.") from exc
    if valor <= 0:
        raise ValueError("Usuario invalido.")
    return valor


def usuario_eh_admin_preconselho(usuario: dict) -> bool:
    return normalizar_cargo_preconselho(usuario) == "ADMIN"


def usuario_eh_gestor_preconselho(usuario: dict) -> bool:
    cargo = normalizar_cargo_preconselho(usuario)
    if cargo in {"ADMIN", "COORDENADOR"}:
        return True
    try:
        return cargo == "PROFESSOR" and int((usuario or {}).get("acesso_coordenacao") or 0) == 1
    except (TypeError, ValueError):
        return False


def usuario_eh_professor_preconselho(usuario: dict) -> bool:
    return normalizar_cargo_preconselho(usuario) == "PROFESSOR"


def validar_texto_obrigatorio_preconselho(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def validar_texto_opcional_preconselho(
    valor: str | None,
    campo: str,
    *,
    max_len: int = 1000,
) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def validar_data_iso_preconselho(valor: str, campo: str) -> str:
    texto = validar_texto_obrigatorio_preconselho(valor, campo, max_len=20)
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def validar_periodo_preconselho(periodo_id: int) -> dict:
    try:
        periodo_id_valor = int(periodo_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Periodo invalido.") from exc
    periodo = buscar_periodo_pre_conselho_por_id(periodo_id_valor)
    if not periodo:
        raise LookupError("Periodo nao encontrado.")
    return periodo


def validar_turma_preconselho(turma_id: int) -> dict:
    try:
        turma_id_valor = int(turma_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Turma invalida.") from exc
    turma = buscar_turma_por_id(turma_id_valor)
    if not turma:
        raise LookupError("Turma nao encontrada.")
    return turma


def validar_disciplina_preconselho(disciplina_id: int) -> dict:
    try:
        disciplina_id_valor = int(disciplina_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Disciplina invalida.") from exc
    disciplina = buscar_disciplina_por_id(disciplina_id_valor)
    if not disciplina:
        raise LookupError("Disciplina nao encontrada.")
    return disciplina


def validar_estudante_na_turma_preconselho(estudante_id: int, turma_id: int) -> dict:
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Estudante invalido.") from exc
    estudante = buscar_estudante_por_id(estudante_id_valor)
    if not estudante:
        raise LookupError("Estudante nao encontrado.")
    if int(estudante.get("turma_id") or 0) != int(turma_id):
        raise ValueError("O estudante nao pertence a turma selecionada.")
    return estudante


def resolver_professor_preconselho(
    usuario: dict,
    professor_id: int | None = None,
    *,
    permitir_gestor: bool = False,
) -> dict:
    cargo = normalizar_cargo_preconselho(usuario)
    usuario_id = obter_usuario_id_preconselho(usuario)

    if cargo == "PROFESSOR":
        if professor_id in (None, usuario_id):
            return {"id": usuario_id, "nome": str(usuario.get("nome") or "").strip()}
        if not (permitir_gestor and usuario_eh_gestor_preconselho(usuario)):
            raise PermissionError("Acesso negado.")

    if not permitir_gestor or not usuario_eh_gestor_preconselho(usuario):
        raise PermissionError("Acesso negado.")
    if professor_id is None:
        raise ValueError("Professor obrigatorio.")

    professor = buscar_usuario_por_id(int(professor_id))
    if not professor or normalizar_cargo_preconselho(professor) != "PROFESSOR":
        raise LookupError("Professor nao encontrado.")
    return {"id": int(professor["id"]), "nome": professor["nome"]}


def _escopo_professor_legado_preconselho(usuario_id: int) -> dict:
    carga = listar_cargas_professores_por_usuario_ids([usuario_id]).get(usuario_id, {})
    nomes_turmas = {
        str(item).strip().casefold() for item in carga.get("turmas") or [] if str(item).strip()
    }
    nomes_disciplinas = {
        str(item).strip().casefold()
        for item in carga.get("disciplinas") or []
        if str(item).strip()
    }
    turmas = [
        dict(item)
        for item in listar_turmas_ativas()
        if str(item.get("nome") or "").strip().casefold() in nomes_turmas
    ]
    disciplinas = [
        dict(item)
        for item in listar_disciplinas_ativas()
        if str(item.get("nome") or "").strip().casefold() in nomes_disciplinas
    ]
    combinacoes = []
    for turma in turmas:
        for disciplina in disciplinas:
            combinacoes.append(
                {
                    "turma_id": int(turma["id"]),
                    "turma_nome": turma.get("nome", "") or "",
                    "turno": turma.get("turno", "") or "",
                    "disciplina_id": int(disciplina["id"]),
                    "disciplina_nome": disciplina.get("nome", "") or "",
                }
            )
    return {
        "usa_atribuicoes_exatas": False,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def escopo_professor_preconselho(usuario_id: int) -> dict:
    atribuicoes = listar_atribuicoes_docentes_por_usuario_ids(
        [usuario_id],
        incluir_inativos=False,
    ).get(usuario_id, [])
    if not atribuicoes:
        return _escopo_professor_legado_preconselho(usuario_id)

    turmas_por_id = {}
    disciplinas_por_id = {}
    combinacoes = []
    for atribuicao in atribuicoes:
        turma_id = int(atribuicao["turma_id"])
        disciplina_id = int(atribuicao["disciplina_id"])
        if turma_id not in turmas_por_id:
            turmas_por_id[turma_id] = {
                "id": turma_id,
                "nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
            }
        if disciplina_id not in disciplinas_por_id:
            disciplinas_por_id[disciplina_id] = {
                "id": disciplina_id,
                "nome": atribuicao.get("disciplina_nome", "") or "",
            }
        combinacoes.append(
            {
                "turma_id": turma_id,
                "turma_nome": atribuicao.get("turma_nome", "") or "",
                "turno": atribuicao.get("turno", "") or "",
                "disciplina_id": disciplina_id,
                "disciplina_nome": atribuicao.get("disciplina_nome", "") or "",
            }
        )

    turmas = sorted(
        turmas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    disciplinas = sorted(
        disciplinas_por_id.values(),
        key=lambda item: (str(item.get("nome") or "").casefold(), int(item.get("id") or 0)),
    )
    combinacoes.sort(
        key=lambda item: (
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        )
    )
    return {
        "usa_atribuicoes_exatas": True,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "combinacoes": combinacoes,
    }


def opcoes_professor_preconselho(usuario_id: int) -> tuple[list[dict], list[dict]]:
    escopo = escopo_professor_preconselho(usuario_id)
    return escopo["turmas"], escopo["disciplinas"]


def validar_escopo_professor_preconselho(
    professor_id: int,
    turma_id: int,
    disciplina_id: int,
):
    escopo = escopo_professor_preconselho(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}
    turma_id_valor = int(turma_id)
    disciplina_id_valor = int(disciplina_id)

    if turma_id_valor not in turma_ids:
        raise PermissionError("Turma fora da carga do professor.")
    if disciplina_id_valor not in disciplina_ids:
        raise PermissionError("Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"]:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (turma_id_valor, disciplina_id_valor) not in combinacoes:
            raise PermissionError("Disciplina fora da atribuicao docente da turma selecionada.")
    return escopo["turmas"], escopo["disciplinas"]


def validar_filtros_professor_preconselho(
    professor_id: int,
    *,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
):
    escopo = escopo_professor_preconselho(professor_id)
    turma_ids = {int(item["id"]) for item in escopo["turmas"]}
    disciplina_ids = {int(item["id"]) for item in escopo["disciplinas"]}

    if turma_id is not None and int(turma_id) not in turma_ids:
        raise PermissionError("Turma fora da carga do professor.")
    if disciplina_id is not None and int(disciplina_id) not in disciplina_ids:
        raise PermissionError("Disciplina fora da carga do professor.")
    if escopo["usa_atribuicoes_exatas"] and turma_id is not None and disciplina_id is not None:
        combinacoes = {
            (int(item["turma_id"]), int(item["disciplina_id"])) for item in escopo["combinacoes"]
        }
        if (int(turma_id), int(disciplina_id)) not in combinacoes:
            raise PermissionError("Disciplina fora da atribuicao docente da turma selecionada.")


def motivos_ativos_validos_preconselho(motivo_ids: list[int]) -> list[dict]:
    motivos = buscar_motivos_pre_conselho_por_ids(motivo_ids)
    ids_recebidos = {int(valor) for valor in motivo_ids or [] if int(valor) > 0}
    ids_encontrados = {int(item["id"]) for item in motivos if int(item.get("ativo") or 0) == 1}
    if ids_recebidos != ids_encontrados:
        raise ValueError("Existe motivo invalido ou inativo na selecao.")
    return motivos


def registro_editavel_usuario_preconselho(usuario: dict, registro: dict) -> bool:
    if usuario_eh_admin_preconselho(usuario):
        return True
    if usuario_eh_professor_preconselho(usuario):
        return int(registro.get("professor_id") or 0) == obter_usuario_id_preconselho(
            usuario
        ) and periodo_editavel_para_cargo(registro.get("periodo_status"), "PROFESSOR")
    return False


def enriquecer_editavel_preconselho(usuario: dict, itens: list[dict]) -> list[dict]:
    return [
        {**item, "editavel": registro_editavel_usuario_preconselho(usuario, item)}
        for item in itens
    ]
