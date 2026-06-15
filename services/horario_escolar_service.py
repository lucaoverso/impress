from collections import Counter
from datetime import datetime

from modules.scheduling.config import TURNOS_CONFIG
from modules.scheduling.lesson_config import (
    build_lesson_display_label,
    find_lesson_by_number,
    list_lessons_for_class,
    list_visual_schedule_items_for_class,
    total_configured_lessons,
)

DIAS_SEMANA_HORARIO = (
    {"valor": "SEGUNDA", "label": "Segunda-feira"},
    {"valor": "TERCA", "label": "Terca-feira"},
    {"valor": "QUARTA", "label": "Quarta-feira"},
    {"valor": "QUINTA", "label": "Quinta-feira"},
    {"valor": "SEXTA", "label": "Sexta-feira"},
)
_DIAS_SEMANA_POR_WEEKDAY = (
    "SEGUNDA",
    "TERCA",
    "QUARTA",
    "QUINTA",
    "SEXTA",
    "SABADO",
    "DOMINGO",
)
_ALIASES_DIA_SEMANA = {
    "SEG": "SEGUNDA",
    "SEGUNDA": "SEGUNDA",
    "SEGUNDA-FEIRA": "SEGUNDA",
    "TER": "TERCA",
    "TERCA": "TERCA",
    "TERCA-FEIRA": "TERCA",
    "TERÇA": "TERCA",
    "TERÇA-FEIRA": "TERCA",
    "QUA": "QUARTA",
    "QUARTA": "QUARTA",
    "QUARTA-FEIRA": "QUARTA",
    "QUI": "QUINTA",
    "QUINTA": "QUINTA",
    "QUINTA-FEIRA": "QUINTA",
    "SEX": "SEXTA",
    "SEXTA": "SEXTA",
    "SEXTA-FEIRA": "SEXTA",
}
DIA_SEMANA_LABELS = {item["valor"]: item["label"] for item in DIAS_SEMANA_HORARIO}
DIA_SEMANA_ORDEM = {
    item["valor"]: indice for indice, item in enumerate(DIAS_SEMANA_HORARIO, start=1)
}
FAIXA_GLOBAL_OFFSET_POR_TURNO_LEGADO = {
    "MATUTINO": 0,
    "INTEGRAL": 0,
    "VESPERTINO": 5,
    "VESPERTINO_EM": 5,
}


def listar_dias_semana_horario() -> list[dict]:
    return [dict(item) for item in DIAS_SEMANA_HORARIO]


def normalizar_dia_semana(valor: str) -> str:
    chave = str(valor or "").strip().upper()
    normalizado = _ALIASES_DIA_SEMANA.get(chave)
    if not normalizado:
        raise ValueError("Dia da semana inválido.")
    return normalizado


def nome_dia_semana(valor: str) -> str:
    try:
        chave = normalizar_dia_semana(valor)
    except ValueError:
        return str(valor or "").strip()
    return DIA_SEMANA_LABELS.get(chave, chave.title())


def validar_ano_letivo(valor: int) -> int:
    try:
        ano = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ano letivo inválido.") from exc
    if ano < 2000 or ano > 2100:
        raise ValueError("Ano letivo inválido.")
    return ano


def validar_aula_numero(
    valor: int,
    turma: dict | None = None,
    *,
    configuracoes_aulas: list[dict] | None = None,
) -> int:
    try:
        aula = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError("Aula inválida.") from exc
    if aula <= 0:
        raise ValueError("Aula inválida.")

    if turma:
        aulas_turma = list_lessons_for_class(turma, configuracoes_aulas or [])
        if not aulas_turma:
            raise ValueError("A turma não possui aulas globais configuradas.")
        aulas_permitidas = {int(item.get("aula_numero") or 0) for item in aulas_turma}
        if aula not in aulas_permitidas:
            primeira_aula = min(aulas_permitidas)
            ultima_aula = max(aulas_permitidas)
            raise ValueError(
                "A aula informada está fora da janela configurada para a turma "
                f"({primeira_aula} a {ultima_aula})."
            )
        return aula

    total_aulas = total_configured_lessons(configuracoes_aulas or [])
    if total_aulas and aula > total_aulas:
        raise ValueError(
            f"A aula informada excede o total de aulas globais configuradas ({total_aulas})."
        )
    if aula > 20:
        raise ValueError("Aula inválida.")
    return aula


def total_aulas_por_turno(turno: str) -> int:
    turno_norm = str(turno or "").strip().upper()
    return int((TURNOS_CONFIG.get(turno_norm) or {}).get("aulas") or 0)


def nome_turno_horario(turno: str) -> str:
    turno_norm = str(turno or "").strip().upper()
    return str((TURNOS_CONFIG.get(turno_norm) or {}).get("nome") or turno or "").strip()


def faixa_global_por_turno_e_aula(turno: str, aula_numero: int) -> int:
    turno_norm = str(turno or "").strip().upper()
    aula = validar_aula_numero(aula_numero)
    faixa = aula + int(FAIXA_GLOBAL_OFFSET_POR_TURNO_LEGADO.get(turno_norm) or 0)
    if turno_norm == "INTEGRAL" and aula > 5:
        faixa += 1
    return faixa


def aula_label_com_faixa(
    turno: str,
    aula_numero: int,
    configuracoes_aulas: list[dict] | None = None,
) -> str:
    configuracoes = configuracoes_aulas or []
    aula_config = find_lesson_by_number(configuracoes, int(aula_numero or 0))
    if aula_config:
        return str(aula_config.get("label") or "")
    faixa = faixa_global_por_turno_e_aula(turno, aula_numero)
    return f"{int(aula_numero)}a aula (faixa {faixa})"


def listar_faixas_turno_horario(turno: str) -> list[dict]:
    total = total_aulas_por_turno(turno)
    itens = []
    for aula_numero in range(1, total + 1):
        faixa_global = faixa_global_por_turno_e_aula(turno, aula_numero)
        itens.append(
            {
                "aula_numero": aula_numero,
                "faixa_global": faixa_global,
                "label": aula_label_com_faixa(turno, aula_numero),
                "label_curta": f"{aula_numero}a aula",
            }
        )
    return itens


def listar_grade_turma_horario(turma: dict, configuracoes_aulas: list[dict]) -> list[dict]:
    return list_visual_schedule_items_for_class(turma, configuracoes_aulas or [])


def listar_aulas_turma_horario(turma: dict, configuracoes_aulas: list[dict]) -> list[dict]:
    return list_lessons_for_class(turma, configuracoes_aulas or [])


def total_aulas_turma_horario(turma: dict, configuracoes_aulas: list[dict]) -> int:
    return len(listar_aulas_turma_horario(turma, configuracoes_aulas))


def enriquecer_horario_escolar(
    item: dict,
    configuracoes_aulas: list[dict] | None = None,
) -> dict:
    turno = str((item or {}).get("turno") or "").strip().upper()
    aula_numero = int((item or {}).get("aula_numero") or 0)
    faixa_armazenada = int((item or {}).get("faixa_global") or 0)
    configuracoes = configuracoes_aulas or []
    aula_config = find_lesson_by_number(configuracoes, aula_numero)
    if aula_config:
        faixa_global = aula_numero
    elif faixa_armazenada > 0:
        faixa_global = faixa_armazenada
    else:
        faixa_global = faixa_global_por_turno_e_aula(turno, aula_numero) if aula_numero > 0 else 0
    return {
        **dict(item or {}),
        "dia_semana": normalizar_dia_semana((item or {}).get("dia_semana")),
        "dia_semana_nome": nome_dia_semana((item or {}).get("dia_semana")),
        "aula_numero": aula_numero,
        "ano_letivo": int((item or {}).get("ano_letivo") or 0),
        "turma_id": int((item or {}).get("turma_id") or 0),
        "disciplina_id": int((item or {}).get("disciplina_id") or 0),
        "professor_id": int((item or {}).get("professor_id") or 0),
        "turno": turno,
        "turno_nome": nome_turno_horario(turno),
        "faixa_global": faixa_global,
        "aula_label": (
            str(aula_config.get("label") or "")
            if aula_config
            else aula_label_com_faixa(turno, aula_numero, configuracoes)
        )
        if faixa_global > 0
        else "",
        "horario_inicio": str((aula_config or {}).get("horario_inicio") or "").strip(),
        "horario_fim": str((aula_config or {}).get("horario_fim") or "").strip(),
    }


def ordenar_horarios_escolares(
    itens: list[dict],
    configuracoes_aulas: list[dict] | None = None,
) -> list[dict]:
    enriquecidos = [
        enriquecer_horario_escolar(item, configuracoes_aulas=configuracoes_aulas)
        for item in (itens or [])
    ]
    return sorted(
        enriquecidos,
        key=lambda item: (
            -int(item.get("ano_letivo") or 0),
            str(item.get("turma_nome") or "").casefold(),
            DIA_SEMANA_ORDEM.get(str(item.get("dia_semana") or "").upper(), 999),
            int(item.get("faixa_global") or 0) or int(item.get("aula_numero") or 0),
            str(item.get("disciplina_nome") or "").casefold(),
            str(item.get("professor_nome") or "").casefold(),
            int(item.get("id") or 0),
        ),
    )


def agrupar_horarios_por_turma(itens: list[dict]) -> list[dict]:
    grupos: dict[tuple[int, int], dict] = {}
    for item in ordenar_horarios_escolares(itens):
        chave = (int(item.get("ano_letivo") or 0), int(item.get("turma_id") or 0))
        grupo = grupos.setdefault(
            chave,
            {
                "ano_letivo": int(item.get("ano_letivo") or 0),
                "turma_id": int(item.get("turma_id") or 0),
                "turma_nome": str(item.get("turma_nome") or "").strip(),
                "turno": str(item.get("turno") or "").strip(),
                "itens": [],
            },
        )
        grupo["itens"].append(item)
    return list(grupos.values())


def agrupar_horarios_por_professor(itens: list[dict]) -> list[dict]:
    grupos: dict[tuple[int, int], dict] = {}
    for item in ordenar_horarios_escolares(itens):
        chave = (int(item.get("ano_letivo") or 0), int(item.get("professor_id") or 0))
        grupo = grupos.setdefault(
            chave,
            {
                "ano_letivo": int(item.get("ano_letivo") or 0),
                "professor_id": int(item.get("professor_id") or 0),
                "professor_nome": str(item.get("professor_nome") or "").strip(),
                "professor_email": str(item.get("professor_email") or "").strip(),
                "itens": [],
            },
        )
        grupo["itens"].append(item)
    return list(grupos.values())


def dia_semana_por_data(data_iso: str) -> str:
    try:
        data = datetime.strptime(str(data_iso or "").strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Data inválida. Use o formato YYYY-MM-DD.") from exc
    return _DIAS_SEMANA_POR_WEEKDAY[data.weekday()]


def anos_letivos_sugeridos(anos_existentes: list[int] | None = None) -> list[int]:
    ano_atual = datetime.now().year
    anos = {ano_atual - 1, ano_atual, ano_atual + 1}
    for valor in anos_existentes or []:
        try:
            anos.add(int(valor))
        except (TypeError, ValueError):
            continue
    return sorted(anos)


def montar_cards_disponiveis_turma(
    turma_disciplinas: list[dict],
    registros: list[dict],
) -> tuple[list[dict], list[dict], list[str]]:
    contagem_alocada = Counter(
        (
            int(item.get("disciplina_id") or 0),
            int(item.get("professor_id") or 0),
        )
        for item in (registros or [])
        if int(item.get("disciplina_id") or 0) > 0 and int(item.get("professor_id") or 0) > 0
    )

    cards_disponiveis = []
    cards_resumo = []
    alertas = []

    itens_ordenados = sorted(
        [
            dict(item)
            for item in (turma_disciplinas or [])
            if int(item.get("professor_id") or 0) > 0 and int(item.get("carga_horaria") or 0) > 0
        ],
        key=lambda item: (
            str(item.get("disciplina_nome") or "").casefold(),
            str(item.get("professor_nome") or "").casefold(),
            int(item.get("id") or 0),
        ),
    )

    for item in itens_ordenados:
        disciplina_id = int(item.get("disciplina_id") or 0)
        professor_id = int(item.get("professor_id") or 0)
        total = max(int(item.get("carga_horaria") or 0), 0)
        alocados = int(contagem_alocada.get((disciplina_id, professor_id), 0))
        disponiveis = max(total - alocados, 0)
        excedentes = max(alocados - total, 0)

        resumo = {
            "turma_disciplina_id": int(item.get("id") or 0),
            "turma_id": int(item.get("turma_id") or 0),
            "disciplina_id": disciplina_id,
            "disciplina_nome": str(item.get("disciplina_nome") or "").strip(),
            "professor_id": professor_id,
            "professor_nome": str(item.get("professor_nome") or "").strip(),
            "professor_email": str(item.get("professor_email") or "").strip(),
            "quantidade_total": total,
            "quantidade_alocada": alocados,
            "quantidade_disponivel": disponiveis,
        }
        cards_resumo.append(resumo)

        if excedentes > 0:
            alertas.append(
                f"{resumo['disciplina_nome']} com {resumo['professor_nome']} excede a carga prevista em {excedentes} aula(s)."
            )

        for indice in range(1, disponiveis + 1):
            cards_disponiveis.append(
                {
                    **resumo,
                    "card_id": f"td-{resumo['turma_disciplina_id']}-disp-{indice}",
                    "indice_disponivel": indice,
                }
            )

    return cards_disponiveis, cards_resumo, alertas
