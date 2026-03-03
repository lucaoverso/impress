import re
import uuid
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation

A4_RETRATO_LARGURA_PT = 595.28
A4_RETRATO_ALTURA_PT = 841.89
A4_PAISAGEM_LARGURA_PT = 841.89
A4_PAISAGEM_ALTURA_PT = 595.28


def contar_paginas_pdf(caminho_arquivo: str) -> int:
    reader = PdfReader(caminho_arquivo)
    return len(reader.pages)


def _listar_paginas_intervalo(intervalo: str, total_paginas: int) -> list[int]:
    if total_paginas <= 0:
        return []

    if not intervalo or not intervalo.strip():
        return list(range(1, total_paginas + 1))

    paginas = set()
    partes = [p.strip() for p in str(intervalo).split(",") if p.strip()]
    for parte in partes:
        if "-" in parte:
            pedacos = [x.strip() for x in parte.split("-", 1)]
            if len(pedacos) != 2 or not pedacos[0] or not pedacos[1]:
                raise ValueError(f"Intervalo de páginas inválido: {parte}")

            inicio_txt, fim_txt = pedacos
            if not re.fullmatch(r"\d+", inicio_txt) or not re.fullmatch(r"\d+", fim_txt):
                raise ValueError(f"Intervalo de páginas inválido: {parte}")

            inicio = int(inicio_txt)
            fim = int(fim_txt)
            if inicio <= 0 or fim <= 0 or inicio > fim:
                raise ValueError(f"Intervalo de páginas inválido: {parte}")
            if fim > total_paginas:
                raise ValueError(f"Página {fim} não existe no documento.")

            paginas.update(range(inicio, fim + 1))
            continue

        if not re.fullmatch(r"\d+", parte):
            raise ValueError(f"Página inválida: {parte}")

        pagina = int(parte)
        if pagina <= 0 or pagina > total_paginas:
            raise ValueError(f"Página {pagina} não existe no documento.")
        paginas.add(pagina)

    return sorted(paginas)


def _medidas_pagina(page) -> tuple[float, float]:
    largura = float(page.cropbox.width)
    altura = float(page.cropbox.height)
    if largura <= 0 or altura <= 0:
        largura = float(page.mediabox.width)
        altura = float(page.mediabox.height)
    return largura, altura


def _normalizar_orientacao(orientacao: str) -> str:
    orientacao_norm = str(orientacao or "").strip().lower()
    return "paisagem" if orientacao_norm == "paisagem" else "retrato"


def _obter_tamanho_folha(orientacao: str) -> tuple[float, float]:
    if orientacao == "paisagem":
        return A4_PAISAGEM_LARGURA_PT, A4_PAISAGEM_ALTURA_PT
    return A4_RETRATO_LARGURA_PT, A4_RETRATO_ALTURA_PT


def _obter_layout_nup(paginas_por_folha: int) -> tuple[int, int]:
    if paginas_por_folha == 1:
        return 1, 1
    if paginas_por_folha == 2:
        return 2, 1
    if paginas_por_folha == 4:
        return 2, 2
    raise ValueError(f"Paginação por folha não suportada: {paginas_por_folha}")


def gerar_pdf_n_por_folha(
    caminho_origem: Path,
    paginas_por_folha: int,
    intervalo_paginas: str = "",
    orientacao: str = "retrato"
) -> Path:
    if paginas_por_folha not in (1, 2, 4):
        raise ValueError("Paginação por folha inválida para geração de layout.")

    reader = PdfReader(str(caminho_origem))
    total_paginas = len(reader.pages)
    paginas_selecionadas = _listar_paginas_intervalo(intervalo_paginas, total_paginas)
    if not paginas_selecionadas:
        raise ValueError("Nenhuma página disponível para geração do layout.")

    # Se o documento possui uma única página selecionada e o usuário pede N-up,
    # replica essa página para preencher toda a folha.
    if len(paginas_selecionadas) == 1 and paginas_por_folha in (2, 4):
        paginas_selecionadas = paginas_selecionadas * paginas_por_folha

    orientacao_norm = _normalizar_orientacao(orientacao)
    if paginas_por_folha == 2:
        orientacao_norm = "paisagem"

    writer = PdfWriter()
    largura_folha, altura_folha = _obter_tamanho_folha(orientacao_norm)
    colunas, linhas = _obter_layout_nup(paginas_por_folha)
    largura_celula = largura_folha / colunas
    altura_celula = altura_folha / linhas

    for inicio in range(0, len(paginas_selecionadas), paginas_por_folha):
        numeros_da_folha = paginas_selecionadas[inicio:inicio + paginas_por_folha]
        folha = writer.add_blank_page(width=largura_folha, height=altura_folha)

        for indice_slot, numero_pagina in enumerate(numeros_da_folha):
            coluna = indice_slot % colunas
            linha = indice_slot // colunas
            pagina = reader.pages[numero_pagina - 1]
            pagina.transfer_rotation_to_content()

            largura_pagina, altura_pagina = _medidas_pagina(pagina)
            escala = min(largura_celula / largura_pagina, altura_celula / altura_pagina)
            largura_render = largura_pagina * escala
            altura_render = altura_pagina * escala

            origem_x_celula = coluna * largura_celula
            origem_y_celula = altura_folha - ((linha + 1) * altura_celula)

            deslocamento_x = origem_x_celula + ((largura_celula - largura_render) / 2.0)
            deslocamento_y = origem_y_celula + ((altura_celula - altura_render) / 2.0)

            transformacao = Transformation().scale(escala, escala).translate(
                tx=deslocamento_x,
                ty=deslocamento_y
            )
            folha.merge_transformed_page(pagina, transformacao, expand=False)

    nome_temporario = f"{caminho_origem.stem}_{paginas_por_folha}up_{uuid.uuid4().hex}.pdf"
    caminho_destino = caminho_origem.with_name(nome_temporario)
    with caminho_destino.open("wb") as destino:
        writer.write(destino)

    return caminho_destino


def gerar_pdf_duas_por_folha_paisagem(caminho_origem: Path, intervalo_paginas: str = "") -> Path:
    return gerar_pdf_n_por_folha(
        caminho_origem=caminho_origem,
        paginas_por_folha=2,
        intervalo_paginas=intervalo_paginas,
        orientacao="paisagem",
    )
