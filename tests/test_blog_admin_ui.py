import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main


ROOT = Path(__file__).resolve().parents[1]


class BlogAdminUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        cls.response = cls.client.get("/admin/blog")
        cls.html = cls.response.text

    def test_page_renders_editor_library_and_accessible_states(self):
        self.assertEqual(self.response.status_code, 200)
        for fragment in (
            'data-admin-active-tab="blog"',
            'id="blogPostList"',
            'id="blogPostForm"',
            'id="blogRichEditor"',
            'contenteditable="true"',
            'role="toolbar"',
            'id="blogImageGallery"',
            'id="blogPageMessage"',
            'aria-live="polite"',
            'accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"',
            "colar ou arrastar uma imagem",
            'id="blogImageSizeControls"',
            'data-blog-image-width="25"',
            'data-blog-image-width="100"',
        ):
            self.assertIn(fragment, self.html)

    def test_page_loads_only_existing_blog_assets(self):
        assets = (
            "css/blog/admin.css",
            "css/blog/library.css",
            "css/blog/editor.css",
            "js/blog/state.js",
            "js/blog/api.js",
            "js/blog/editor.js",
            "js/blog/images.js",
            "js/blog/page.js",
        )
        for asset in assets:
            with self.subTest(asset=asset):
                self.assertIn(f"/static/{asset}", self.html)
                self.assertTrue((ROOT / "static" / asset).is_file())
                self.assertEqual(self.client.get(f"/static/{asset}").status_code, 200)

    def test_navigation_and_client_contract_keep_blog_admin_only(self):
        sidebar = (ROOT / "templates/includes/app_sidebar_config.html").read_text(encoding="utf-8")
        page_script = (ROOT / "static/js/blog/page.js").read_text(encoding="utf-8")
        api_script = (ROOT / "static/js/blog/api.js").read_text(encoding="utf-8")
        editor_script = (ROOT / "static/js/blog/editor.js").read_text(encoding="utf-8")
        state_script = (ROOT / "static/js/blog/state.js").read_text(encoding="utf-8")
        admin_css = (ROOT / "static/css/blog/admin.css").read_text(encoding="utf-8")
        editor_css = (ROOT / "static/css/blog/editor.css").read_text(encoding="utf-8")
        public_article_css = (ROOT / "static/css/blog/public-article.css").read_text(
            encoding="utf-8"
        )

        self.assertIn('"href": "/admin/blog"', sidebar)
        self.assertIn('"admin_only": true', sidebar)
        self.assertIn('normalizarCargoUsuario(user) !== "ADMIN"', page_script)
        self.assertIn('const baseUrl = "/api/admin/blog"', api_script)
        self.assertIn("sanitizeHtml", editor_script)
        self.assertIn("data-blog-image", editor_script)
        self.assertIn("transferredImage", editor_script)
        self.assertIn('addEventListener("drop"', editor_script)
        self.assertIn("uploadInlineImage", editor_script)
        self.assertIn("allowedImageWidths", editor_script)
        self.assertIn("setSelectedImageWidth", editor_script)
        self.assertIn('figure[data-width="25"]', editor_css)
        self.assertIn(".blog-rich-editor.is-drag-over", editor_css)
        self.assertIn('.blog-article-figure[data-width="75"]', public_article_css)
        self.assertIn("Não foi possível conectar ao servidor", state_script)
        self.assertIn(".blog-editor-empty[hidden]", admin_css)


if __name__ == "__main__":
    unittest.main()
