from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from auth import get_usuario_logado
from db.relatorios import gerar_dashboard_relatorios

from .common import usuario_tem_acesso_coordenacao, validar_data_agendamento

router = APIRouter()


def _exigir_acesso_relatorios(usuario: dict):
    if not usuario_tem_acesso_coordenacao(usuario):
        raise HTTPException(403, "Acesso negado.")
    return usuario


def _resolver_periodo(data_inicio: str | None, data_fim: str | None) -> tuple[str, str]:
    data_inicio_norm = validar_data_agendamento(data_inicio) if data_inicio else None
    data_fim_norm = validar_data_agendamento(data_fim) if data_fim else None

    if data_inicio_norm and data_fim_norm and data_inicio_norm > data_fim_norm:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    hoje = date.today()

    if data_fim_norm:
        referencia_inicio = date.fromisoformat(data_fim_norm)
    else:
        referencia_inicio = hoje

    inicio = data_inicio_norm or referencia_inicio.replace(day=1).isoformat()
    fim = data_fim_norm or hoje.isoformat()

    if inicio > fim:
        raise HTTPException(400, "Periodo invalido: data inicial maior que data final.")

    return inicio, fim


@router.get("/api/relatorios/dashboard")
def dashboard_relatorios_api(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    usuario=Depends(get_usuario_logado),
):
    _exigir_acesso_relatorios(usuario)
    inicio, fim = _resolver_periodo(data_inicio, data_fim)
    return gerar_dashboard_relatorios(inicio, fim)
