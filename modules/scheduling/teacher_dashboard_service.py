from datetime import date, datetime, time, timedelta

from modules.scheduling.school_schedule_data_service import (
    listar_configuracoes_aulas,
    listar_horarios_escolares,
)
from modules.scheduling.school_schedule_service import ordenar_horarios_escolares


DIAS_SEMANA = (
    "SEGUNDA",
    "TERCA",
    "QUARTA",
    "QUINTA",
    "SEXTA",
    "SABADO",
    "DOMINGO",
)
ROTULOS_DIA = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)


def _horario(data_aula: date, valor: str) -> datetime | None:
    try:
        hora = time.fromisoformat(str(valor or "").strip())
    except ValueError:
        return None
    return datetime.combine(data_aula, hora)


def _rotulo_data(data_aula: date, hoje: date) -> str:
    if data_aula == hoje:
        return "Hoje"
    if data_aula == hoje + timedelta(days=1):
        return "Amanhã"
    return f"{ROTULOS_DIA[data_aula.weekday()]}, {data_aula.strftime('%d/%m')}"


def selecionar_proximas_aulas(
    itens: list[dict],
    *,
    agora: datetime,
    limite: int = 3,
) -> list[dict]:
    proximas = []
    limite_valor = max(int(limite or 0), 1)

    for deslocamento in range(8):
        data_aula = agora.date() + timedelta(days=deslocamento)
        dia_semana = DIAS_SEMANA[data_aula.weekday()]

        for item in itens or []:
            if str(item.get("dia_semana") or "").upper() != dia_semana:
                continue

            inicio = _horario(data_aula, item.get("horario_inicio", ""))
            fim = _horario(data_aula, item.get("horario_fim", ""))
            if deslocamento == 0 and fim and fim <= agora:
                continue

            aula_numero = int(item.get("aula_numero") or 0)
            proximas.append(
                {
                    "id": int(item.get("id") or 0),
                    "data": data_aula.isoformat(),
                    "data_rotulo": _rotulo_data(data_aula, agora.date()),
                    "horario_inicio": str(item.get("horario_inicio") or "").strip(),
                    "horario_fim": str(item.get("horario_fim") or "").strip(),
                    "aula_numero": aula_numero,
                    "turma_nome": str(item.get("turma_nome") or "").strip(),
                    "disciplina_nome": str(item.get("disciplina_nome") or "").strip(),
                    "turno_nome": str(item.get("turno_nome") or "").strip(),
                    "em_andamento": bool(inicio and fim and inicio <= agora < fim),
                    "_ordem": inicio or datetime.combine(
                        data_aula,
                        time.min,
                    ) + timedelta(minutes=aula_numero),
                }
            )

    proximas.sort(key=lambda item: (item["_ordem"], item["aula_numero"], item["id"]))
    return [
        {chave: valor for chave, valor in item.items() if chave != "_ordem"}
        for item in proximas[:limite_valor]
    ]


def listar_proximas_aulas_professor(
    professor_id: int,
    *,
    agora: datetime | None = None,
    limite: int = 3,
) -> dict:
    referencia = agora or datetime.now()
    configuracoes = listar_configuracoes_aulas(incluir_inativas=False)
    itens = ordenar_horarios_escolares(
        listar_horarios_escolares(
            ano_letivo=referencia.year,
            professor_id=int(professor_id),
        ),
        configuracoes_aulas=configuracoes,
    )
    aulas = selecionar_proximas_aulas(itens, agora=referencia, limite=limite)
    return {
        "aulas": aulas,
        "total": len(aulas),
        "periodo_rotulo": aulas[0]["data_rotulo"] if aulas else "Próximos 7 dias",
    }
