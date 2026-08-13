import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from modules.blog import public_router, repository
from modules.blog.host_middleware import BlogSubdomainMiddleware
from routers.config import STATIC_DIR
from tests.blog_test_support import apply_blog_migrations


class BlogPublicRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.db_path = temp_path / "blog.db"
        self.image_dir = temp_path / "images"
        self.image_dir.mkdir()

        conn = self._connect()
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO usuarios (id) VALUES (7)")
        apply_blog_migrations(conn)
        conn.close()

        self.connection_patch = patch(
            "modules.blog.repository.get_connection", side_effect=self._connect
        )
        self.image_dir_patch = patch(
            "modules.blog.image_service.BLOG_IMAGE_DIR", self.image_dir
        )
        self.connection_patch.start()
        self.image_dir_patch.start()

        self.published_token = "a" * 32
        self.draft_token = "b" * 32
        self.published = self._create_post(
            title="Feira cultural da escola",
            slug="feira-cultural-da-escola",
            token=self.published_token,
            published=True,
        )
        self.draft = self._create_post(
            title="Noticia ainda em revisao",
            slug="noticia-em-revisao",
            token=self.draft_token,
            published=False,
        )

        app = FastAPI()
        app.add_middleware(BlogSubdomainMiddleware, public_host="blog.eepjd.com.br")
        app.include_router(public_router.router)
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.image_dir_patch.stop()
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _create_post(self, *, title: str, slug: str, token: str, published: bool) -> dict:
        body_html = (
            '<p onclick="alert(1)">A comunidade participou.</p>'
            '<script>alert("x")</script>'
            f'<figure data-blog-image="{token}">'
            f'<img data-blog-image="{token}" onerror="alert(1)">'
            '<figcaption>Apresentacao dos estudantes</figcaption></figure>'
        )
        post = repository.create_post(
            author_user_id=7,
            title=title,
            slug=slug,
            summary="Um encontro de aprendizagem e comunidade.",
            body_html=body_html,
            tags=[{"name": "Projetos", "slug": "projetos"}] if published else [],
        )
        repository.create_image(
            post["id"],
            {
                "token": token,
                "stored_name": f"{token}.webp",
                "thumbnail_name": f"{token}-thumb.webp",
                "alt_text": "Estudantes apresentando seus trabalhos",
                "caption": "Apresentacao dos estudantes",
                "width": 1200,
                "height": 800,
                "is_cover": True,
            },
        )
        (self.image_dir / f"{token}.webp").write_bytes(b"public-image")
        (self.image_dir / f"{token}-thumb.webp").write_bytes(b"public-thumb")
        if published:
            repository.set_post_status(post["id"], "PUBLISHED")
        return post

    def test_anonymous_home_lists_only_published_posts(self):
        response = self.client.get("/blog/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-robots-tag"], "noindex, nofollow")
        self.assertIn("Feira cultural da escola", response.text)
        self.assertNotIn("Noticia ainda em revisao", response.text)
        self.assertIn(f"/blog/artigos/{self.published['slug']}", response.text)
        self.assertIn("Projetos", response.text)

        filtered = self.client.get("/blog/", params={"tag": "projetos"})
        self.assertEqual(filtered.status_code, 200)
        self.assertIn('aria-current="page">Projetos', filtered.text)
        self.assertIn("?tag=projetos", filtered.text)

    def test_article_is_sanitized_and_draft_returns_404(self):
        response = self.client.get(f"/blog/artigos/{self.published['slug']}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("A comunidade participou.", response.text)
        self.assertIn(f'/blog/images/{self.published_token}', response.text)
        self.assertNotIn("onclick", response.text)
        self.assertNotIn("onerror", response.text)
        self.assertNotIn("alert(&quot;x&quot;)", response.text)
        self.assertEqual(
            self.client.get(f"/blog/artigos/{self.draft['slug']}").status_code,
            404,
        )

    def test_public_image_requires_a_published_owner(self):
        response = self.client.get(f"/blog/images/{self.published_token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"public-image")
        self.assertIn("immutable", response.headers["cache-control"])
        self.assertEqual(response.headers["x-robots-tag"], "noindex, noimageindex")
        self.assertEqual(
            self.client.get(f"/blog/images/{self.draft_token}").status_code,
            404,
        )

    def test_blog_subdomain_uses_clean_public_urls(self):
        response = self.client.get("/", headers={"host": "blog.eepjd.com.br"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Escola Estadual Padre José Daniel", response.text)
        self.assertNotIn("Padre João D'Ávila", response.text)
        self.assertIn(f'href="/artigos/{self.published["slug"]}"', response.text)
        self.assertNotIn(f'href="/blog/artigos/{self.published["slug"]}"', response.text)
        article = self.client.get(
            f"/artigos/{self.published['slug']}",
            headers={"host": "blog.eepjd.com.br"},
        )
        self.assertEqual(article.status_code, 200)
        self.assertIn(f'src="/images/{self.published_token}"', article.text)
        self.assertNotIn("x-robots-tag", article.headers)

    def test_robots_and_sitemap_only_advertise_public_urls(self):
        robots = self.client.get(
            "/robots.txt", headers={"host": "blog.eepjd.com.br"}
        )
        sitemap = self.client.get(
            "/sitemap.xml", headers={"host": "blog.eepjd.com.br"}
        )

        self.assertEqual(robots.status_code, 200)
        self.assertIn("User-agent: *", robots.text)
        self.assertIn("Sitemap: https://blog.eepjd.com.br/sitemap.xml", robots.text)
        self.assertEqual(sitemap.status_code, 200)
        ElementTree.fromstring(sitemap.content)
        self.assertIn("https://blog.eepjd.com.br/</loc>", sitemap.text)
        self.assertIn(
            f"https://blog.eepjd.com.br/artigos/{self.published['slug']}",
            sitemap.text,
        )
        self.assertNotIn(self.draft["slug"], sitemap.text)
        self.assertNotIn("/blog/artigos/", sitemap.text)

    def test_public_host_adds_security_headers_and_removes_blog_prefix(self):
        response = self.client.get(
            "https://blog.eepjd.com.br/", follow_redirects=False
        )
        redirect = self.client.get(
            f"/blog/artigos/{self.published['slug']}?origem=teste",
            headers={"host": "blog.eepjd.com.br"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("default-src 'self'", response.headers["content-security-policy"])
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("max-age=31536000", response.headers["strict-transport-security"])
        self.assertEqual(redirect.status_code, 308)
        self.assertEqual(
            redirect.headers["location"],
            f"/artigos/{self.published['slug']}?origem=teste",
        )


if __name__ == "__main__":
    unittest.main()
