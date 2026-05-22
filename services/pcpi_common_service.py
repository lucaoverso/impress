import re
import unicodedata
from datetime import datetime

TURNOS_PCPI_CONFIG = {
    "MATUTINO": {"nome": "Matutino", "aulas": 5},
    "VESPERTINO": {"nome": "Vespertino", "aulas": 6},
}

TURNOS_AGENDAMENTO_POR_TURNO_PCPI = {
    "MATUTINO": {"MATUTINO", "INTEGRAL"},
    "VESPERTINO": {"VESPERTINO", "VESPERTINO_EM", "INTEGRAL"},
}
_AULAS_INTEGRAL_POR_TURNO_PCPI = {
    "MATUTINO": set(range(1, 6)),
    "VESPERTINO": set(range(6, 9)),
}

TIPOS_ACAO_PCPI = (
    "reuniao",
    "orientacao",
    "rede_social",
    "registro",
    "impressao",
    "adequacao_impressao",
    "projeto",
    "gremio",
    "colaboracao",
    "evento",
    "planejamento",
    "formulario2",
)

GRUPO_AUTOMATICO_STE = "ste"
GRUPO_AUTOMATICO_TECNOLOGIA = "tecnologia_educacional"
GRUPO_AUTOMATICO_AUDIOVISUAL = "recurso_audiovisual"
GRUPO_AUTOMATICO_APOIO = "apoio_pedagogico"

FECHAMENTO_PCPI_PADRAO = (
    "Acompanhamento continuo das demandas do turno, com suporte pedagogico e "
    "tecnologico as acoes planejadas pela unidade escolar."
)


def _texto_limpo(valor) -> str:
    return str(valor or "").strip()


def nome_turno_pcpi(turno: str) -> str:
    turno_norm = _texto_limpo(turno).upper()
    config = TURNOS_PCPI_CONFIG.get(turno_norm)
    if not config:
        return turno_norm or "Turno nao informado"
    return str(config["nome"])


def validar_data_pcpi(valor: str, campo: str = "Data") -> str:
    texto = _texto_limpo(valor)
    if not texto:
        raise ValueError(f"{campo} invalida. Use o formato YYYY-MM-DD.")

    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{campo} invalida. Use o formato YYYY-MM-DD.") from exc
    return data.isoformat()


def validar_turno_pcpi(valor: str) -> str:
    turno = _texto_limpo(valor).upper()
    if turno not in TURNOS_PCPI_CONFIG:
        turnos_validos = ", ".join(TURNOS_PCPI_CONFIG.keys())
        raise ValueError(f"Turno invalido. Use um dos valores: {turnos_validos}.")
    return turno


def validar_texto_obrigatorio_pcpi(valor: str, campo: str, *, max_len: int = 255) -> str:
    texto = _texto_limpo(valor)
    if not texto:
        raise ValueError(f"{campo} e obrigatorio.")
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def validar_texto_opcional_pcpi(
    valor: str | None,
    campo: str = "Texto",
    *,
    max_len: int = 255,
) -> str:
    texto = _texto_limpo(valor)
    if not texto:
        return ""
    if len(texto) > max_len:
        raise ValueError(f"{campo} excede o limite de {max_len} caracteres.")
    return texto


def obter_usuario_id_pcpi(usuario: dict) -> int | None:
    try:
        valor = int((usuario or {}).get("id"))
    except (TypeError, ValueError):
        return None
    return valor if valor > 0 else None


def turno_agendamento_pertence_ao_turno_pcpi(turno_agendamento: str, turno_pcpi: str) -> bool:
    turno_pcpi_norm = _texto_limpo(turno_pcpi).upper()
    turno_agendamento_norm = _texto_limpo(turno_agendamento).upper()
    turnos_equivalentes = TURNOS_AGENDAMENTO_POR_TURNO_PCPI.get(turno_pcpi_norm, {turno_pcpi_norm})
    return turno_agendamento_norm in turnos_equivalentes


def _aula_agendamento_para_int(valor) -> int | None:
    texto = _texto_limpo(valor)
    if not texto:
        return None

    correspondencia = re.search(r"\d+", texto)
    if not correspondencia:
        return None

    numero = int(correspondencia.group())
    return numero if numero > 0 else None


def _formatar_ordinal_aula(numero: int) -> str:
    return f"{numero}\u00AA aula"


def agendamento_pertence_ao_turno_pcpi(agendamento: dict, turno_pcpi: str) -> bool:
    turno_agendamento = _texto_limpo((agendamento or {}).get("turno")).upper()
    turno_pcpi_norm = _texto_limpo(turno_pcpi).upper()
    if not turno_agendamento_pertence_ao_turno_pcpi(turno_agendamento, turno_pcpi_norm):
        return False

    if turno_agendamento != "INTEGRAL":
        return True

    aula = _aula_agendamento_para_int((agendamento or {}).get("aula"))
    if aula is None:
        return True

    aulas_permitidas = _AULAS_INTEGRAL_POR_TURNO_PCPI.get(turno_pcpi_norm)
    if not aulas_permitidas:
        return False
    return aula in aulas_permitidas


def _normalizar_texto_chave(valor: str) -> str:
    texto = _texto_limpo(valor).lower()
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_acentos.split())


def _formatar_data_br(data_iso: str) -> str:
    try:
        return datetime.strptime(str(data_iso), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(data_iso or "")


def _lista_unica_texto(valores) -> list[str]:
    itens = []
    for valor in valores or []:
        texto = _texto_limpo(valor)
        if texto and texto not in itens:
            itens.append(texto)
    return itens


def _formatar_lista_pt_br(itens: list[str]) -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) == 1:
        return valores[0]
    if len(valores) == 2:
        return f"{valores[0]} e {valores[1]}"
    return ", ".join(valores[:-1]) + f" e {valores[-1]}"


def _formatar_lista_resumida(itens: list[str], *, limite: int = 3, resumo: str = "") -> str:
    valores = _lista_unica_texto(itens)
    if not valores:
        return ""
    if len(valores) <= limite:
        return _formatar_lista_pt_br(valores)

    prefixo = valores[:limite]
    if resumo:
        prefixo.append(resumo)
    return _formatar_lista_pt_br(prefixo)


def _capitalizar_frase(frase: str) -> str:
    texto = _texto_limpo(frase)
    if not texto:
        return ""
    return texto[0].upper() + texto[1:]


def _garantir_ponto_final(frase: str) -> str:
    texto = _texto_limpo(frase)
    if not texto:
        return ""
    if texto[-1] in ".!?":
        return texto
    return texto + "."


def _coletar_descricoes_registros(registros: list[dict], *, campo: str = "descricao_curta") -> str:
    valores = _lista_unica_texto(registro.get(campo) for registro in registros)
    return _formatar_lista_resumida(valores, limite=3, resumo="outras demandas do turno")


def _coletar_observacoes_registros(registros: list[dict]) -> str:
    valores = _lista_unica_texto(registro.get("observacoes") for registro in registros)
    return _formatar_lista_resumida(valores, limite=2, resumo="outros apontamentos do turno")


def _complemento_observacoes(observacoes: str) -> str:
    texto = _texto_limpo(observacoes)
    if not texto:
        return ""
    return f", considerando {texto}"
