import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from auth import get_usuario_logado
from database import (
    ACAO_OCORRENCIA_VALIDAS,
    STATUS_OCORRENCIA_REGISTRADO,
    STATUS_OCORRENCIA_VALIDOS,
    atualizar_alinea,
    atualizar_artigo,
    atualizar_inciso,
    atualizar_lei,
    atualizar_ocorrencia,
    atualizar_estudante,
    atualizar_regimento_item,
    atualizar_status_regimento_item,
    atualizar_status_estudante,
    buscar_alinea_por_id,
    buscar_artigo_por_id,
    buscar_estudante_por_id,
    buscar_inciso_por_id,
    buscar_lei_por_id,
    buscar_estudantes_ocorrencia,
    buscar_ocorrencia_por_id,
    buscar_professor_por_id_ocorrencia,
    buscar_professores_ocorrencia,
    buscar_regimento_item_por_id,
    buscar_regimento_itens_por_ids,
    buscar_turma_por_id,
    criar_alinea,
    criar_artigo,
    criar_estudante,
    criar_inciso,
    criar_lei,
    criar_ocorrencia,
    criar_regimento_item,
    listar_alineas,
    listar_artigos,
    listar_disciplinas_ativas,
    listar_estudantes,
    listar_incisos,
    listar_leis,
    listar_ocorrencias,
    listar_professores_agendamento,
    listar_regimento_itens,
    listar_turmas_ativas,
    remover_alinea,
    remover_artigo,
    remover_estudante,
    remover_inciso,
    remover_lei,
    remover_ocorrencia,
    remover_regimento_item,
    salvar_regimento_itens_ocorrencia,
)
from models import (
    AlineaCreateIn,
    AlineaOut,
    AlineaUpdateIn,
    ArtigoCreateIn,
    ArtigoOut,
    ArtigoUpdateIn,
    EstudanteCreateIn,
    EstudanteOut,
    EstudanteStatusIn,
    EstudanteUpdateIn,
    ImportacaoCsvOut,
    IncisoCreateIn,
    IncisoOut,
    IncisoUpdateIn,
    LeiCreateIn,
    LeiOut,
    LeiUpdateIn,
    OcorrenciaCreateIn,
    OcorrenciaOut,
    OcorrenciaUpdateIn,
    RegimentoItemCreateIn,
    RegimentoItemOut,
    RegimentoItemStatusIn,
    RegimentoItemUpdateIn,
)
from services.csv_import_service import importar_base_legal_arquivo, importar_estudantes_arquivo
from services.ocorrencia_disciplina_service import (
    acao_compativel_com_gravidade,
    inferir_gravidade_ocorrencia,
    listar_acoes_aplicadas,
    rotulo_gravidade_ocorrencia,
)
from services.ocorrencia_pdf_service import gerar_pdf_ocorrencia_registro

router = APIRouter()

_HORARIO_REGEX = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
_ACOES_ROTULOS = {
    "orientacao_verbal": "Orientação verbal",
    "advertencia": "Advertência verbal",
    ""
    "chamada_responsavel": "Chamada de responsável",
    "encaminhamento_direcao": "Encaminhamento à direção",
    "registro_informativo": "Registro informativo",
}
_STATUS_ROTULOS = {
    "registrado": "Registrado",
    "em_acompanhamento": "Em acompanhamento",
    "aguardando_responsavel": "Aguardando responsável",
    "resolvido": "Resolvido",
}
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


def _model_to_dict(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _normalizar_cargo(usuario: dict) -> str:
    cargo = str(usuario.get("cargo") or "").strip().upper()
    if cargo:
        return cargo

    perfil = str(usuario.get("perfil") or "").strip().lower()
    if perfil == "admin":
        return "ADMIN"
    if perfil == "coordenador":
        return "COORDENADOR"
    return "PROFESSOR"


def _exigir_gestor(usuario: dict):
    if _normalizar_cargo(usuario) not in {"ADMIN", "COORDENADOR"}:
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


def _validar_horario_ocorrencia(valor: str) -> str:
    texto = _texto_obrigatorio(valor, "Horario da ocorrencia", max_len=30)
    if _HORARIO_REGEX.match(texto):
        formato = "%H:%M:%S" if texto.count(":") == 2 else "%H:%M"
        try:
            datetime.strptime(texto, formato)
        except ValueError as exc:
            raise HTTPException(400, "Horario da ocorrencia invalido.") from exc
    return texto


def _validar_status(valor: str) -> str:
    status = str(valor or "").strip()
    if status not in STATUS_OCORRENCIA_VALIDOS:
        raise HTTPException(400, "Status invalido.")
    return status


def _validar_acao_aplicada(valor: str) -> str:
    acao = str(valor or "").strip()
    if acao not in ACAO_OCORRENCIA_VALIDAS:
        raise HTTPException(400, "Acao aplicada invalida.")
    return acao


def _validar_acao_compativel_com_base_legal(acao_aplicada: str, itens_regimento: list[dict]) -> str | None:
    gravidade = inferir_gravidade_ocorrencia(itens_regimento)
    if gravidade and not acao_compativel_com_gravidade(acao_aplicada, gravidade):
        raise HTTPException(
            400,
            (
                "A acao aplicada nao e compativel com a gravidade automatica da ocorrencia "
                f"({rotulo_gravidade_ocorrencia(gravidade)})."
            ),
        )
    return gravidade


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


def _normalizar_turno_turma(valor: str | None) -> str:
    return str(valor or "").strip().upper()


def _faixa_global_por_turno_e_aula(turno: str, aula_turno: int) -> int:
    faixa_global = int(aula_turno) + _FAIXA_GLOBAL_OFFSET_POR_TURNO[turno]
    # No integral, a faixa 6 fica livre para não colidir com a 1ª do vespertino.
    if turno == "INTEGRAL" and int(aula_turno) > 5:
        faixa_global += 1
    return faixa_global


def _faixas_disponiveis_turno(turno: str) -> list[int]:
    turno_normalizado = _normalizar_turno_turma(turno)
    config_turno = _TURNOS_CONFIG.get(turno_normalizado)
    if not config_turno:
        return []

    faixas = []
    total_aulas = int(config_turno["aulas"])
    for aula_turno in range(1, total_aulas + 1):
        faixas.append(_faixa_global_por_turno_e_aula(turno_normalizado, aula_turno))
    return faixas


def _validar_faixa_aula_por_turma(aula: str | None, turma_id: int) -> str:
    texto_aula = _texto_obrigatorio(aula, "Aula", max_len=20)
    if not texto_aula.isdigit():
        raise HTTPException(400, "Aula invalida. Selecione uma faixa valida.")

    faixa_global = int(texto_aula)
    if faixa_global <= 0:
        raise HTTPException(400, "Aula invalida. Selecione uma faixa valida.")

    turma = buscar_turma_por_id(turma_id)
    if not turma:
        raise HTTPException(400, "Turma invalida.")

    turno_turma = _normalizar_turno_turma(turma.get("turno"))
    config_turno = _TURNOS_CONFIG.get(turno_turma)
    if not config_turno:
        raise HTTPException(400, "Turma sem turno configurado. Atualize o cadastro da turma.")

    faixas_disponiveis = set(_faixas_disponiveis_turno(turno_turma))
    if faixa_global not in faixas_disponiveis:
        raise HTTPException(400, "Faixa de aula invalida para o turno da turma selecionada.")

    return str(faixa_global)


def _validar_estudante_id(estudante_id: int | None) -> int | None:
    if estudante_id is None:
        return None
    try:
        estudante_id_valor = int(estudante_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Estudante invalido.") from exc
    if estudante_id_valor <= 0:
        raise HTTPException(400, "Estudante invalido.")
    return estudante_id_valor


def _validar_professor_id(professor_id: int | None) -> int | None:
    if professor_id is None:
        return None
    try:
        professor_id_valor = int(professor_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Professor requerente invalido.") from exc
    if professor_id_valor <= 0:
        raise HTTPException(400, "Professor requerente invalido.")
    return professor_id_valor


def _resolver_dados_estudante(
    *,
    nome_estudante: str | None,
    estudante_id: int | None,
    turma_id: int,
) -> tuple[str, int | None]:
    estudante_id_valor = _validar_estudante_id(estudante_id)
    nome_resolvido = _texto_opcional(nome_estudante, max_len=255)

    if estudante_id_valor is None:
        if not nome_resolvido:
            raise HTTPException(400, "Nome do estudante e obrigatorio.")
        return nome_resolvido, None

    estudante = buscar_estudante_por_id(estudante_id_valor)
    if not estudante:
        raise HTTPException(400, "Estudante selecionado nao encontrado.")
    if int(estudante.get("ativo") or 0) != 1:
        raise HTTPException(400, "Estudante selecionado esta inativo.")

    turma_estudante_id = int(estudante.get("turma_id") or 0)
    if turma_estudante_id != int(turma_id):
        raise HTTPException(400, "Turma da ocorrencia diferente da turma do estudante.")

    return str(estudante.get("nome") or "").strip(), estudante_id_valor


def _resolver_dados_professor(
    *,
    professor_requerente: str | None,
    professor_requerente_id: int | None,
) -> tuple[str, int | None]:
    professor_id_valor = _validar_professor_id(professor_requerente_id)
    professor_nome = _texto_opcional(professor_requerente, max_len=255)

    if professor_id_valor is None:
        if not professor_nome:
            raise HTTPException(400, "Professor requerente e obrigatorio.")
        return professor_nome, None

    professor = buscar_professor_por_id_ocorrencia(professor_id_valor)
    if not professor:
        raise HTTPException(400, "Professor selecionado nao encontrado.")
    return str(professor.get("nome") or "").strip(), professor_id_valor


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


def _normalizar_regimento_item_ids(valores: list[int] | None) -> list[int]:
    ids_norm = []
    vistos = set()
    for valor in valores or []:
        try:
            regimento_item_id = int(valor)
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, "Item do regimento invalido.") from exc
        if regimento_item_id <= 0:
            raise HTTPException(400, "Item do regimento invalido.")
        if regimento_item_id in vistos:
            continue
        vistos.add(regimento_item_id)
        ids_norm.append(regimento_item_id)

    if not ids_norm:
        return []

    itens = buscar_regimento_itens_por_ids(ids_norm)
    if len(itens) != len(ids_norm):
        raise HTTPException(400, "Um ou mais itens do regimento nao foram encontrados.")
    return ids_norm


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
    lei_nome = _texto_obrigatorio(
        dados_brutos.get("lei_nome"),
        "Lei",
        max_len=120,
    ) if str(dados_brutos.get("lei_nome") or "").strip() else "Base legal"

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
    alinea_identificador = _texto_opcional(
        dados_brutos.get("alinea_identificador"),
        max_len=40,
    )
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


def _montar_resposta_estudante(estudante_id: int) -> dict:
    estudante = buscar_estudante_por_id(estudante_id)
    if not estudante:
        raise HTTPException(404, "Estudante nao encontrado.")
    return estudante


def _ler_upload_estudantes(arquivo: UploadFile) -> tuple[bytes, str, str]:
    nome_arquivo = str(getattr(arquivo, "filename", "") or "").strip()
    if not nome_arquivo:
        raise HTTPException(400, "Arquivo de estudantes nao enviado.")

    tipo_conteudo = str(getattr(arquivo, "content_type", "") or "").lower()
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(".csv")
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
    extensao_valida = nome_arquivo.lower().endswith(".json") or nome_arquivo.lower().endswith(".csv")
    tipo_valido = "json" in tipo_conteudo or "csv" in tipo_conteudo or "text/plain" in tipo_conteudo
    if not extensao_valida and not tipo_valido:
        raise HTTPException(400, "Envie um arquivo JSON ou CSV valido.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo da base legal vazio.")
    return conteudo, nome_arquivo, tipo_conteudo


@router.get("/ocorrencias/opcoes")
def listar_opcoes_ocorrencias(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    turmas = listar_turmas_ativas()
    professores = listar_professores_agendamento()

    turmas_formatadas = []
    for turma in turmas:
        turno_turma = _normalizar_turno_turma(turma.get("turno"))
        config_turno = _TURNOS_CONFIG.get(turno_turma)
        turmas_formatadas.append(
            {
                "id": turma["id"],
                "nome": turma["nome"],
                "turno": turno_turma,
                "turno_nome": config_turno["nome"] if config_turno else "Turno nao configurado",
                "aulas": int(config_turno["aulas"]) if config_turno else 0,
                "turno_valido": bool(config_turno),
                "faixas_disponiveis": _faixas_disponiveis_turno(turno_turma),
            }
        )

    return {
        "status_padrao": STATUS_OCORRENCIA_REGISTRADO,
        "acoes_aplicadas": listar_acoes_aplicadas(),
        "status": [
            {"id": status, "nome": _STATUS_ROTULOS.get(status, status)}
            for status in STATUS_OCORRENCIA_VALIDOS
        ],
        "turmas": turmas_formatadas,
        "professores": [
            {
                "id": professor["id"],
                "nome": professor["nome"],
                "email": professor.get("email", ""),
                "label": (
                    f'{professor["nome"]} ({professor.get("email", "")})'
                    if str(professor.get("email", "")).strip()
                    else str(professor["nome"])
                ),
            }
            for professor in professores
        ],
        "disciplinas": [
            {
                "id": disciplina["id"],
                "nome": disciplina["nome"],
                "label": disciplina["nome"],
            }
            for disciplina in listar_disciplinas_ativas()
        ],
        "leis": listar_leis(),
        "artigos": listar_artigos(),
        "incisos": listar_incisos(),
        "alineas": listar_alineas(),
        "regimento_itens": [
            {
                **item,
                "label": item["artigo"],
            }
            for item in listar_regimento_itens(incluir_inativos=True)
        ],
    }


@router.get("/ocorrencias/busca/professores")
def buscar_professores_ocorrencia_api(
    q: str = Query(default=""),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    professores = buscar_professores_ocorrencia(termo=q, limite=limite)
    return [
        {
            "id": professor["id"],
            "nome": professor["nome"],
            "email": professor.get("email", ""),
            "label": (
                f'{professor["nome"]} ({professor.get("email", "")})'
                if str(professor.get("email", "")).strip()
                else str(professor["nome"])
            ),
        }
        for professor in professores
    ]


@router.get("/ocorrencias/busca/estudantes")
def buscar_estudantes_ocorrencia_api(
    q: str = Query(default=""),
    turma_id: int | None = Query(default=None),
    limite: int = Query(default=20),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    estudantes = buscar_estudantes_ocorrencia(
        termo=q,
        turma_id=turma_id_filtro,
        limite=limite,
    )
    return [
        {
            "id": estudante["id"],
            "nome": estudante["nome"],
            "turma_id": estudante["turma_id"],
            "turma_nome": estudante.get("turma_nome", ""),
            "label": f'{estudante["nome"]} ({estudante.get("turma_nome", "Sem turma")})',
        }
        for estudante in estudantes
    ]


@router.post("/ocorrencias", response_model=OcorrenciaOut)
def criar_ocorrencia_api(payload: OcorrenciaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)

    turma_id = _validar_turma_id(payload.turma_id)
    faixa_aula = _validar_faixa_aula_por_turma(payload.aula, turma_id)
    status = _validar_status(payload.status or STATUS_OCORRENCIA_REGISTRADO)
    acao_aplicada = _validar_acao_aplicada(payload.acao_aplicada)
    regimento_item_ids = _normalizar_regimento_item_ids(payload.regimento_item_ids)
    regimento_itens = buscar_regimento_itens_por_ids(regimento_item_ids) if regimento_item_ids else []
    _validar_acao_compativel_com_base_legal(acao_aplicada, regimento_itens)
    descricao = _texto_obrigatorio(payload.descricao, "Descricao", max_len=5000)

    nome_estudante, estudante_id = _resolver_dados_estudante(
        nome_estudante=payload.nome_estudante,
        estudante_id=payload.estudante_id,
        turma_id=turma_id,
    )
    professor_requerente, professor_requerente_id = _resolver_dados_professor(
        professor_requerente=payload.professor_requerente,
        professor_requerente_id=payload.professor_requerente_id,
    )

    try:
        ocorrencia_id = criar_ocorrencia(
            nome_estudante=nome_estudante,
            estudante_id=estudante_id,
            turma_id=turma_id,
            professor_requerente=professor_requerente,
            professor_requerente_id=professor_requerente_id,
            disciplina=_texto_obrigatorio(payload.disciplina, "Disciplina"),
            data_ocorrencia=_validar_data_iso(payload.data_ocorrencia, "Data da ocorrencia"),
            aula=faixa_aula,
            horario_ocorrencia=_validar_horario_ocorrencia(payload.horario_ocorrencia),
            descricao=descricao,
            acao_aplicada=acao_aplicada,
            status=status,
            regimento_item_ids=regimento_item_ids,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.get("/ocorrencias", response_model=list[OcorrenciaOut])
def listar_ocorrencias_api(
    status: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    nome_estudante: str | None = Query(default=None),
    data_inicial: str | None = Query(default=None),
    data_final: str | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)

    status_filtro = None
    if status is not None and str(status).strip():
        status_filtro = _validar_status(status)

    data_inicial_norm = _validar_data_opcional(data_inicial, "Data inicial")
    data_final_norm = _validar_data_opcional(data_final, "Data final")
    if data_inicial_norm and data_final_norm and data_inicial_norm > data_final_norm:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    return listar_ocorrencias(
        status=status_filtro,
        turma_id=turma_id_filtro,
        nome_estudante=str(nome_estudante or "").strip() or None,
        data_inicial=data_inicial_norm,
        data_final=data_final_norm,
    )


@router.get("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def buscar_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.get("/ocorrencias/{ocorrencia_id}/pdf")
def gerar_pdf_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    ocorrencia = _montar_resposta_ocorrencia(ocorrencia_id)
    turma = buscar_turma_por_id(int(ocorrencia.get("turma_id") or 0))
    pdf_bytes = gerar_pdf_ocorrencia_registro(ocorrencia, turma=turma)
    nome_arquivo = _nome_arquivo_pdf_ocorrencia(ocorrencia)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nome_arquivo}"'},
    )


@router.patch("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_parcial_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    atual = buscar_ocorrencia_por_id(ocorrencia_id)
    if not atual:
        raise HTTPException(404, "Ocorrencia nao encontrada.")

    dados_brutos = _model_to_dict(payload, exclude_unset=True)
    if not dados_brutos:
        raise HTTPException(400, "Informe ao menos um campo para atualizar.")

    dados_validados = {}
    regimento_item_ids_validados = None

    if {"nome_estudante", "estudante_id", "turma_id"} & set(dados_brutos.keys()):
        turma_id_merge = _validar_turma_id(dados_brutos.get("turma_id", atual["turma_id"]))
        nome_estudante_merge, estudante_id_merge = _resolver_dados_estudante(
            nome_estudante=dados_brutos.get("nome_estudante", atual["nome_estudante"]),
            estudante_id=dados_brutos.get("estudante_id", atual.get("estudante_id")),
            turma_id=turma_id_merge,
        )
        dados_validados["turma_id"] = turma_id_merge
        dados_validados["nome_estudante"] = nome_estudante_merge
        dados_validados["estudante_id"] = estudante_id_merge
    elif "turma_id" in dados_brutos:
        dados_validados["turma_id"] = _validar_turma_id(dados_brutos["turma_id"])

    if {"professor_requerente", "professor_requerente_id"} & set(dados_brutos.keys()):
        professor_nome_merge, professor_id_merge = _resolver_dados_professor(
            professor_requerente=dados_brutos.get(
                "professor_requerente",
                atual["professor_requerente"],
            ),
            professor_requerente_id=dados_brutos.get(
                "professor_requerente_id",
                atual.get("professor_requerente_id"),
            ),
        )
        dados_validados["professor_requerente"] = professor_nome_merge
        dados_validados["professor_requerente_id"] = professor_id_merge

    if "disciplina" in dados_brutos:
        dados_validados["disciplina"] = _texto_obrigatorio(
            dados_brutos["disciplina"],
            "Disciplina",
        )
    if "data_ocorrencia" in dados_brutos:
        dados_validados["data_ocorrencia"] = _validar_data_iso(
            dados_brutos["data_ocorrencia"],
            "Data da ocorrencia",
        )
    if "aula" in dados_brutos:
        turma_id_para_aula = int(dados_validados.get("turma_id", atual["turma_id"]))
        dados_validados["aula"] = _validar_faixa_aula_por_turma(
            dados_brutos["aula"],
            turma_id_para_aula,
        )
    elif "turma_id" in dados_validados:
        # Ao trocar turma, garante que a aula atual também pertença à faixa válida do novo turno.
        dados_validados["aula"] = _validar_faixa_aula_por_turma(
            atual.get("aula"),
            int(dados_validados["turma_id"]),
        )
    if "horario_ocorrencia" in dados_brutos:
        dados_validados["horario_ocorrencia"] = _validar_horario_ocorrencia(
            dados_brutos["horario_ocorrencia"]
        )
    if "descricao" in dados_brutos:
        dados_validados["descricao"] = _texto_obrigatorio(
            dados_brutos["descricao"],
            "Descricao",
            max_len=5000,
        )
    if "regimento_item_ids" in dados_brutos:
        regimento_item_ids_validados = _normalizar_regimento_item_ids(
            dados_brutos.get("regimento_item_ids")
        )
    if "acao_aplicada" in dados_brutos:
        dados_validados["acao_aplicada"] = _validar_acao_aplicada(dados_brutos["acao_aplicada"])
    if "status" in dados_brutos:
        dados_validados["status"] = _validar_status(dados_brutos["status"])

    if not dados_validados and regimento_item_ids_validados is None:
        raise HTTPException(400, "Nenhum campo valido informado para atualizacao.")

    if regimento_item_ids_validados is not None or "acao_aplicada" in dados_validados:
        acao_para_validar = str(dados_validados.get("acao_aplicada", atual.get("acao_aplicada") or "")).strip()
        if regimento_item_ids_validados is not None:
            itens_para_validar = (
                buscar_regimento_itens_por_ids(regimento_item_ids_validados)
                if regimento_item_ids_validados
                else []
            )
        else:
            itens_para_validar = list(atual.get("regimento_itens") or [])
        _validar_acao_compativel_com_base_legal(acao_para_validar, itens_para_validar)

    alterado = True
    if dados_validados:
        try:
            alterado = atualizar_ocorrencia(ocorrencia_id, dados_validados)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    if regimento_item_ids_validados is not None:
        try:
            salvar_regimento_itens_ocorrencia(ocorrencia_id, regimento_item_ids_validados)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_ocorrencia(ocorrencia_id)


@router.put("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def atualizar_ocorrencia_api(
    ocorrencia_id: int,
    payload: OcorrenciaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    return atualizar_ocorrencia_parcial_api(ocorrencia_id, payload, usuario)


@router.delete("/ocorrencias/{ocorrencia_id}")
def remover_ocorrencia_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    removido = remover_ocorrencia(ocorrencia_id)
    if not removido:
        raise HTTPException(404, "Ocorrencia nao encontrada.")
    return {"mensagem": "Ocorrencia excluida com sucesso."}


@router.post("/ocorrencias/{ocorrencia_id}/excluir")
def remover_ocorrencia_fallback_api(ocorrencia_id: int, usuario=Depends(get_usuario_logado)):
    return remover_ocorrencia_api(ocorrencia_id, usuario)


@router.get("/estudantes", response_model=list[EstudanteOut])
def listar_estudantes_api(
    nome: str | None = Query(default=None),
    turma_id: int | None = Query(default=None),
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    turma_id_filtro = None
    if turma_id is not None:
        turma_id_filtro = _validar_turma_id(turma_id)

    return listar_estudantes(
        incluir_inativos=incluir_inativos,
        nome=str(nome or "").strip() or None,
        turma_id=turma_id_filtro,
    )


@router.get("/estudantes/{estudante_id}", response_model=EstudanteOut)
def buscar_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_estudante(estudante_id)


@router.post("/estudantes", response_model=EstudanteOut)
def criar_estudante_api(payload: EstudanteCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    turma_id = _validar_turma_id(payload.turma_id)
    try:
        estudante_id = criar_estudante(
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=True,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_estudante(estudante_id)


@router.post("/estudantes/importar", response_model=ImportacaoCsvOut)
@router.post("/estudantes/importar-csv", response_model=ImportacaoCsvOut)
def importar_estudantes_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_estudantes(arquivo)
        return importar_estudantes_arquivo(
            conteudo,
            nome_arquivo=nome_arquivo,
            tipo_conteudo=tipo_conteudo,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/estudantes/{estudante_id}", response_model=EstudanteOut)
def atualizar_estudante_api(
    estudante_id: int,
    payload: EstudanteUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_estudante_por_id(estudante_id):
        raise HTTPException(404, "Estudante nao encontrado.")

    turma_id = _validar_turma_id(payload.turma_id)
    try:
        alterado = atualizar_estudante(
            estudante_id=estudante_id,
            nome=_texto_obrigatorio(payload.nome, "Nome do estudante"),
            turma_id=turma_id,
            ativo=bool(payload.ativo),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return _montar_resposta_estudante(estudante_id)


@router.put("/estudantes/{estudante_id}/status")
def atualizar_status_estudante_api(
    estudante_id: int,
    payload: EstudanteStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    alterado = atualizar_status_estudante(estudante_id, bool(payload.ativo))
    if not alterado:
        raise HTTPException(404, "Estudante nao encontrado.")
    return {"mensagem": "Status do estudante atualizado com sucesso."}


@router.delete("/estudantes/{estudante_id}")
def remover_estudante_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    removido, ocorrencias_desvinculadas = remover_estudante(estudante_id)
    if not removido:
        raise HTTPException(404, "Estudante nao encontrado.")
    return {
        "mensagem": "Estudante excluido com sucesso.",
        "ocorrencias_desvinculadas": ocorrencias_desvinculadas,
    }


@router.post("/estudantes/{estudante_id}/excluir")
def remover_estudante_fallback_api(estudante_id: int, usuario=Depends(get_usuario_logado)):
    return remover_estudante_api(estudante_id, usuario)


@router.get("/leis", response_model=list[LeiOut])
def listar_leis_api(usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return listar_leis()


@router.get("/leis/{lei_id}", response_model=LeiOut)
def buscar_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_lei(lei_id)


@router.post("/leis", response_model=LeiOut)
def criar_lei_api(payload: LeiCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        lei_id = criar_lei(
            nome=_texto_obrigatorio(payload.nome, "Nome da lei", max_len=120),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_lei(lei_id)


@router.put("/leis/{lei_id}", response_model=LeiOut)
def atualizar_lei_api(
    lei_id: int,
    payload: LeiUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_lei_por_id(lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        alterado = atualizar_lei(
            lei_id=lei_id,
            nome=_texto_obrigatorio(payload.nome, "Nome da lei", max_len=120),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Lei nao encontrada.")
    return _montar_resposta_lei(lei_id)


@router.delete("/leis/{lei_id}")
def remover_lei_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_lei(lei_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Lei nao encontrada.")
    return {"mensagem": "Lei excluida com sucesso."}


@router.post("/leis/{lei_id}/excluir")
def remover_lei_fallback_api(lei_id: int, usuario=Depends(get_usuario_logado)):
    return remover_lei_api(lei_id, usuario)


@router.get("/artigos", response_model=list[ArtigoOut])
def listar_artigos_api(
    lei_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_artigos(lei_id=lei_id)


@router.get("/artigos/{artigo_id}", response_model=ArtigoOut)
def buscar_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_artigo(artigo_id)


@router.post("/artigos", response_model=ArtigoOut)
def criar_artigo_api(payload: ArtigoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_lei_por_id(payload.lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        artigo_id = criar_artigo(
            lei_id=payload.lei_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do artigo", max_len=120),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do artigo", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_artigo(artigo_id)


@router.put("/artigos/{artigo_id}", response_model=ArtigoOut)
def atualizar_artigo_api(
    artigo_id: int,
    payload: ArtigoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_artigo_por_id(artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    if not buscar_lei_por_id(payload.lei_id):
        raise HTTPException(404, "Lei nao encontrada.")
    try:
        alterado = atualizar_artigo(
            artigo_id=artigo_id,
            lei_id=payload.lei_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do artigo", max_len=120),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do artigo", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Artigo nao encontrado.")
    return _montar_resposta_artigo(artigo_id)


@router.delete("/artigos/{artigo_id}")
def remover_artigo_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_artigo(artigo_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Artigo nao encontrado.")
    return {"mensagem": "Artigo excluido com sucesso."}


@router.post("/artigos/{artigo_id}/excluir")
def remover_artigo_fallback_api(artigo_id: int, usuario=Depends(get_usuario_logado)):
    return remover_artigo_api(artigo_id, usuario)


@router.get("/incisos", response_model=list[IncisoOut])
def listar_incisos_api(
    artigo_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_incisos(artigo_id=artigo_id)


@router.get("/incisos/{inciso_id}", response_model=IncisoOut)
def buscar_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_inciso(inciso_id)


@router.post("/incisos", response_model=IncisoOut)
def criar_inciso_api(payload: IncisoCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_artigo_por_id(payload.artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    try:
        inciso_id = criar_inciso(
            artigo_id=payload.artigo_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do inciso", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do inciso", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_inciso(inciso_id)


@router.put("/incisos/{inciso_id}", response_model=IncisoOut)
def atualizar_inciso_api(
    inciso_id: int,
    payload: IncisoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_inciso_por_id(inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    if not buscar_artigo_por_id(payload.artigo_id):
        raise HTTPException(404, "Artigo nao encontrado.")
    try:
        alterado = atualizar_inciso(
            inciso_id=inciso_id,
            artigo_id=payload.artigo_id,
            numero=_texto_obrigatorio(payload.numero, "Numero do inciso", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao do inciso", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Inciso nao encontrado.")
    return _montar_resposta_inciso(inciso_id)


@router.delete("/incisos/{inciso_id}")
def remover_inciso_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_inciso(inciso_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Inciso nao encontrado.")
    return {"mensagem": "Inciso excluido com sucesso."}


@router.post("/incisos/{inciso_id}/excluir")
def remover_inciso_fallback_api(inciso_id: int, usuario=Depends(get_usuario_logado)):
    return remover_inciso_api(inciso_id, usuario)


@router.get("/alineas", response_model=list[AlineaOut])
def listar_alineas_api(
    inciso_id: int | None = Query(default=None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_alineas(inciso_id=inciso_id)


@router.get("/alineas/{alinea_id}", response_model=AlineaOut)
def buscar_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_alinea(alinea_id)


@router.post("/alineas", response_model=AlineaOut)
def criar_alinea_api(payload: AlineaCreateIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    if not buscar_inciso_por_id(payload.inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    try:
        alinea_id = criar_alinea(
            inciso_id=payload.inciso_id,
            identificador=_texto_obrigatorio(payload.identificador, "Identificador da alinea", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao da alinea", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_alinea(alinea_id)


@router.put("/alineas/{alinea_id}", response_model=AlineaOut)
def atualizar_alinea_api(
    alinea_id: int,
    payload: AlineaUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_alinea_por_id(alinea_id):
        raise HTTPException(404, "Alinea nao encontrada.")
    if not buscar_inciso_por_id(payload.inciso_id):
        raise HTTPException(404, "Inciso nao encontrado.")
    try:
        alterado = atualizar_alinea(
            alinea_id=alinea_id,
            inciso_id=payload.inciso_id,
            identificador=_texto_obrigatorio(payload.identificador, "Identificador da alinea", max_len=40),
            descricao=_texto_obrigatorio(payload.descricao, "Descricao da alinea", max_len=5000),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not alterado:
        raise HTTPException(404, "Alinea nao encontrada.")
    return _montar_resposta_alinea(alinea_id)


@router.delete("/alineas/{alinea_id}")
def remover_alinea_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_alinea(alinea_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Alinea nao encontrada.")
    return {"mensagem": "Alinea excluida com sucesso."}


@router.post("/alineas/{alinea_id}/excluir")
def remover_alinea_fallback_api(alinea_id: int, usuario=Depends(get_usuario_logado)):
    return remover_alinea_api(alinea_id, usuario)


@router.get("/regimento-itens", response_model=list[RegimentoItemOut])
def listar_regimento_itens_api(
    incluir_inativos: bool = Query(default=True),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    return listar_regimento_itens(incluir_inativos=incluir_inativos)


@router.get("/regimento-itens/{regimento_item_id}", response_model=RegimentoItemOut)
def buscar_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    return _montar_resposta_regimento_item(regimento_item_id)


@router.delete("/regimento-itens/{regimento_item_id}")
def remover_regimento_item_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestor(usuario)
    try:
        removido = remover_regimento_item(regimento_item_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removido:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return {"mensagem": "Item da base legal excluido com sucesso."}


@router.post("/regimento-itens/{regimento_item_id}/excluir")
def remover_regimento_item_fallback_api(regimento_item_id: int, usuario=Depends(get_usuario_logado)):
    return remover_regimento_item_api(regimento_item_id, usuario)


@router.post("/regimento-itens", response_model=RegimentoItemOut)
def criar_regimento_item_api(
    payload: RegimentoItemCreateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    dados = _normalizar_payload_regimento(payload)
    try:
        regimento_item_id = criar_regimento_item(
            lei_nome=dados["lei_nome"],
            artigo_numero=dados["artigo_numero"],
            artigo_descricao=dados["artigo_descricao"],
            inciso_numero=dados["inciso_numero"],
            inciso_descricao=dados["inciso_descricao"],
            alinea_identificador=dados["alinea_identificador"],
            alinea_descricao=dados["alinea_descricao"],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _montar_resposta_regimento_item(regimento_item_id)


@router.post("/regimento-itens/importar", response_model=ImportacaoCsvOut)
@router.post("/regimento-itens/importar-csv", response_model=ImportacaoCsvOut)
def importar_regimento_itens_arquivo_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    try:
        conteudo, nome_arquivo, tipo_conteudo = _ler_upload_base_legal(arquivo)
        return importar_base_legal_arquivo(
            conteudo,
            nome_arquivo=nome_arquivo,
            tipo_conteudo=tipo_conteudo,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/regimento-itens/{regimento_item_id}", response_model=RegimentoItemOut)
def atualizar_regimento_item_api(
    regimento_item_id: int,
    payload: RegimentoItemUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    if not buscar_regimento_item_por_id(regimento_item_id):
        raise HTTPException(404, "Item do regimento nao encontrado.")

    dados = _normalizar_payload_regimento(payload)
    try:
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
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not alterado:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return _montar_resposta_regimento_item(regimento_item_id)


@router.put("/regimento-itens/{regimento_item_id}/status")
def atualizar_status_regimento_item_api(
    regimento_item_id: int,
    payload: RegimentoItemStatusIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestor(usuario)
    alterado = atualizar_status_regimento_item(regimento_item_id, bool(payload.ativo))
    if not alterado:
        raise HTTPException(404, "Item do regimento nao encontrado.")
    return {"mensagem": "Status do item do regimento atualizado com sucesso."}
