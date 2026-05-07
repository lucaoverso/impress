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
        "Voce redige registros administrativos do PCPI.\n"
        "\n"
        "Tarefa:\n"
        "Reescreva o conteudo em um unico paragrafo, com linguagem formal, coerente e sucinta.\n"
        "\n"
        "Regras obrigatorias:\n"
        "- Nao invente fatos.\n"
        "- Nao adicione nomes, turmas, recursos ou acoes ausentes no contexto.\n"
        "- Elimine repeticoes.\n"
        "- Preserve os fatos centrais do texto base.\n"
        "- Mantenha tom administrativo.\n"
        "- Retorne somente o texto final.\n"
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
