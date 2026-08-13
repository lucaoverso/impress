import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from auth import get_usuario_logado
from modules.blog.router import router
from tests.blog_test_support import apply_blog_migrations


def _jpeg_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1200, 800), (20, 80, 140)).save(output, format="JPEG")
    return output.getvalue()


class BlogAdminRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "blog-router.db"
        self.image_dir = Path(self.temp_dir.name) / "images"
        self.image_dir.mkdir()

        conn = self._connect()
        conn.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO usuarios (id) VALUES (7)")
        apply_blog_migrations(conn)
        conn.close()

        self.connection_patch = patch(
            "modules.blog.repository.get_connection", side_effect=self._connect
        )
        self.image_dir_patch = patch("modules.blog.config.BLOG_IMAGE_DIR", self.image_dir)
        self.connection_patch.start()
        self.image_dir_patch.start()

        self.app = FastAPI()
        self.app.include_router(router)
        self.admin = {"id": 7, "perfil": "admin", "cargo": "ADMIN"}
        self.app.dependency_overrides[get_usuario_logado] = lambda: self.admin
        self.client = TestClient(self.app)

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

    def _create_post(self, title: str = "Feira da escola") -> dict:
        response = self.client.post(
            "/api/admin/blog/posts",
            json={
                "title": title,
                "summary": "Noticia da comunidade escolar",
                "body_html": "<p>Conteudo da noticia.</p>",
                "tags": [" Projetos ", "projetos", "Vida escolar"],
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def _upload_image(self, post_id: int, *, is_cover: bool = False) -> dict:
        response = self.client.post(
            f"/api/admin/blog/posts/{post_id}/images",
            files={"file": ("evento.jpg", _jpeg_bytes(), "image/jpeg")},
            data={
                "alt_text": "Estudantes durante o evento",
                "caption": "Evento realizado na escola",
                "is_cover": str(is_cover).lower(),
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_valid_jpeg_is_accepted_with_generic_browser_mime(self):
        post = self._create_post("Imagem com MIME generico")
        response = self.client.post(
            f"/api/admin/blog/posts/{post['id']}/images",
            files={"file": ("foto.JPG", _jpeg_bytes(), "application/octet-stream")},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["width"], 1200)

    def test_admin_can_manage_article_images_and_publication_lifecycle(self):
        post = self._create_post("Ação da escola")
        self.assertEqual(post["slug"], "acao-da-escola")
        self.assertEqual(post["status"], "DRAFT")
        self.assertEqual(post["tags"], [
            {"name": "Projetos", "slug": "projetos"},
            {"name": "Vida escolar", "slug": "vida-escolar"},
        ])

        updated = self.client.put(
            f"/api/admin/blog/posts/{post['id']}",
            json={
                "title": "Ação cultural da escola",
                "summary": "Resumo atualizado",
                "body_html": "<p>Conteudo atualizado.</p>",
                "tags": ["Eventos"],
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["slug"], "acao-cultural-da-escola")
        self.assertEqual(updated.json()["tags"][0]["slug"], "eventos")

        image = self._upload_image(post["id"])
        cover = self.client.put(f"/api/admin/blog/posts/{post['id']}/cover/{image['id']}")
        self.assertEqual(cover.status_code, 200)
        self.assertTrue(cover.json()["is_cover"])

        metadata = self.client.patch(
            f"/api/admin/blog/posts/{post['id']}/images/{image['id']}",
            json={"alt_text": "Apresentacao cultural", "caption": "Legenda revisada"},
        )
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(metadata.json()["caption"], "Legenda revisada")

        details = self.client.get(f"/api/admin/blog/posts/{post['id']}")
        self.assertEqual(details.status_code, 200)
        self.assertEqual([item["id"] for item in details.json()["images"]], [image["id"]])

        stored = self.client.get(f"/api/admin/blog/images/{image['token']}")
        thumbnail = self.client.get(
            f"/api/admin/blog/images/{image['token']}", params={"thumbnail": "true"}
        )
        self.assertEqual(stored.status_code, 200)
        self.assertEqual(stored.headers["content-type"], "image/webp")
        self.assertEqual(stored.headers["cache-control"], "private, no-store")
        self.assertEqual(thumbnail.status_code, 200)
        self.assertLess(len(thumbnail.content), len(stored.content))

        published = self.client.post(f"/api/admin/blog/posts/{post['id']}/publish")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.json()["status"], "PUBLISHED")
        listing = self.client.get("/api/admin/blog/posts", params={"status": "PUBLISHED"})
        self.assertEqual([item["id"] for item in listing.json()], [post["id"]])

        unpublished = self.client.post(f"/api/admin/blog/posts/{post['id']}/unpublish")
        self.assertEqual(unpublished.json()["status"], "DRAFT")
        self.client.post(f"/api/admin/blog/posts/{post['id']}/publish")
        archived = self.client.post(f"/api/admin/blog/posts/{post['id']}/archive")
        self.assertEqual(archived.json()["status"], "ARCHIVED")
        restored = self.client.post(f"/api/admin/blog/posts/{post['id']}/restore")
        self.assertEqual(restored.json()["status"], "DRAFT")

        removed = self.client.delete(f"/api/admin/blog/posts/{post['id']}/images/{image['id']}")
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(list(self.image_dir.iterdir()), [])

    def test_only_admin_can_use_blog_management_api(self):
        self.app.dependency_overrides[get_usuario_logado] = lambda: {
            "id": 7,
            "perfil": "professor",
            "cargo": "PROFESSOR",
        }
        response = self.client.get("/api/admin/blog/posts")
        self.assertEqual(response.status_code, 403)

        protected_app = FastAPI()
        protected_app.include_router(router)
        with TestClient(protected_app) as client:
            unauthenticated = client.get(
                "/api/admin/blog/posts", headers={"Authorization": "Invalid token"}
            )
        self.assertEqual(unauthenticated.status_code, 401)

    def test_domain_errors_have_stable_http_statuses_and_image_scope(self):
        first = self._create_post("Primeiro artigo")
        second = self._create_post("Segundo artigo")

        incomplete = self.client.post(f"/api/admin/blog/posts/{first['id']}/publish")
        self.assertEqual(incomplete.status_code, 400)

        invalid_image = self.client.post(
            f"/api/admin/blog/posts/{first['id']}/images",
            files={"file": ("arquivo.jpg", b"invalido", "image/jpeg")},
        )
        self.assertEqual(invalid_image.status_code, 400)

        image = self._upload_image(first["id"])
        wrong_post = self.client.patch(
            f"/api/admin/blog/posts/{second['id']}/images/{image['id']}",
            json={"alt_text": "Outro texto", "caption": ""},
        )
        self.assertEqual(wrong_post.status_code, 404)

        missing = self.client.get("/api/admin/blog/posts/999999")
        self.assertEqual(missing.status_code, 404)
        invalid_status = self.client.get("/api/admin/blog/posts", params={"status": "INVALID"})
        self.assertEqual(invalid_status.status_code, 422)


if __name__ == "__main__":
    unittest.main()
