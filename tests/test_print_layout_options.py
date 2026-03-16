import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from services.pdf_service import (
    A4_PAISAGEM_ALTURA_PT,
    A4_PAISAGEM_LARGURA_PT,
    A4_RETRATO_ALTURA_PT,
    A4_RETRATO_LARGURA_PT,
    _obter_layout_nup,
    gerar_pdf_n_por_folha,
)
from services.printer import _montar_opcoes_cups_legado


class PrintLayoutOptionsTest(unittest.TestCase):
    def _criar_pdf_origem(self, pasta: Path, paginas: int = 2) -> Path:
        caminho = pasta / "origem.pdf"
        writer = PdfWriter()
        for _ in range(paginas):
            writer.add_blank_page(width=A4_RETRATO_LARGURA_PT, height=A4_RETRATO_ALTURA_PT)

        with caminho.open("wb") as arquivo:
            writer.write(arquivo)

        return caminho

    def test_layout_nup_duas_por_folha_varia_com_orientacao(self):
        self.assertEqual(_obter_layout_nup(2, "retrato"), (1, 2))
        self.assertEqual(_obter_layout_nup(2, "paisagem"), (2, 1))

    def test_gerar_pdf_duas_por_folha_preserva_retrato(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pasta = Path(tmp_dir)
            origem = self._criar_pdf_origem(pasta)
            saida = gerar_pdf_n_por_folha(origem, paginas_por_folha=2, orientacao="retrato")

            reader = PdfReader(str(saida))
            self.assertEqual(len(reader.pages), 1)
            pagina = reader.pages[0]
            self.assertAlmostEqual(float(pagina.mediabox.width), A4_RETRATO_LARGURA_PT, places=1)
            self.assertAlmostEqual(float(pagina.mediabox.height), A4_RETRATO_ALTURA_PT, places=1)

    def test_gerar_pdf_duas_por_folha_paisagem_permanece_em_paisagem(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pasta = Path(tmp_dir)
            origem = self._criar_pdf_origem(pasta)
            saida = gerar_pdf_n_por_folha(origem, paginas_por_folha=2, orientacao="paisagem")

            reader = PdfReader(str(saida))
            self.assertEqual(len(reader.pages), 1)
            pagina = reader.pages[0]
            self.assertAlmostEqual(float(pagina.mediabox.width), A4_PAISAGEM_LARGURA_PT, places=1)
            self.assertAlmostEqual(float(pagina.mediabox.height), A4_PAISAGEM_ALTURA_PT, places=1)

    def test_opcoes_cups_duas_por_folha_seguem_orientacao(self):
        opcoes_retrato = _montar_opcoes_cups_legado(
            {"paginas_por_folha": 2, "orientacao": "retrato", "duplex": False}
        )
        opcoes_paisagem = _montar_opcoes_cups_legado(
            {"paginas_por_folha": 2, "orientacao": "paisagem", "duplex": False}
        )

        self.assertEqual(opcoes_retrato["number-up-layout"], "tblr")
        self.assertEqual(opcoes_paisagem["number-up-layout"], "lrtb")


if __name__ == "__main__":
    unittest.main()
