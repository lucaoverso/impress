from pathlib import Path

from fastapi import HTTPException

from modules.printing import repository
from modules.printing.policies import print_job_can_be_reused, resolve_job_pdf_path


def get_job_with_access(
    *,
    job_id: int,
    usuario: dict,
    buscar_job=None,
    usuario_pode_gerir_impressoes,
) -> dict:
    buscar_job_fn = buscar_job or repository.get_job
    job = buscar_job_fn(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")

    usuario_job_raw = job.get("usuario_id")
    usuario_job_id = int(usuario_job_raw) if usuario_job_raw is not None else None
    eh_gestor = usuario_pode_gerir_impressoes(usuario)
    eh_dono = usuario_job_id is not None and usuario_job_id == int(usuario["id"])
    if not eh_gestor and not eh_dono:
        raise HTTPException(403, "Você não pode acessar este job.")

    return job


def read_reusable_job_pdf_content(
    *,
    job_id: int,
    usuario: dict,
    spool_dir: Path,
    buscar_job=None,
    usuario_pode_gerir_impressoes,
):
    job = get_job_with_access(
        job_id=job_id,
        usuario=usuario,
        buscar_job=buscar_job,
        usuario_pode_gerir_impressoes=usuario_pode_gerir_impressoes,
    )
    if not print_job_can_be_reused(job):
        raise HTTPException(409, "Apenas jobs concluídos podem ser reutilizados no preview.")

    caminho_arquivo = resolve_job_pdf_path(job, spool_dir)
    try:
        conteudo_pdf = caminho_arquivo.read_bytes()
    except OSError as exc:
        raise HTTPException(500, "Falha ao ler o arquivo vinculado a este job.") from exc

    if not conteudo_pdf:
        raise HTTPException(404, "O arquivo deste job está vazio ou indisponível.")

    return job, caminho_arquivo, conteudo_pdf


def cancel_print_job(
    *,
    job_id: int,
    usuario: dict,
    buscar_job=None,
    usuario_pode_gerir_impressoes,
    buscar_usuario_por_id,
    usuario_tem_cota_ilimitada,
    cancelar_job=None,
    obter_cota_atual,
):
    cancelar_job_fn = cancelar_job or repository.cancel_job

    job = get_job_with_access(
        job_id=job_id,
        usuario=usuario,
        buscar_job=buscar_job,
        usuario_pode_gerir_impressoes=usuario_pode_gerir_impressoes,
    )

    usuario_job_raw = job.get("usuario_id")
    usuario_job_id = int(usuario_job_raw) if usuario_job_raw is not None else None
    usuario_job = (
        buscar_usuario_por_id(usuario_job_id, incluir_inativos=True)
        if usuario_job_id is not None
        else None
    )
    cota_ilimitada = bool(usuario_job and usuario_tem_cota_ilimitada(usuario_job))

    resultado = cancelar_job_fn(job_id, estornar_cota=not cota_ilimitada)
    if not resultado.get("cancelado"):
        raise HTTPException(
            409,
            "Este job não pode mais ser cancelado (já está em impressão ou finalizado).",
        )

    paginas_restantes = None
    if usuario_job_id is not None and not cota_ilimitada:
        cota = obter_cota_atual(usuario_job_id)
        paginas_restantes = int(cota["restante"])

    return {
        "mensagem": "Job cancelado com sucesso.",
        "paginas_estornadas": int(resultado.get("paginas_estornadas") or 0),
        "paginas_restantes": paginas_restantes,
        "cota_ilimitada": cota_ilimitada,
    }
