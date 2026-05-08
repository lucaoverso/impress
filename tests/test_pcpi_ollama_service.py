import json
import os
import unittest
from unittest.mock import patch
from urllib import request as urllib_request

from services.pcpi_ollama_service import (
    PCPI_OLLAMA_KEEP_ALIVE_PADRAO,
    PCPI_OLLAMA_TEMPERATURE,
    PcpiOllamaError,
    gerar_texto_pcpi_ollama,
    ollama_pcpi_habilitado,
)


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PcpiOllamaServiceTest(unittest.TestCase):
    def setUp(self):
        self._old_enabled = os.environ.get("PCPI_OLLAMA_ENABLED")
        self._old_base_url = os.environ.get("PCPI_OLLAMA_BASE_URL")
        self._old_model = os.environ.get("PCPI_OLLAMA_MODEL")
        self._old_timeout = os.environ.get("PCPI_OLLAMA_TIMEOUT_SECONDS")
        self._old_keep_alive = os.environ.get("PCPI_OLLAMA_KEEP_ALIVE")

    def tearDown(self):
        self._restaurar_env("PCPI_OLLAMA_ENABLED", self._old_enabled)
        self._restaurar_env("PCPI_OLLAMA_BASE_URL", self._old_base_url)
        self._restaurar_env("PCPI_OLLAMA_MODEL", self._old_model)
        self._restaurar_env("PCPI_OLLAMA_TIMEOUT_SECONDS", self._old_timeout)
        self._restaurar_env("PCPI_OLLAMA_KEEP_ALIVE", self._old_keep_alive)

    def _restaurar_env(self, nome: str, valor_antigo: str | None):
        if valor_antigo is None:
            os.environ.pop(nome, None)
        else:
            os.environ[nome] = valor_antigo

    def test_ollama_habilitado_respeita_variavel_de_ambiente(self):
        os.environ["PCPI_OLLAMA_ENABLED"] = "true"
        self.assertTrue(ollama_pcpi_habilitado())

        os.environ["PCPI_OLLAMA_ENABLED"] = "false"
        self.assertFalse(ollama_pcpi_habilitado())

    def test_gerar_texto_pcpi_ollama_envia_prompt_com_temperatura_fixa(self):
        os.environ["PCPI_OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
        os.environ["PCPI_OLLAMA_MODEL"] = "qwen2.5:7b"
        os.environ["PCPI_OLLAMA_KEEP_ALIVE"] = "45m"

        contexto = {"texto_base": "Texto base do PCPI.", "turno": "MATUTINO"}

        with patch(
            "services.pcpi_ollama_service.request.urlopen",
            return_value=_FakeHttpResponse({"response": "Texto final do Ollama."}),
        ) as urlopen:
            texto = gerar_texto_pcpi_ollama(contexto)

        requisicao = urlopen.call_args.args[0]
        payload = json.loads(requisicao.data.decode("utf-8"))

        self.assertEqual(texto, "Texto final do Ollama.")
        self.assertEqual(payload["model"], "qwen2.5:7b")
        self.assertEqual(payload["options"]["temperature"], PCPI_OLLAMA_TEMPERATURE)
        self.assertEqual(payload["keep_alive"], "45m")
        self.assertFalse(payload["stream"])

    def test_gerar_texto_pcpi_ollama_usa_keep_alive_padrao(self):
        os.environ["PCPI_OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
        os.environ["PCPI_OLLAMA_MODEL"] = "qwen2.5:7b"
        os.environ.pop("PCPI_OLLAMA_KEEP_ALIVE", None)

        with patch(
            "services.pcpi_ollama_service.request.urlopen",
            return_value=_FakeHttpResponse({"response": "Texto final do Ollama."}),
        ) as urlopen:
            gerar_texto_pcpi_ollama({"texto_base": "Texto base do PCPI."})

        requisicao = urlopen.call_args.args[0]
        payload = json.loads(requisicao.data.decode("utf-8"))
        self.assertEqual(payload["keep_alive"], PCPI_OLLAMA_KEEP_ALIVE_PADRAO)

    def test_gerar_texto_pcpi_ollama_falha_com_resposta_vazia(self):
        os.environ["PCPI_OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
        os.environ["PCPI_OLLAMA_MODEL"] = "qwen2.5:7b"

        with patch(
            "services.pcpi_ollama_service.request.urlopen",
            return_value=_FakeHttpResponse({"response": ""}),
        ):
            with self.assertRaises(PcpiOllamaError):
                gerar_texto_pcpi_ollama({"texto_base": "Texto base."})

    def test_gerar_texto_pcpi_ollama_consulta_endpoint_real_quando_integracao_habilitada(self):
        if os.environ.get("PCPI_OLLAMA_INTEGRATION_TEST") != "true":
            self.skipTest("Defina PCPI_OLLAMA_INTEGRATION_TEST=true para executar contra o Ollama real.")

        os.environ.setdefault("PCPI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        os.environ.setdefault("PCPI_OLLAMA_MODEL", "qwen2.5:7b")

        contexto = {
            "texto_base": "Atendimento ao professor para organizacao de material pedagogico.",
            "turno": "MATUTINO",
            "frases_automaticas": [
                "Disponibilizacao e acompanhamento na Sala de Tecnologia Educacional.",
            ],
            "frases_manuais": [
                "Registro de orientacao pedagogica ao docente.",
            ],
        }

        with patch(
            "services.pcpi_ollama_service.request.urlopen",
            wraps=urllib_request.urlopen,
        ) as urlopen_real:
            texto = gerar_texto_pcpi_ollama(contexto)

        requisicao = urlopen_real.call_args.args[0]
        payload = json.loads(requisicao.data.decode("utf-8"))

        self.assertTrue(texto.strip())
        self.assertTrue(requisicao.full_url.endswith("/api/generate"))
        self.assertEqual(payload["model"], os.environ["PCPI_OLLAMA_MODEL"])
        self.assertEqual(payload["options"]["temperature"], PCPI_OLLAMA_TEMPERATURE)
        self.assertFalse(payload["stream"])


if __name__ == "__main__":
    unittest.main()
