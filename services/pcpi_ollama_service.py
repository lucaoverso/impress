import json
import os
from urllib import error, request

PCPI_OLLAMA_BASE_URL_PADRAO = "http://127.0.0.1:11434"
PCPI_OLLAMA_MODEL_PADRAO = "qwen2.5:7b"
PCPI_OLLAMA_TIMEOUT_PADRAO = 15
PCPI_OLLAMA_TEMPERATURE = 0.2


class PcpiOllamaError(RuntimeError):
    pass


def _bool_env(nome: str, padrao: bool = False) -> bool:
    valor = str(os.getenv(nome, "") or "").strip().lower()
    if not valor:
        return padrao
    return valor in {"1", "true", "yes", "on"}


def ollama_pcpi_habilitado() -> bool:
    return _bool_env("PCPI_OLLAMA_ENABLED", False)


def _ollama_base_url() -> str:
    return str(os.getenv("PCPI_OLLAMA_BASE_URL", PCPI_OLLAMA_BASE_URL_PADRAO) or "").strip().rstrip("/")


def _ollama_generate_url() -> str:
    base_url = _ollama_base_url()
    if not base_url:
        raise PcpiOllamaError("PCPI_OLLAMA_BASE_URL nao configurada.")
    return f"{base_url}/api/generate"


def _ollama_model() -> str:
    return str(os.getenv("PCPI_OLLAMA_MODEL", PCPI_OLLAMA_MODEL_PADRAO) or "").strip()


def _ollama_timeout_seconds() -> int:
    valor = str(os.getenv("PCPI_OLLAMA_TIMEOUT_SECONDS", str(PCPI_OLLAMA_TIMEOUT_PADRAO)) or "").strip()
    try:
        timeout = int(valor)
    except ValueError:
        timeout = PCPI_OLLAMA_TIMEOUT_PADRAO
    return timeout if timeout > 0 else PCPI_OLLAMA_TIMEOUT_PADRAO


def _normalizar_texto_resposta(texto: str) -> str:
    return " ".join(str(texto or "").split()).strip()


def _montar_prompt_pcpi(contexto: dict) -> str:
    contexto_json = json.dumps(contexto, ensure_ascii=False, indent=2, sort_keys=True)

    return (
        "Você é responsável pela redação de registros administrativos do Professor Coordenador de Práticas Inovadoras (PCPI), "
        "seguindo as orientações oficiais da SED/MS para lançamento de rotina no e-SGDE.\n"
        "\n"
        "Objetivo:\n"
        "Transformar as informações do contexto em um único texto corrido, formal, coeso e adequado ao padrão institucional utilizado "
        "nos registros do PCPI.\n"
        "\n"
        "Orientações de escrita:\n"
        "- O foco do texto deve ser a ação do PCPI e não apenas a ação do professor.\n"
        "- Priorize linguagem administrativa, pedagógica e objetiva.\n"
        "- Sempre que possível, inicie períodos com substantivos de ação, como:\n"
        "  Participação, Orientação, Atendimento, Disponibilização, Acompanhamento,\n"
        "  Organização, Produção, Registro, Elaboração, Colaboração, Entrega e recebimento.\n"
        "- Atividades técnicas semelhantes devem ser agrupadas em um único trecho.\n"
        "- Valorize o caráter pedagógico das ações realizadas.\n"
        "- Quando houver uso da STE, recursos tecnológicos ou apoio a docentes, evidencie suporte técnico e pedagógico.\n"
        "- Quando houver reuniões, conselhos ou alinhamentos, destaque observação das demandas pedagógicas e organização dos encaminhamentos.\n"
        "- Quando houver impressões ou organização de materiais, relacione ao apoio às atividades pedagógicas.\n"
        "- O texto deve soar natural, institucional e pronto para uso no SGDE.\n"
        "\n"
        "Regras obrigatórias:\n"
        "- Não invente fatos.\n"
        "- Não adicionar professores, turmas, disciplinas, horários ou recursos ausentes no contexto.\n"
        "- Não criar projetos ou reuniões inexistentes.\n"
        "- Não utilizar linguagem informal.\n"
        "- Não usar caixa alta.\n"
        "- Não repetir informações desnecessariamente.\n"
        "- Preserve todos os fatos centrais presentes no contexto.\n"
        "- Caso existam múltiplas ações semelhantes, agrupe de forma coesa.\n"
        "- O resultado deve conter apenas um único parágrafo.\n"
        "- Retorne somente o texto final, sem títulos, comentários ou explicações.\n"
        "\n"
        "Exemplos esperados de construção:\n"
        "- 'Disponibilização e acompanhamento na Sala de Tecnologia Educacional (STE)...'\n"
        "- 'Entrega e recebimento de equipamentos tecnológicos...'\n"
        "- 'Produção e organização de impressões de materiais pedagógicos...'\n"
        "- 'Participação em reunião para alinhamento das demandas pedagógicas...'\n"
        "- 'Orientação ao professor quanto ao uso pedagógico de recurso tecnológico...'\n"
        "\n"
        "Contexto estruturado:\n"
        f"{contexto_json}\n"
    )


def _extrair_mensagem_http(exc: error.HTTPError) -> str:
    try:
        corpo = exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        corpo = ""
    if corpo:
        return corpo
    return f"HTTP {exc.code}"


def gerar_texto_pcpi_ollama(contexto: dict) -> str:
    modelo = _ollama_model()
    if not modelo:
        raise PcpiOllamaError("PCPI_OLLAMA_MODEL nao configurado.")

    payload = {
        "model": modelo,
        "prompt": _montar_prompt_pcpi(contexto),
        "stream": False,
        "options": {"temperature": PCPI_OLLAMA_TEMPERATURE},
    }

    requisicao = request.Request(
        _ollama_generate_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(requisicao, timeout=_ollama_timeout_seconds()) as resposta:
            corpo = resposta.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        raise PcpiOllamaError(f"Erro ao consultar o Ollama: {_extrair_mensagem_http(exc)}") from exc
    except error.URLError as exc:
        raise PcpiOllamaError(f"Nao foi possivel conectar ao Ollama: {exc.reason}") from exc
    except TimeoutError as exc:
        raise PcpiOllamaError("Timeout ao aguardar resposta do Ollama.") from exc
    except OSError as exc:
        raise PcpiOllamaError(f"Falha ao consultar o Ollama: {exc}") from exc

    try:
        dados = json.loads(corpo)
    except json.JSONDecodeError as exc:
        raise PcpiOllamaError("Ollama retornou uma resposta JSON invalida.") from exc

    texto = _normalizar_texto_resposta(dados.get("response"))
    if not texto:
        raise PcpiOllamaError("Ollama retornou texto vazio para o PCPI.")
    return texto
