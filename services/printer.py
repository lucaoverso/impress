import json
import os
import re
import shlex
import subprocess
from pathlib import Path

from services.pdf_service import gerar_pdf_duas_por_folha_paisagem

LP_COMMAND = os.getenv("CUPS_LP_COMMAND", "lp")
LP_TIMEOUT_SECONDS = int(os.getenv("CUPS_LP_TIMEOUT_SECONDS", "30"))
DEFAULT_PRINTER_NAME = os.getenv("CUPS_PRINTER", "").strip()

REQUEST_ID_REGEX = re.compile(r"request id is\s+([^\s]+)-(\d+)", re.IGNORECASE)
GENERIC_JOB_ID_REGEX = re.compile(r"([A-Za-z0-9_.-]+)-(\d+)")

def _montar_opcoes_cups_legado(job):
    paginas_por_folha = int(job.get("paginas_por_folha") or 1)
    orientacao = str(job.get("orientacao") or "retrato").strip().lower()
    duplex = bool(job.get("duplex"))
    intervalo_paginas = str(job.get("intervalo_paginas") or "").strip()

    if duplex:
        sides = "two-sided-short-edge" if orientacao == "paisagem" else "two-sided-long-edge"
    else:
        sides = "one-sided"

    orientacao_cups = 4 if orientacao == "paisagem" else 3

    opcoes = {
        "number-up": paginas_por_folha,
        "sides": sides,
        "orientation-requested": orientacao_cups,
    }

    if orientacao == "paisagem":
        opcoes["landscape"] = True

    if paginas_por_folha == 2:
        opcoes["number-up-layout"] = "lrtb"

    if intervalo_paginas:
        opcoes["page-ranges"] = intervalo_paginas

    return opcoes

def _carregar_opcoes_cups(job):
    payload = job.get("cups_options")
    if not payload:
        return _montar_opcoes_cups_legado(job)

    try:
        opcoes = json.loads(payload)
        if not isinstance(opcoes, dict):
            raise ValueError("Estrutura inválida para cups_options")
        return opcoes
    except Exception:
        return _montar_opcoes_cups_legado(job)

def _extrair_cups_job_id(lp_output: str):
    if not lp_output:
        return None

    match = REQUEST_ID_REGEX.search(lp_output)
    if match:
        return int(match.group(2))

    match = GENERIC_JOB_ID_REGEX.search(lp_output)
    if match:
        try:
            return int(match.group(2))
        except ValueError:
            return None

    return None

def _normalizar_int(valor, padrao: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao

def _forcar_layout_duas_por_folha(caminho: Path, job, opcoes_cups):
    paginas_por_folha = _normalizar_int(
        opcoes_cups.get("number-up", job.get("paginas_por_folha")),
        1
    )
    if paginas_por_folha != 2:
        return caminho, opcoes_cups, None

    intervalo_paginas = str(
        job.get("intervalo_paginas")
        or opcoes_cups.get("page-ranges")
        or ""
    ).strip()
    caminho_layout = gerar_pdf_duas_por_folha_paisagem(caminho, intervalo_paginas)

    opcoes_ajustadas = dict(opcoes_cups)
    opcoes_ajustadas["number-up"] = 1
    opcoes_ajustadas.pop("number-up-layout", None)
    opcoes_ajustadas.pop("orientation-requested", None)
    opcoes_ajustadas.pop("landscape", None)
    opcoes_ajustadas.pop("page-ranges", None)

    return caminho_layout, opcoes_ajustadas, caminho_layout

def imprimir_job(job):
    arquivo_path = job.get("arquivo_path")
    if not arquivo_path:
        raise RuntimeError(f"Job {job['id']} sem arquivo_path para impressão.")

    caminho = Path(arquivo_path)
    if not caminho.exists():
        raise RuntimeError(f"Arquivo do job não encontrado: {arquivo_path}")

    opcoes_cups = _carregar_opcoes_cups(job)
    impressora = (job.get("printer_name") or DEFAULT_PRINTER_NAME or "").strip()
    caminho_envio = caminho
    arquivo_temporario = None

    try:
        caminho_envio, opcoes_cups, arquivo_temporario = _forcar_layout_duas_por_folha(
            caminho,
            job,
            opcoes_cups
        )

        cmd = [LP_COMMAND]
        if impressora:
            cmd.extend(["-d", impressora])

        cmd.extend(["-n", str(job.get("copias") or 1)])
        cmd.extend(["-t", str(job.get("arquivo") or caminho.name)])

        for chave in sorted(opcoes_cups.keys()):
            valor = opcoes_cups[chave]
            if valor is None or valor == "" or valor is False:
                continue

            if valor is True:
                cmd.extend(["-o", str(chave)])
                continue

            cmd.extend(["-o", f"{chave}={valor}"])

        cmd.append(str(caminho_envio))
        print(f"🖨️ Enviando para CUPS: {shlex.join(cmd)}")

        try:
            resultado = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=LP_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Comando 'lp' não encontrado. Instale e configure o CUPS no servidor.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Timeout ao enviar job para o CUPS.") from exc

        output = "\n".join(
            [parte for parte in [resultado.stdout.strip(), resultado.stderr.strip()] if parte]
        ).strip()

        if resultado.returncode != 0:
            raise RuntimeError(output or f"Falha ao enviar job para CUPS (exit {resultado.returncode})")

        cups_job_id = _extrair_cups_job_id(output)
        print(f"✅ Job aceito pelo CUPS: {output or 'sem saída'}")
        return {
            "cups_job_id": cups_job_id,
            "printer_name": impressora or None,
            "cups_output": output,
        }
    finally:
        if arquivo_temporario:
            try:
                arquivo_temporario.unlink()
            except OSError:
                pass
