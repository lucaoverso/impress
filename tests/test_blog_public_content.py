import unittest

from modules.blog.public_content import sanitize_public_html


class BlogPublicContentTests(unittest.TestCase):
    def setUp(self):
        self.token = "a" * 32
        self.images = [
            {
                "token": self.token,
                "alt_text": 'Feira de ciencias "na escola"',
            }
        ]

    def sanitize(self, value: str) -> str:
        return sanitize_public_html(
            value,
            image_base_path="/blog/images",
            images=self.images,
        )

    def test_keeps_editor_formatting_and_safe_alignment(self):
        result = self.sanitize(
            '<h2>Projeto</h2><p style="text-align: center" onclick="x()">'
            '<strong>Aprender</strong><br><em>juntos</em></p>'
        )

        self.assertIn("<h2>Projeto</h2>", result)
        self.assertIn('<p style="text-align: center">', result)
        self.assertIn("<strong>Aprender</strong><br><em>juntos</em>", result)
        self.assertNotIn("onclick", result)

    def test_removes_active_content_and_escapes_text(self):
        result = self.sanitize(
            '<p>Antes<script>alert("x")</script><iframe><b>oculto</b></iframe>'
            '<span title="x">&lt;depois&gt;</span></p>'
        )

        self.assertEqual(result, "<p>Antes&lt;depois&gt;</p>")
        self.assertNotIn("alert", result)
        self.assertNotIn("iframe", result)

    def test_only_renders_images_owned_by_the_article(self):
        result = self.sanitize(
            f'<figure data-blog-image="{self.token}">'
            f'<img data-blog-image="{self.token}" src="https://example.com/x" onerror="x()">'
            '<figcaption>Turma apresentando o projeto</figcaption></figure>'
            f'<img data-blog-image="{"b" * 32}">'
        )

        self.assertIn(f'src="/blog/images/{self.token}"', result)
        self.assertIn('alt="Feira de ciencias &quot;na escola&quot;"', result)
        self.assertIn("<figcaption>Turma apresentando o projeto</figcaption>", result)
        self.assertNotIn("example.com", result)
        self.assertNotIn("onerror", result)
        self.assertNotIn("b" * 32, result)


if __name__ == "__main__":
    unittest.main()
