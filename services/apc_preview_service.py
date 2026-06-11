import tempfile
from pathlib import Path

from services.file_service import converter_para_pdf, obter_extensao_arquivo


def gerar_preview_pdf_apc(caminho_origem: Path, nome_arquivo: str) -> bytes:
    extensao = obter_extensao_arquivo(nome_arquivo) or caminho_origem.suffix.lower()

    with tempfile.TemporaryDirectory(prefix="apc_preview_") as diretorio:
        caminho_temporario = Path(diretorio) / f"anexo{extensao}"
        caminho_temporario.write_bytes(caminho_origem.read_bytes())
        caminho_pdf = converter_para_pdf(caminho_temporario, extensao)
        conteudo_pdf = caminho_pdf.read_bytes()

    if not conteudo_pdf:
        raise RuntimeError("Falha ao gerar PDF para visualizacao do anexo.")
    return conteudo_pdf
