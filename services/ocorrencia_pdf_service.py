from __future__ import annotations

from services.ocorrencia_pdf.base_legal import _montar_blocos_base_legal
from services.ocorrencia_pdf.helpers import _obter_gravidade_ocorrencia, _obter_titulo_documento
from services.ocorrencia_pdf.parser import _obter_runs_descricao_formatada
from services.ocorrencia_pdf.renderer import _RenderizadorRegistroOcorrencia, gerar_pdf_ocorrencia_registro

__all__ = [
    "_RenderizadorRegistroOcorrencia",
    "_montar_blocos_base_legal",
    "_obter_gravidade_ocorrencia",
    "_obter_runs_descricao_formatada",
    "_obter_titulo_documento",
    "gerar_pdf_ocorrencia_registro",
]
