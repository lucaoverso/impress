import sqlite3
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from auth import get_usuario_logado
from db.apc import (
    agendar_apc_preview_job,
    atualizar_apc_envio,
    atualizar_apc_periodo,
    buscar_apc_envio_por_id,
    buscar_apc_periodo_por_id,
    buscar_apc_preview_job_por_envio,
    concluir_apc_preview_job,
    criar_apc_envio,
    criar_apc_periodo,
    excluir_apc_envio,
    excluir_apc_periodo,
    listar_anos_letivos_apc,
    listar_apc_destinatarios,
    listar_apc_envios,
    listar_apc_periodos,
    substituir_apc_destinatarios,
)
from db.docencia import listar_atribuicoes_docentes
from db.horario_escolar import listar_anos_letivos_horario_escolar, listar_horarios_escolares
from db.usuarios import listar_professores_agendamento
from models import ApcEnvioOut, ApcPeriodoIn, ApcPeriodoOut, ApcPeriodoUpdateIn
from modules.apc_review.schemas import ApcReviewUpdateIn
from modules.apc_review.service import update_submission_review
from modules.apc_activity import repository as apc_activity_repository
from modules.apc_activity.image_service import (
    MAX_IMAGE_BYTES,
    resolve_activity_image,
    store_activity_image,
)
from modules.apc_activity.schemas import ApcActivityIn, ApcActivityOut, ApcActivityPreviewIn
from modules.apc_activity.service import (
    prepare_activity_data,
    render_preview as render_activity_preview,
    save_activity,
)
from modules.audit.models import AuditCategory, AuditOutcome
from modules.audit.service import record_event
from modules.printing.attachment_printing import imprimir_anexo_pdf
from services.apc_service import (
    APC_PUBLICO_ALVO_HORARIO_DIA,
    APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS,
    APC_PUBLICO_ALVO_TODOS_PROFESSORES,
    agrupar_destinatarios_selecionados_apc,
    agrupar_horarios_professor_dia,
    agrupar_professores_elegiveis,
    chave_entrega_apc,
    contexto_apc_anos,
    enriquecer_periodo_apc,
    filtrar_horarios_por_tipo_entrega,
    intervalo_mes_referencia,
    montar_painel_periodo_apc,
    montar_painel_professor_apc,
    nome_arquivo_armazenado,
    nome_publico_arquivo_apc,
    nome_publico_alvo,
    nome_tipo_entrega,
    normalizar_data_apc,
    normalizar_prazo_envio,
    normalizar_publico_alvo,
    normalizar_tipo_entrega,
    ordenar_periodos_apc,
    periodo_apc_aberto,
    validar_mes_referencia,
    APC_TIPO_ENTREGA_APC,
    APC_TIPO_ENTREGA_GERAL,
    APC_TIPO_ENTREGA_PROVA_BIMESTRAL,
)
from services.apc_preview_service import gerar_preview_pdf_apc
from services.apc_recipient_service import (
    group_recipient_options,
    merge_recipient_options,
)
from services.file_service import arquivo_suportado
from services.horario_escolar_service import validar_ano_letivo

from .common import normalizar_cargo_usuario, usuario_eh_professor, usuario_tem_acesso_coordenacao
from .config import APC_DIR, FORMATOS_UPLOAD_DESCRICAO

router = APIRouter()
logger = logging.getLogger(__name__)


def _pode_gerir_apc(usuario: dict) -> bool:
    return bool(usuario_tem_acesso_coordenacao(usuario))


def _exigir_gestao_apc(usuario: dict):
    if not _pode_gerir_apc(usuario):
        raise HTTPException(403, "Acesso negado.")
    return usuario


def _garantir_diretorio_apc() -> Path:
    caminho = Path(APC_DIR)
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def _garantir_diretorio_preview_apc() -> Path:
    caminho = _garantir_diretorio_apc() / "previews"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def _remover_arquivo_se_existir(caminho: Path):
    try:
        caminho.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _resolver_caminho_envio_seguro(caminho_arquivo: str) -> Path:
    caminho_base = _garantir_diretorio_apc().resolve(strict=False)
    caminho = Path(str(caminho_arquivo or "")).resolve(strict=False)
    try:
        caminho.relative_to(caminho_base)
    except ValueError as exc:
        raise HTTPException(409, "O arquivo vinculado a este envio esta fora do diretorio configurado.") from exc

    if not caminho.exists() or not caminho.is_file():
        raise HTTPException(404, "Arquivo do envio nao encontrado.")
    return caminho


def _resolver_caminho_preview_seguro(caminho_arquivo: str) -> Path | None:
    caminho_bruto = str(caminho_arquivo or "").strip()
    if not caminho_bruto:
        return None

    caminho_base = _garantir_diretorio_preview_apc().resolve(strict=False)
    caminho = Path(caminho_bruto).resolve(strict=False)
    try:
        caminho.relative_to(caminho_base)
    except ValueError:
        return None

    if not caminho.exists() or not caminho.is_file():
        return None
    return caminho


def _caminho_preview_cache(job: dict) -> Path:
    return _garantir_diretorio_preview_apc() / (
        f"apc_preview_{int(job.get('envio_id') or 0)}_{int(job.get('id') or 0)}.pdf"
    )


def _buscar_preview_cache_pronto(envio_id: int) -> Path | None:
    job = buscar_apc_preview_job_por_envio(int(envio_id))
    if not job or str(job.get("status") or "").upper() != "CONCLUIDO":
        return None
    return _resolver_caminho_preview_seguro(str(job.get("preview_pdf_path") or ""))


def _remover_preview_cache_envio(envio_id: int):
    job = buscar_apc_preview_job_por_envio(int(envio_id))
    if not job:
        return
    caminho = _resolver_caminho_preview_seguro(str(job.get("preview_pdf_path") or ""))
    if caminho:
        _remover_arquivo_se_existir(caminho)


def _agendar_preview_apc(envio: dict):
    try:
        agendar_apc_preview_job(
            envio_id=int(envio["id"]),
            arquivo_path=str(envio.get("arquivo_path") or ""),
            arquivo_nome_original=str(envio.get("arquivo_nome_original") or ""),
        )
    except Exception:
        logger.exception("Falha ao agendar preview APC para envio %s", envio.get("id"))


def _salvar_preview_cache(envio: dict, conteudo_pdf: bytes):
    try:
        job = buscar_apc_preview_job_por_envio(int(envio["id"]))
        if not job:
            job = agendar_apc_preview_job(
                envio_id=int(envio["id"]),
                arquivo_path=str(envio.get("arquivo_path") or ""),
                arquivo_nome_original=str(envio.get("arquivo_nome_original") or ""),
            )
        caminho_pdf = _caminho_preview_cache(job)
        caminho_pdf.write_bytes(conteudo_pdf)
        concluir_apc_preview_job(int(job["id"]), str(caminho_pdf))
    except Exception:
        logger.exception("Falha ao salvar cache de preview APC para envio %s", envio.get("id"))


def _dados_periodo_payload(payload: ApcPeriodoIn | ApcPeriodoUpdateIn) -> dict:
    try:
        ano_letivo = int(payload.ano_letivo)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Ano letivo invalido.") from exc

    if ano_letivo < 2000 or ano_letivo > 2100:
        raise HTTPException(400, "Ano letivo invalido.")

    try:
        data_referencia = normalizar_data_apc(payload.data_referencia)
        prazo_envio = normalizar_prazo_envio(data_referencia, payload.prazo_envio)
        publico_alvo = normalizar_publico_alvo(payload.publico_alvo)
        tipo_entrega = normalizar_tipo_entrega(payload.tipo_entrega)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    titulo = str(payload.titulo or "Documento").strip() or "Documento"
    observacao = str(payload.observacao or "").strip()
    return {
        "ano_letivo": ano_letivo,
        "data_referencia": data_referencia,
        "prazo_envio": prazo_envio,
        "titulo": titulo,
        "observacao": observacao,
        "publico_alvo": publico_alvo,
        "tipo_entrega": tipo_entrega,
    }


def _chave_destinatario(item: dict) -> tuple[int, int, int]:
    return (
        int(item.get("professor_id") or 0),
        int(item.get("turma_id") or 0),
        int(item.get("disciplina_id") or 0),
    )


def _listar_vinculos_destinatarios_ano(ano_letivo: int) -> list[dict]:
    grupos: dict[tuple[int, int, int], dict] = {}

    for item in listar_horarios_escolares(ano_letivo=int(ano_letivo)):
        chave = _chave_destinatario(item)
        if chave[0] <= 0 or chave[1] <= 0 or chave[2] <= 0:
            continue
        grupos.setdefault(
            chave,
            {
                "professor_id": chave[0],
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
                "turma_id": chave[1],
                "turma_nome": str(item.get("turma_nome") or "").strip(),
                "disciplina_id": chave[2],
                "disciplina_nome": str(item.get("disciplina_nome") or "").strip(),
            },
        )

    for item in listar_atribuicoes_docentes(incluir_inativos=False):
        chave = (
            int(item.get("professor_id") or 0),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        )
        if chave[0] <= 0 or chave[1] <= 0 or chave[2] <= 0:
            continue
        grupos.setdefault(
            chave,
            {
                "professor_id": chave[0],
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
                "turma_id": chave[1],
                "turma_nome": str(item.get("turma_nome") or "").strip(),
                "disciplina_id": chave[2],
                "disciplina_nome": str(item.get("disciplina_nome") or "").strip(),
            },
        )

    return sorted(
        grupos.values(),
        key=lambda item: (
            str(item.get("professor_nome") or "").casefold(),
            str(item.get("turma_nome") or "").casefold(),
            str(item.get("disciplina_nome") or "").casefold(),
            int(item.get("professor_id") or 0),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        ),
    )


def _normalizar_destinatarios_payload(
    payload: ApcPeriodoIn | ApcPeriodoUpdateIn,
    *,
    ano_letivo: int,
    publico_alvo: str,
    periodo_id: int | None = None,
) -> list[dict]:
    itens = []
    vistos: set[tuple[int, int, int]] = set()

    if publico_alvo != APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS:
        return itens

    opcoes_validas = {
        _chave_destinatario(item): item for item in _listar_vinculos_destinatarios_ano(ano_letivo)
    }
    if periodo_id is not None:
        opcoes_validas.update(
            {
                _chave_destinatario(item): item
                for item in listar_apc_destinatarios(periodo_id=int(periodo_id))
            }
        )

    for bruto in list(payload.destinatarios or []):
        item = {
            "professor_id": int(getattr(bruto, "professor_id", 0) or 0),
            "turma_id": int(getattr(bruto, "turma_id", 0) or 0),
            "disciplina_id": int(getattr(bruto, "disciplina_id", 0) or 0),
        }
        chave = _chave_destinatario(item)
        if chave[0] <= 0 or chave[1] <= 0 or chave[2] <= 0:
            raise HTTPException(
                400,
                "Selecione professor, turma e disciplina para cada destinatario da solicitacao.",
            )
        if chave in vistos:
            continue
        if chave not in opcoes_validas:
            raise HTTPException(
                400,
                "Um dos destinatarios selecionados nao pertence aos vinculos ativos do ano letivo informado.",
            )
        itens.append(item)
        vistos.add(chave)

    if not itens:
        raise HTTPException(
            400,
            "Selecione ao menos um professor com sua respectiva turma e disciplina.",
        )

    return itens


def _obter_horarios_periodo(periodo: dict, professor_id: int | None = None) -> list[dict]:
    periodo_norm = enriquecer_periodo_apc(periodo)
    return listar_horarios_escolares(
        ano_letivo=int(periodo_norm["ano_letivo"]),
        professor_id=professor_id,
        dia_semana=periodo_norm["dia_semana"],
    )


def _obter_elegiveis_periodo(periodo: dict, professor_id: int | None = None) -> list[dict]:
    periodo_norm = enriquecer_periodo_apc(periodo)
    if periodo_norm["publico_alvo"] == APC_PUBLICO_ALVO_TODOS_PROFESSORES:
        professores = listar_professores_agendamento()
        if professor_id is not None:
            professores = [
                item for item in professores if int(item.get("id") or 0) == int(professor_id)
            ]
        return agrupar_professores_elegiveis(professores)

    if periodo_norm["publico_alvo"] == APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS:
        destinatarios = listar_apc_destinatarios(
            periodo_id=int(periodo_norm["id"]),
            professor_id=int(professor_id) if professor_id is not None else None,
        )
        return agrupar_destinatarios_selecionados_apc(destinatarios)

    horarios = _obter_horarios_periodo(periodo_norm, professor_id=professor_id)
    horarios_filtrados = filtrar_horarios_por_tipo_entrega(
        horarios,
        periodo_norm["tipo_entrega"],
    )
    return agrupar_horarios_professor_dia(horarios_filtrados)


def _selecionar_item_professor_periodo(
    painel: dict | None,
    *,
    turma_id: int = 0,
    disciplina_id: int = 0,
) -> dict | None:
    itens = list((painel or {}).get("itens") or [])
    if not itens:
        return None

    chave = chave_entrega_apc(
        int((painel or {}).get("professor_id") or 0),
        int(turma_id or 0),
        int(disciplina_id or 0),
    )
    for item in itens:
        if chave_entrega_apc(
            int(item.get("professor_id") or 0),
            int(item.get("turma_id") or 0),
            int(item.get("disciplina_id") or 0),
        ) == chave:
            return item

    if int(turma_id or 0) == 0 and int(disciplina_id or 0) == 0 and len(itens) == 1:
        return itens[0]
    return None


def _coercer_form_int(valor, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        try:
            return int(getattr(valor, "default", padrao) or padrao)
        except (TypeError, ValueError):
            return int(padrao)


def _resolver_visao_apc(usuario: dict, visao: str | None = None) -> str:
    valor = str(visao or "").strip().lower()
    if valor and valor not in {"docente", "gestao"}:
        raise HTTPException(400, "Visao invalida para este modulo.")

    pode_gerir = _pode_gerir_apc(usuario)
    eh_professor = usuario_eh_professor(usuario)

    if valor == "gestao":
        if not pode_gerir:
            raise HTTPException(403, "Voce nao possui acesso a visao de gestao.")
        return "gestao"

    if valor == "docente":
        if not eh_professor:
            raise HTTPException(403, "Somente professores possuem visao docente.")
        return "docente"

    if pode_gerir and not eh_professor:
        return "gestao"
    if eh_professor:
        return "docente"
    if pode_gerir:
        return "gestao"
    raise HTTPException(403, "Acesso negado.")


def _anexar_destinatarios_configurados(payload: dict, periodo_id: int) -> dict:
    destinatarios = listar_apc_destinatarios(periodo_id=int(periodo_id))
    return {
        **payload,
        "destinatarios_configurados": destinatarios,
    }


def _montar_resumo_calendario_para_usuario(periodo: dict, usuario: dict, visao: str) -> dict | None:
    periodo_norm = enriquecer_periodo_apc(periodo)
    elegiveis = _obter_elegiveis_periodo(periodo_norm)

    if visao == "gestao":
        painel = montar_painel_periodo_apc(
            periodo_norm,
            elegiveis,
            listar_apc_envios(periodo_id=int(periodo_norm["id"])),
        )
        return {
            **painel["periodo"],
            "total_elegiveis": painel["total_elegiveis"],
            "total_enviados": painel["total_enviados"],
            "total_pendentes": painel["total_pendentes"],
            "total_aprovados": int(painel.get("total_aprovados") or 0),
            "total_impressos": int(painel.get("total_impressos") or 0),
            "total_ajustes": int(painel.get("total_ajustes") or 0),
            "total_aguardando_revisao": int(
                painel.get("total_aguardando_revisao") or 0
            ),
            "enviado": False,
            "total_aulas": 0,
            "total_entregas": painel["total_elegiveis"],
        }

    painel_professor = montar_painel_professor_apc(
        periodo_norm,
        int(usuario["id"]),
        _obter_elegiveis_periodo(periodo_norm, professor_id=int(usuario["id"])),
        listar_apc_envios(
            periodo_id=int(periodo_norm["id"]),
            professor_id=int(usuario["id"]),
        ),
    )
    if not painel_professor:
        return None

    return {
        **painel_professor["periodo"],
        "total_elegiveis": int(painel_professor.get("total_entregas") or 0),
        "total_enviados": int(painel_professor.get("total_enviadas") or 0),
        "total_pendentes": int(painel_professor.get("total_pendentes") or 0),
        "total_aprovados": int(painel_professor.get("total_aprovados") or 0),
        "total_impressos": int(painel_professor.get("total_impressos") or 0),
        "total_ajustes": int(painel_professor.get("total_ajustes") or 0),
        "total_aguardando_revisao": int(
            painel_professor.get("total_aguardando_revisao") or 0
        ),
        "enviado": int(painel_professor.get("total_pendentes") or 0) == 0,
        "total_aulas": int(painel_professor["total_aulas"]),
        "total_entregas": int(painel_professor.get("total_entregas") or 0),
    }


def _montar_resumo_gestao_apc(periodo: dict) -> dict:
    painel = montar_painel_periodo_apc(
        enriquecer_periodo_apc(periodo),
        _obter_elegiveis_periodo(periodo),
        listar_apc_envios(periodo_id=int(periodo["id"])),
    )
    itens = list(painel.get("itens") or [])
    envios = [
        item["envio"]
        for item in itens
        if isinstance(item.get("envio"), dict)
    ]

    def valores_unicos(campo: str) -> list[str]:
        return sorted(
            {
                str(item.get(campo) or "").strip()
                for item in itens
                if str(item.get(campo) or "").strip()
            },
            key=str.casefold,
        )

    return {
        **painel["periodo"],
        "total_elegiveis": painel["total_elegiveis"],
        "total_enviados": painel["total_enviados"],
        "total_pendentes": painel["total_pendentes"],
        "total_aprovados": int(painel.get("total_aprovados") or 0),
        "total_impressos": int(painel.get("total_impressos") or 0),
        "total_ajustes": int(painel.get("total_ajustes") or 0),
        "total_aguardando_revisao": int(
            painel.get("total_aguardando_revisao") or 0
        ),
        "professores": valores_unicos("professor_nome"),
        "disciplinas": valores_unicos("disciplina_nome"),
        "turmas": valores_unicos("turma_nome"),
        "ultimo_envio_em": max(
            (str(envio.get("enviado_em") or "") for envio in envios),
            default="",
        ),
    }


@router.get("/apc/contexto")
def obter_contexto_apc_api(usuario=Depends(get_usuario_logado)):
    anos_existentes = sorted(
        set(listar_anos_letivos_apc()) | set(listar_anos_letivos_horario_escolar())
    )
    return {
        "anos_letivos": contexto_apc_anos(anos_existentes),
        "ano_letivo_atual": datetime.now().year,
        "mes_atual": datetime.now().strftime("%Y-%m"),
        "hoje": datetime.now().date().isoformat(),
        "publicos_alvo": [
            {
                "valor": APC_PUBLICO_ALVO_TODOS_PROFESSORES,
                "label": nome_publico_alvo(APC_PUBLICO_ALVO_TODOS_PROFESSORES),
            },
            {
                "valor": APC_PUBLICO_ALVO_HORARIO_DIA,
                "label": nome_publico_alvo(APC_PUBLICO_ALVO_HORARIO_DIA),
            },
            {
                "valor": APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS,
                "label": nome_publico_alvo(APC_PUBLICO_ALVO_PROFESSORES_SELECIONADOS),
            },
        ],
        "tipos_entrega": [
            {
                "valor": APC_TIPO_ENTREGA_GERAL,
                "label": nome_tipo_entrega(APC_TIPO_ENTREGA_GERAL),
            },
            {
                "valor": APC_TIPO_ENTREGA_APC,
                "label": nome_tipo_entrega(APC_TIPO_ENTREGA_APC),
            },
            {
                "valor": APC_TIPO_ENTREGA_PROVA_BIMESTRAL,
                "label": nome_tipo_entrega(APC_TIPO_ENTREGA_PROVA_BIMESTRAL),
            },
        ],
        "usuario": {
            "id": int(usuario["id"]),
            "nome": str(usuario.get("nome") or "").strip(),
            "cargo": normalizar_cargo_usuario(usuario),
            "pode_gerir": _pode_gerir_apc(usuario),
            "eh_professor": usuario_eh_professor(usuario),
        },
    }


@router.get("/apc/destinatarios/opcoes")
def listar_opcoes_destinatarios_apc_api(
    ano_letivo: int,
    periodo_id: int | None = None,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    try:
        ano_letivo_validado = validar_ano_letivo(int(ano_letivo))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    configurados = []
    if periodo_id is not None:
        periodo = buscar_apc_periodo_por_id(int(periodo_id))
        if not periodo:
            raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
        configurados = listar_apc_destinatarios(periodo_id=int(periodo_id))

    return {
        "ano_letivo": int(ano_letivo_validado),
        "professores": group_recipient_options(
            merge_recipient_options(
                _listar_vinculos_destinatarios_ano(int(ano_letivo_validado)),
                configurados,
            )
        ),
    }


@router.get("/apc/calendario")
def listar_calendario_apc_api(
    mes: str,
    ano_letivo: int | None = None,
    visao: str | None = None,
    usuario=Depends(get_usuario_logado),
):
    try:
        mes_norm = validar_mes_referencia(mes)
        data_inicio, data_fim = intervalo_mes_referencia(mes_norm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    visao_resolvida = _resolver_visao_apc(usuario, visao)
    ano_consulta = int(ano_letivo) if ano_letivo is not None else int(mes_norm[:4])
    filtros_periodo = {"ano_letivo": ano_consulta}
    if visao_resolvida == "gestao":
        filtros_periodo.update(
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    periodos = ordenar_periodos_apc(
        listar_apc_periodos(**filtros_periodo)
    )

    itens = []
    for periodo in periodos:
        resumo = _montar_resumo_calendario_para_usuario(periodo, usuario, visao_resolvida)
        if resumo is None:
            continue
        itens.append(resumo)

    return {
        "mes": mes_norm,
        "ano_letivo": int(ano_letivo) if ano_letivo is not None else None,
        "periodos": itens,
    }


@router.get("/apc/solicitacoes")
def listar_solicitacoes_gestao_apc_api(
    ano_letivo: int,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    try:
        ano_validado = validar_ano_letivo(int(ano_letivo))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    periodos = ordenar_periodos_apc(
        listar_apc_periodos(ano_letivo=int(ano_validado))
    )
    return {
        "ano_letivo": int(ano_validado),
        "periodos": [
            _montar_resumo_gestao_apc(periodo)
            for periodo in periodos
        ],
    }


@router.get("/apc/periodos/{periodo_id}")
def obter_periodo_apc_api(
    periodo_id: int,
    visao: str | None = None,
    usuario=Depends(get_usuario_logado),
):
    periodo = buscar_apc_periodo_por_id(periodo_id)
    if not periodo:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")

    visao_resolvida = _resolver_visao_apc(usuario, visao)
    elegiveis = _obter_elegiveis_periodo(periodo)
    if visao_resolvida == "gestao":
        return _anexar_destinatarios_configurados(
            montar_painel_periodo_apc(
                periodo,
                elegiveis,
                listar_apc_envios(periodo_id=periodo_id),
            ),
            periodo_id,
        )

    painel = montar_painel_professor_apc(
        periodo,
        int(usuario["id"]),
        _obter_elegiveis_periodo(periodo, professor_id=int(usuario["id"])),
        listar_apc_envios(periodo_id=periodo_id, professor_id=int(usuario["id"])),
    )
    if not painel:
        raise HTTPException(403, "Nenhuma entrega prevista para voce nesta data.")
    return painel


@router.post("/apc/periodos", response_model=ApcPeriodoOut)
def criar_periodo_apc_api(payload: ApcPeriodoIn, usuario=Depends(get_usuario_logado)):
    _exigir_gestao_apc(usuario)
    dados = _dados_periodo_payload(payload)
    destinatarios = _normalizar_destinatarios_payload(
        payload,
        ano_letivo=int(dados["ano_letivo"]),
        publico_alvo=str(dados["publico_alvo"] or ""),
    )
    try:
        periodo = criar_apc_periodo(
            ano_letivo=dados["ano_letivo"],
            data_referencia=dados["data_referencia"],
            prazo_envio=dados["prazo_envio"],
            titulo=dados["titulo"],
            observacao=dados["observacao"],
            publico_alvo=dados["publico_alvo"],
            tipo_entrega=dados["tipo_entrega"],
            criado_por_usuario_id=int(usuario["id"]),
        )
        if periodo and destinatarios:
            substituir_apc_destinatarios(int(periodo["id"]), destinatarios)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            409,
            "Ja existe uma solicitacao semelhante cadastrada para essa data no ano letivo.",
        ) from exc
    return enriquecer_periodo_apc(periodo)


@router.put("/apc/periodos/{periodo_id}", response_model=ApcPeriodoOut)
def atualizar_periodo_apc_api(
    periodo_id: int,
    payload: ApcPeriodoUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    if not buscar_apc_periodo_por_id(periodo_id):
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")

    dados = _dados_periodo_payload(payload)
    destinatarios = _normalizar_destinatarios_payload(
        payload,
        ano_letivo=int(dados["ano_letivo"]),
        publico_alvo=str(dados["publico_alvo"] or ""),
        periodo_id=periodo_id,
    )
    try:
        periodo = atualizar_apc_periodo(
            periodo_id=periodo_id,
            ano_letivo=dados["ano_letivo"],
            data_referencia=dados["data_referencia"],
            prazo_envio=dados["prazo_envio"],
            titulo=dados["titulo"],
            observacao=dados["observacao"],
            publico_alvo=dados["publico_alvo"],
            tipo_entrega=dados["tipo_entrega"],
        )
        substituir_apc_destinatarios(periodo_id, destinatarios)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            409,
            "Ja existe uma solicitacao semelhante cadastrada para essa data no ano letivo.",
        ) from exc

    if not periodo:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    return enriquecer_periodo_apc(periodo)


@router.delete("/apc/periodos/{periodo_id}")
def excluir_periodo_apc_api(periodo_id: int, usuario=Depends(get_usuario_logado)):
    _exigir_gestao_apc(usuario)
    if not buscar_apc_periodo_por_id(periodo_id):
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    try:
        removido = excluir_apc_periodo(periodo_id)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            409,
            "Nao e possivel excluir esta solicitacao porque ja existem arquivos enviados.",
        ) from exc
    if not removido:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    return {"mensagem": "Solicitacao de entrega removida com sucesso."}


@router.post("/apc/periodos/{periodo_id}/envio", response_model=ApcEnvioOut)
def enviar_arquivo_apc_api(
    periodo_id: int,
    turma_id: int = Form(0),
    disciplina_id: int = Form(0),
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    if not usuario_eh_professor(usuario):
        raise HTTPException(403, "Somente professores podem enviar arquivos.")

    periodo = buscar_apc_periodo_por_id(periodo_id)
    if not periodo:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    periodo_norm = enriquecer_periodo_apc(periodo)

    if not periodo_apc_aberto(periodo_norm):
        raise HTTPException(409, "O prazo de envio desta solicitacao ja foi encerrado.")

    if not arquivo or not arquivo.filename:
        raise HTTPException(400, "Arquivo nao enviado.")
    if not arquivo_suportado(arquivo.filename):
        raise HTTPException(400, f"Formato nao suportado. Envie {FORMATOS_UPLOAD_DESCRICAO}.")

    turma_id_valor = _coercer_form_int(turma_id, 0)
    disciplina_id_valor = _coercer_form_int(disciplina_id, 0)

    painel = montar_painel_professor_apc(
        periodo_norm,
        int(usuario["id"]),
        _obter_elegiveis_periodo(periodo_norm, professor_id=int(usuario["id"])),
        listar_apc_envios(periodo_id=periodo_id, professor_id=int(usuario["id"])),
    )
    if not painel:
        raise HTTPException(403, "Nao ha entrega prevista para voce nesta data.")

    item_envio = _selecionar_item_professor_periodo(
        painel,
        turma_id=turma_id_valor,
        disciplina_id=disciplina_id_valor,
    )
    if not item_envio:
        raise HTTPException(403, "Nao ha entrega prevista para essa disciplina nesta data.")

    conteudo = arquivo.file.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo vazio.")

    envio_existente = item_envio.get("envio")
    diretorio = _garantir_diretorio_apc()
    nome_cliente = str(arquivo.filename or "").strip()
    nome_publico = nome_publico_arquivo_apc(
        periodo_norm.get("titulo"),
        str(item_envio.get("professor_nome") or usuario.get("nome") or "").strip(),
        periodo_norm.get("data_referencia"),
        nome_cliente,
    )
    nome_destino = nome_arquivo_armazenado(
        periodo_id,
        int(usuario["id"]),
        nome_publico,
        turma_id=int(item_envio.get("turma_id") or 0),
        disciplina_id=int(item_envio.get("disciplina_id") or 0),
    )
    caminho_destino = diretorio / nome_destino

    try:
        with caminho_destino.open("wb") as destino:
            destino.write(conteudo)
    except OSError as exc:
        raise HTTPException(500, "Falha ao armazenar o arquivo enviado.") from exc

    try:
        if envio_existente:
            envio = atualizar_apc_envio(
                envio_id=int(envio_existente["id"]),
                arquivo_nome_cliente=nome_cliente,
                arquivo_nome_original=nome_publico,
                arquivo_path=str(caminho_destino),
                arquivo_tamanho=len(conteudo),
                arquivo_tipo=str(arquivo.content_type or "").strip(),
            )
            caminho_antigo = Path(str(envio_existente.get("arquivo_path") or "").strip())
            if caminho_antigo and caminho_antigo != caminho_destino:
                _remover_arquivo_se_existir(caminho_antigo)
        else:
            envio = criar_apc_envio(
                periodo_id=periodo_id,
                professor_usuario_id=int(usuario["id"]),
                turma_id=int(item_envio.get("turma_id") or 0),
                disciplina_id=int(item_envio.get("disciplina_id") or 0),
                arquivo_nome_cliente=nome_cliente,
                arquivo_nome_original=nome_publico,
                arquivo_path=str(caminho_destino),
                arquivo_tamanho=len(conteudo),
                arquivo_tipo=str(arquivo.content_type or "").strip(),
            )
    except sqlite3.IntegrityError as exc:
        _remover_arquivo_se_existir(caminho_destino)
        raise HTTPException(409, "Conflito ao registrar o envio do arquivo.") from exc
    except Exception:
        _remover_arquivo_se_existir(caminho_destino)
        raise

    if not envio:
        _remover_arquivo_se_existir(caminho_destino)
        raise HTTPException(500, "Falha ao registrar o envio do arquivo.")

    _remover_preview_cache_envio(int(envio["id"]))
    _agendar_preview_apc(envio)

    record_event(
        category=AuditCategory.ATTACHMENTS,
        action="attachment.submitted",
        outcome=AuditOutcome.SUCCESS,
        actor=usuario,
        description=f"Anexo enviado por {usuario.get('nome') or 'professor'}: {nome_cliente}.",
        entity_type="apc_submission",
        entity_id=envio.get("id"),
        metadata={
            "period_id": periodo_id,
            "class_id": item_envio.get("turma_id"),
            "subject_id": item_envio.get("disciplina_id"),
            "file_name": nome_cliente,
            "file_size": len(conteudo),
            "replaced_existing": bool(envio_existente),
        },
    )
    return envio


def _resolver_entrega_professor_apc(
    *, periodo_id: int, turma_id: int, disciplina_id: int, usuario: dict
) -> tuple[dict, dict]:
    if not usuario_eh_professor(usuario):
        raise HTTPException(403, "Somente professores podem criar atividades.")
    periodo = buscar_apc_periodo_por_id(periodo_id)
    if not periodo:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    periodo_norm = enriquecer_periodo_apc(periodo)
    if not periodo_apc_aberto(periodo_norm):
        raise HTTPException(409, "O prazo de envio desta solicitacao ja foi encerrado.")
    painel = montar_painel_professor_apc(
        periodo_norm,
        int(usuario["id"]),
        _obter_elegiveis_periodo(periodo_norm, professor_id=int(usuario["id"])),
        listar_apc_envios(periodo_id=periodo_id, professor_id=int(usuario["id"])),
    )
    item = _selecionar_item_professor_periodo(
        painel or {}, turma_id=int(turma_id or 0), disciplina_id=int(disciplina_id or 0)
    )
    if not item:
        raise HTTPException(403, "Nao ha entrega prevista para essa disciplina nesta data.")
    return periodo_norm, item


@router.post("/apc/atividade/imagens")
def enviar_imagem_atividade_apc_api(
    arquivo: UploadFile = File(...),
    usuario=Depends(get_usuario_logado),
):
    if not usuario_eh_professor(usuario):
        raise HTTPException(403, "Somente professores podem inserir imagens na APC.")
    content = arquivo.file.read(MAX_IMAGE_BYTES + 1)
    try:
        return store_activity_image(content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/apc/atividade/imagens/{token}")
def obter_imagem_atividade_apc_api(token: str, usuario=Depends(get_usuario_logado)):
    path = resolve_activity_image(token)
    if path is None:
        raise HTTPException(404, "Imagem nao encontrada.")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media_type)


@router.post("/apc/periodos/{periodo_id}/atividade/preview")
def visualizar_atividade_apc_api(
    periodo_id: int,
    payload: ApcActivityPreviewIn,
    usuario=Depends(get_usuario_logado),
):
    periodo, item = _resolver_entrega_professor_apc(
        periodo_id=periodo_id,
        turma_id=payload.turma_id,
        disciplina_id=payload.disciplina_id,
        usuario=usuario,
    )
    try:
        data = prepare_activity_data(
            payload, user=usuario, period=periodo, delivery=item, allow_incomplete=True
        )
        content = render_activity_preview(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response(content=content, media_type="application/pdf")


@router.post(
    "/apc/periodos/{periodo_id}/atividade",
    response_model=ApcActivityOut,
)
def criar_atividade_apc_api(
    periodo_id: int,
    payload: ApcActivityIn,
    usuario=Depends(get_usuario_logado),
):
    periodo, item = _resolver_entrega_professor_apc(
        periodo_id=periodo_id,
        turma_id=payload.turma_id,
        disciplina_id=payload.disciplina_id,
        usuario=usuario,
    )
    try:
        data = prepare_activity_data(payload, user=usuario, period=periodo, delivery=item)
        envio, atividade, _pdf = save_activity(
            data=data,
            period_id=periodo_id,
            user_id=int(usuario["id"]),
            existing=item.get("envio"),
            directory=_garantir_diretorio_apc(),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, "Nao foi possivel armazenar a atividade gerada.") from exc

    _remover_preview_cache_envio(int(envio["id"]))
    _agendar_preview_apc(envio)
    record_event(
        category=AuditCategory.ATTACHMENTS,
        action="attachment.generated",
        outcome=AuditOutcome.SUCCESS,
        actor=usuario,
        description=f"APC gerada por {usuario.get('nome') or 'professor'}.",
        entity_type="apc_submission",
        entity_id=envio.get("id"),
        metadata={
            "period_id": periodo_id,
            "class_id": item.get("turma_id"),
            "subject_id": item.get("disciplina_id"),
            "activity_columns": data["activity_columns"],
            "replaced_existing": bool(item.get("envio")),
        },
    )
    return {"envio": envio, "atividade": atividade}


@router.get("/apc/envios/{envio_id}/atividade")
def obter_atividade_apc_api(envio_id: int, usuario=Depends(get_usuario_logado)):
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")
    if not _pode_gerir_apc(usuario) and int(envio.get("professor_id") or 0) != int(usuario["id"]):
        raise HTTPException(403, "Acesso negado.")
    atividade = apc_activity_repository.get_generated_activity(envio_id)
    if not atividade:
        raise HTTPException(404, "Este anexo nao foi criado pelo gerador de APC.")
    return atividade


@router.put("/apc/envios/{envio_id}/revisao", response_model=ApcEnvioOut)
def revisar_envio_apc_api(
    envio_id: int,
    payload: ApcReviewUpdateIn,
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    envio = update_submission_review(
        submission_id=envio_id,
        status=payload.status,
        message=payload.mensagem,
        reviewer=usuario,
    )
    record_event(
        category=AuditCategory.ATTACHMENTS,
        action="attachment.reviewed",
        outcome=AuditOutcome.SUCCESS,
        actor=usuario,
        description=(
            f"Anexo de {envio.get('professor_nome') or 'professor'} revisado: "
            f"{envio.get('review_status')}."
        ),
        entity_type="apc_submission",
        entity_id=envio_id,
        metadata={
            "review_status": envio.get("review_status"),
            "target_user_id": envio.get("professor_id"),
        },
    )
    return envio


@router.delete("/apc/envios/{envio_id}")
def excluir_envio_apc_api(envio_id: int, usuario=Depends(get_usuario_logado)):
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")

    professor_id = int(envio.get("professor_id") or 0)
    if not usuario_eh_professor(usuario) or int(usuario["id"]) != professor_id:
        raise HTTPException(
            403,
            "Somente o professor responsavel pode remover este arquivo enquanto o prazo estiver aberto.",
        )

    periodo = buscar_apc_periodo_por_id(int(envio.get("periodo_id") or 0))
    if not periodo:
        raise HTTPException(404, "Solicitacao de entrega nao encontrada.")
    periodo_norm = enriquecer_periodo_apc(periodo)
    if not periodo_apc_aberto(periodo_norm):
        raise HTTPException(409, "O prazo de envio desta solicitacao ja foi encerrado.")

    caminho_arquivo = None
    try:
        caminho_arquivo = _resolver_caminho_envio_seguro(envio.get("arquivo_path"))
    except HTTPException as exc:
        if int(exc.status_code) != 404:
            raise

    _remover_preview_cache_envio(envio_id)

    if not excluir_apc_envio(envio_id):
        raise HTTPException(404, "Envio nao encontrado.")

    if caminho_arquivo:
        _remover_arquivo_se_existir(caminho_arquivo)

    return {"mensagem": "Arquivo removido com sucesso. Voce ja pode enviar novamente."}


@router.get("/apc/envios/{envio_id}/arquivo")
def baixar_arquivo_apc_api(envio_id: int, usuario=Depends(get_usuario_logado)):
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")

    professor_id = int(envio.get("professor_id") or 0)
    if not _pode_gerir_apc(usuario) and int(usuario["id"]) != professor_id:
        raise HTTPException(403, "Voce nao pode acessar este arquivo.")

    caminho = _resolver_caminho_envio_seguro(envio.get("arquivo_path"))
    media_type = str(envio.get("arquivo_tipo") or "").strip() or "application/octet-stream"
    return FileResponse(
        path=str(caminho),
        filename=str(envio.get("arquivo_nome_original") or caminho.name),
        media_type=media_type,
    )


@router.get("/apc/envios/{envio_id}/preview")
def visualizar_arquivo_apc_api(envio_id: int, usuario=Depends(get_usuario_logado)):
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")

    professor_id = int(envio.get("professor_id") or 0)
    if not _pode_gerir_apc(usuario) and int(usuario["id"]) != professor_id:
        raise HTTPException(403, "Voce nao pode acessar este arquivo.")

    caminho = _resolver_caminho_envio_seguro(envio.get("arquivo_path"))
    nome_arquivo = str(envio.get("arquivo_nome_original") or caminho.name)
    caminho_preview = _buscar_preview_cache_pronto(envio_id)
    if caminho_preview:
        return FileResponse(
            path=str(caminho_preview),
            media_type="application/pdf",
            headers={"Cache-Control": "no-store"},
        )

    try:
        conteudo_pdf = gerar_preview_pdf_apc(caminho, nome_arquivo)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, "Nao foi possivel preparar a visualizacao do anexo.") from exc

    _salvar_preview_cache(envio, conteudo_pdf)
    return Response(
        content=conteudo_pdf,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/apc/envios/{envio_id}/imprimir")
def imprimir_arquivo_apc_api(
    envio_id: int,
    copias: int = Form(...),
    paginas_por_folha: int = Form(1),
    duplex: bool = Form(False),
    orientacao: str = Form("retrato"),
    intervalo_paginas: str = Form(""),
    tags: list[str] = Form(default=[]),
    professor_id: int | None = Form(None),
    usuario=Depends(get_usuario_logado),
):
    _exigir_gestao_apc(usuario)
    envio = buscar_apc_envio_por_id(envio_id)
    if not envio:
        raise HTTPException(404, "Envio nao encontrado.")

    caminho = _resolver_caminho_envio_seguro(envio.get("arquivo_path"))
    nome_arquivo = str(envio.get("arquivo_nome_original") or caminho.name)
    try:
        caminho_preview = _buscar_preview_cache_pronto(envio_id)
        if caminho_preview:
            conteudo_pdf = caminho_preview.read_bytes()
        else:
            conteudo_pdf = gerar_preview_pdf_apc(caminho, nome_arquivo)
            _salvar_preview_cache(envio, conteudo_pdf)
        return imprimir_anexo_pdf(
            conteudo_pdf=conteudo_pdf,
            nome_arquivo=nome_arquivo,
            copias=copias,
            paginas_por_folha=paginas_por_folha,
            duplex=duplex,
            orientacao=orientacao,
            intervalo_paginas=intervalo_paginas,
            tags=tags,
            professor_id=professor_id,
            usuario=usuario,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        raise HTTPException(500, "Nao foi possivel preparar o anexo para impressao.") from exc
