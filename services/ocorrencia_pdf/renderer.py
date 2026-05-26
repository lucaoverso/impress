from __future__ import annotations

from services.ocorrencia_pdf.renderer_content import _RenderizadorConteudoMixin
from services.ocorrencia_pdf.renderer_footer import _RenderizadorRodapeMixin
from services.ocorrencia_pdf.renderer_structure import _RenderizadorEstruturaMixin


class _RenderizadorRegistroOcorrencia(
    _RenderizadorRodapeMixin,
    _RenderizadorConteudoMixin,
    _RenderizadorEstruturaMixin,
):
    pass


def gerar_pdf_ocorrencia_registro(ocorrencia: dict, *, turma: dict | None = None) -> bytes:
    return _RenderizadorRegistroOcorrencia(ocorrencia, turma=turma).renderizar()
