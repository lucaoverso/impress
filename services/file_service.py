import subprocess
import shutil
import os
from pathlib import Path

SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}
OFFICE_EXTENSIONS = {".docx", ".doc"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SOFFICE_TIMEOUT_SECONDS = 120
SOFFICE_PATHS_COMUNS = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/homebrew/bin/soffice",
    "/snap/bin/libreoffice",
)


def obter_extensao_arquivo(nome_arquivo: str) -> str:
    return Path(nome_arquivo or "").suffix.lower()


def arquivo_suportado(nome_arquivo: str) -> bool:
    return obter_extensao_arquivo(nome_arquivo) in SUPPORTED_UPLOAD_EXTENSIONS


def converter_para_pdf(caminho_origem: Path, extensao: str) -> Path:
    extensao_limpa = str(extensao or "").lower()

    if extensao_limpa == ".pdf":
        return caminho_origem
    if extensao_limpa in OFFICE_EXTENSIONS:
        return converter_office_para_pdf(caminho_origem)
    if extensao_limpa in IMAGE_EXTENSIONS:
        return converter_imagem_para_pdf(caminho_origem)

    raise ValueError("Formato de arquivo não suportado para impressão.")

def _descobrir_comando_soffice() -> str | None:
    comando_env = os.getenv("LIBREOFFICE_COMMAND", "").strip()
    if comando_env:
        caminho_env = Path(comando_env)
        if caminho_env.exists():
            return str(caminho_env)
        resolvido_env = shutil.which(comando_env)
        if resolvido_env:
            return resolvido_env

    for candidato in ("soffice", "libreoffice"):
        resolvido = shutil.which(candidato)
        if resolvido:
            return resolvido

    for caminho in SOFFICE_PATHS_COMUNS:
        candidato = Path(caminho)
        if candidato.exists():
            return str(candidato)

    return None


def converter_office_para_pdf(caminho_origem: Path) -> Path:
    comando_soffice = _descobrir_comando_soffice()
    if not comando_soffice:
        raise RuntimeError(
            "Conversão de DOC/DOCX indisponível: LibreOffice não encontrado. "
            "Configure LIBREOFFICE_COMMAND com o caminho do 'soffice' ou envie o arquivo em PDF."
        )

    caminho_destino = caminho_origem.with_suffix(".pdf")
    if caminho_destino.exists():
        caminho_destino.unlink()

    cmd = [
        comando_soffice,
        "--headless",
        "--nologo",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(caminho_origem.parent),
        str(caminho_origem),
    ]

    try:
        resultado = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=SOFFICE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Timeout ao converter documento Office para PDF."
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Comando do LibreOffice não encontrado para conversão de DOC/DOCX."
        ) from exc

    if resultado.returncode != 0:
        saida = "\n".join(
            [
                parte
                for parte in [resultado.stdout.strip(), resultado.stderr.strip()]
                if parte
            ]
        ).strip()
        raise RuntimeError(saida or "Falha ao converter documento Office para PDF.")

    if not caminho_destino.exists():
        raise RuntimeError("Conversão de DOC/DOCX finalizou sem gerar PDF.")

    return caminho_destino


def converter_imagem_para_pdf(caminho_origem: Path) -> Path:
    try:
        from PIL import Image, ImageOps
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Conversão de imagens requer a biblioteca Pillow no servidor."
        ) from exc

    caminho_destino = caminho_origem.with_suffix(".pdf")
    if caminho_destino.exists():
        caminho_destino.unlink()

    try:
        with Image.open(caminho_origem) as imagem_original:
            imagem = ImageOps.exif_transpose(imagem_original)
            if imagem.mode in {"RGBA", "LA"}:
                fundo = Image.new("RGB", imagem.size, (255, 255, 255))
                fundo.paste(imagem, mask=imagem.split()[-1])
                imagem_pdf = fundo
            elif imagem.mode == "P" and "transparency" in imagem.info:
                rgba = imagem.convert("RGBA")
                fundo = Image.new("RGB", rgba.size, (255, 255, 255))
                fundo.paste(rgba, mask=rgba.split()[-1])
                imagem_pdf = fundo
            else:
                imagem_pdf = imagem.convert("RGB")

            imagem_pdf.save(caminho_destino, "PDF", resolution=300.0)
    except Exception as exc:
        raise RuntimeError(
            "Falha ao converter imagem para PDF. Verifique se o arquivo está íntegro."
        ) from exc

    return caminho_destino
