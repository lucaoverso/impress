import json
import os
from urllib import error, request

PCPI_OLLAMA_BASE_URL_PADRAO = "http://127.0.0.1:11434"
PCPI_OLLAMA_MODEL_PADRAO = "qwen2.5:7b"
PCPI_OLLAMA_TIMEOUT_PADRAO = 15
PCPI_OLLAMA_KEEP_ALIVE_PADRAO = "30m"
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
    return str(
        os.getenv("PCPI_OLLAMA_BASE_URL", PCPI_OLLAMA_BASE_URL_PADRAO) or ""
    ).strip().rstrip("/")


def _ollama_generate_url() -> str:
    base_url = _ollama_base_url()
    if not base_url:
        raise PcpiOllamaError("PCPI_OLLAMA_BASE_URL nao configurada.")
    return f"{base_url}/api/generate"


def _ollama_model() -> str:
    return str(os.getenv("PCPI_OLLAMA_MODEL", PCPI_OLLAMA_MODEL_PADRAO) or "").strip()


def _ollama_timeout_seconds() -> int:
    valor = str(
        os.getenv("PCPI_OLLAMA_TIMEOUT_SECONDS", str(PCPI_OLLAMA_TIMEOUT_PADRAO)) or ""
    ).strip()
    try:
        timeout = int(valor)
    except ValueError:
        timeout = PCPI_OLLAMA_TIMEOUT_PADRAO
    return timeout if timeout > 0 else PCPI_OLLAMA_TIMEOUT_PADRAO


def _ollama_keep_alive() -> str:
    valor = str(
        os.getenv("PCPI_OLLAMA_KEEP_ALIVE", PCPI_OLLAMA_KEEP_ALIVE_PADRAO) or ""
    ).strip()
    return valor or PCPI_OLLAMA_KEEP_ALIVE_PADRAO


def _normalizar_texto_resposta(texto: str) -> str:
    return " ".join(str(texto or "").split()).strip()


def _montar_prompt_pcpi(contexto: dict) -> str:
    contexto_json = json.dumps(
        contexto,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        "Reescreva o registro do PCPI em um unico paragrafo, com linguagem formal, "
        "objetiva e institucional.\n"
        "Foque na acao do PCPI, preserve os fatos centrais e agrupe atividades semelhantes.\n"
        "Nao invente informacoes e nao adicione professores, turmas, recursos ou acoes "
        "ausentes no contexto.\n"
        "Retorne somente o texto final.\n"
        f"Contexto:{contexto_json}"
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
        "keep_alive": _ollama_keep_alive(),
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
