from pypdf import PdfReader

def contar_paginas_pdf(caminho_arquivo: str) -> int:
    reader = PdfReader(caminho_arquivo)
    return len(reader.pages)
