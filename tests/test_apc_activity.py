import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pypdf import PdfReader

from modules.apc_activity.pdf_service import (
    BODY_FONT_SIZE,
    CREST_SIZE,
    LINE_HEIGHT,
    _register_font,
    generate_activity_pdf,
)
from reportlab.pdfbase import pdfmetrics
from modules.apc_activity.sanitizer import sanitize_activity_html, visible_text
from modules.apc_activity.schemas import ApcActivityIn, ApcActivityPreviewIn
from modules.apc_activity import service as activity_service
from modules.apc_activity.service import prepare_activity_data
from routers import apc_router


class ApcActivityPdfTests(unittest.TestCase):
    def _data(self, *, columns=1, activities=None):
        return {
            "professor_nome": "Professora Maria de Souza",
            "turma_nome": "6º ANO A",
            "disciplina_nome": "Ciências",
            "data_referencia": "2026-06-29",
            "data_referencia_br": "29/06/2026",
            "habilidade": "MS.EF06CI04.s.04 - Associar a produção de materiais ao desenvolvimento científico.",
            "conteudo": "Desenvolvimento científico e tecnológico",
            "corpo_html": activities or "<p>Leia o <strong>texto</strong> com atenção.</p><ol><li>Primeira questão.</li><li>Segunda questão.</li></ol>",
            "activity_columns": columns,
        }

    def test_generates_valid_a4_pdf_for_both_layouts(self):
        for columns in (1, 2):
            with self.subTest(columns=columns):
                content = generate_activity_pdf(self._data(columns=columns))
                self.assertTrue(content.startswith(b"%PDF"))
                reader = PdfReader(__import__("io").BytesIO(content))
                self.assertGreaterEqual(len(reader.pages), 1)
                page = reader.pages[0]
                self.assertAlmostEqual(float(page.mediabox.width) / float(page.mediabox.height), 210 / 297, places=2)

    def test_reference_docx_typography_and_crest_geometry(self):
        self.assertAlmostEqual(BODY_FONT_SIZE * 72 / 150, 12, places=1)
        self.assertAlmostEqual(LINE_HEIGHT * 72 / 150, 18, delta=0.25)
        self.assertAlmostEqual(CREST_SIZE[0] * 25.4 / 150, 19.3, places=1)
        self.assertAlmostEqual(CREST_SIZE[1] * 25.4 / 150, 20.0, places=1)

    def test_font_registration_falls_back_when_system_fonts_are_missing(self):
        name = "APCTestTimesFallback"
        _register_font(name, ("/font/path/that/does/not/exist.ttf",), "Times-Roman")
        self.assertIn(name, pdfmetrics.getRegisteredFontNames())
        self.assertGreater(pdfmetrics.stringWidth("APC Ciências", name, 12), 0)

    def test_pdf_keeps_text_as_vectors_instead_of_page_image(self):
        content = generate_activity_pdf(self._data())
        page = PdfReader(__import__("io").BytesIO(content)).pages[0]
        extracted = page.extract_text()
        self.assertIn("PROFESSOR:", extracted)
        self.assertIn("ATIVIDADE PEDAG", extracted)
        self.assertLessEqual(len(page.images), 1)

    def test_preview_renders_header_before_activity_fields_are_filled(self):
        data = self._data()
        data.update({"habilidade": "", "conteudo": "", "corpo_html": ""})
        page = PdfReader(__import__("io").BytesIO(generate_activity_pdf(data))).pages[0]
        extracted = page.extract_text()
        self.assertIn("PROFESSOR:", extracted)
        self.assertIn("Professora Maria de Souza", extracted)
        self.assertIn("HABILIDADE", extracted)

    def test_long_activity_creates_multiple_pages(self):
        items = "".join(f"<li>Questão {index} com um enunciado suficientemente detalhado para ocupar espaço.</li>" for index in range(1, 90))
        content = generate_activity_pdf(self._data(columns=2, activities=f"<ol>{items}</ol>"))
        self.assertGreater(len(PdfReader(__import__("io").BytesIO(content)).pages), 1)

    def test_sanitizer_removes_scripts_and_attributes(self):
        sanitized = sanitize_activity_html('<p onclick="bad()">Texto <strong>seguro</strong><script>alert(1)</script></p>')
        self.assertNotIn("onclick", sanitized)
        self.assertNotIn("<script", sanitized)
        self.assertIn("<strong>seguro</strong>", sanitized)
        self.assertEqual(visible_text(sanitized), "Texto seguro")

    def test_sanitizer_preserves_contenteditable_line_breaks(self):
        sanitized = sanitize_activity_html("Primeira linha<div>Segunda linha</div>")
        self.assertEqual(sanitized, "Primeira linha<p>Segunda linha</p>")


class ApcActivityRouterTests(unittest.TestCase):
    def _payload(self):
        return ApcActivityIn(
            turma_id=10,
            disciplina_id=20,
            habilidade="EF00 - Habilidade",
            conteudo="Conteudo",
            corpo_html="<p>Texto livre</p>",
            activity_columns=1,
        )

    def test_preview_accepts_empty_content_but_save_validation_does_not(self):
        payload = ApcActivityPreviewIn(turma_id=10, disciplina_id=20)
        data = prepare_activity_data(
            payload,
            user={"nome": "Professor"},
            period={"data_referencia": "2026-07-14"},
            delivery={
                "turma_id": 10,
                "turma_nome": "6º A",
                "disciplina_id": 20,
                "disciplina_nome": "Ciências",
            },
            allow_incomplete=True,
        )
        self.assertEqual(data["habilidade"], "")
        self.assertEqual(data["corpo_html"], "")
        with self.assertRaisesRegex(ValueError, "habilidade"):
            prepare_activity_data(
                payload,
                user={"nome": "Professor"},
                period={"data_referencia": "2026-07-14"},
                delivery={"turma_id": 10, "disciplina_id": 20},
            )

    @patch.object(activity_service.repository, "upsert_generated_activity", return_value={"id": 2})
    @patch.object(activity_service.repository, "save_submission", return_value={"id": 1})
    @patch.object(activity_service, "generate_activity_pdf", return_value=b"%PDF-test")
    def test_first_save_does_not_treat_empty_old_path_as_current_directory(
        self, _generate, _save_submission, _upsert
    ):
        with TemporaryDirectory() as temp_dir:
            submission, activity, pdf = activity_service.save_activity(
                data={
                    "turma_id": 10,
                    "disciplina_id": 20,
                    "disciplina_nome": "Ciencias",
                    "data_referencia": "2026-07-14",
                    "habilidade": "EF00 - Habilidade",
                    "conteudo": "Conteudo",
                    "corpo_html": "<p>Texto</p>",
                    "activity_columns": 1,
                },
                period_id=1,
                user_id=7,
                existing=None,
                directory=Path(temp_dir),
            )
            self.assertEqual(submission["id"], 1)
            self.assertEqual(activity["id"], 2)
            self.assertEqual(pdf, b"%PDF-test")

    @patch.object(apc_router, "render_activity_preview", return_value=b"%PDF-preview")
    @patch.object(apc_router, "prepare_activity_data", return_value={"activity_columns": 1})
    @patch.object(apc_router, "_resolver_entrega_professor_apc", return_value=({"id": 1}, {"turma_id": 10, "disciplina_id": 20}))
    def test_preview_returns_pdf(self, _resolve, _prepare, _render):
        response = apc_router.visualizar_atividade_apc_api(1, self._payload(), {"id": 7, "cargo": "professor"})
        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(response.body, b"%PDF-preview")
        self.assertTrue(_prepare.call_args.kwargs["allow_incomplete"])

    @patch.object(apc_router, "record_event")
    @patch.object(apc_router, "_agendar_preview_apc")
    @patch.object(apc_router, "_remover_preview_cache_envio")
    @patch.object(apc_router, "_garantir_diretorio_apc")
    @patch.object(apc_router, "save_activity", return_value=({"id": 9}, {"id": 3}, b"%PDF"))
    @patch.object(apc_router, "prepare_activity_data", return_value={"activity_columns": 2})
    @patch.object(apc_router, "_resolver_entrega_professor_apc", return_value=({"id": 1}, {"turma_id": 10, "disciplina_id": 20, "envio": None}))
    def test_generation_schedules_normal_attachment_preview(
        self, _resolve, _prepare, _save, _directory, remove_preview, schedule_preview, _audit
    ):
        result = apc_router.criar_atividade_apc_api(1, self._payload(), {"id": 7, "nome": "Professor", "cargo": "professor"})
        self.assertEqual(result["envio"]["id"], 9)
        remove_preview.assert_called_once_with(9)
        schedule_preview.assert_called_once_with({"id": 9})


if __name__ == "__main__":
    unittest.main()
