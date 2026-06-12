import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from static_files import (
    IMAGE_CACHE_CONTROL,
    IMMUTABLE_CACHE_CONTROL,
    REVALIDATE_CACHE_CONTROL,
    CachedStaticFiles,
)


class StaticFilesCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        static_dir = Path(self.temp_dir.name)
        (static_dir / "img" / "resources").mkdir(parents=True)
        (static_dir / "img" / "resources" / "projetor-a1b2c3d4e5.webp").write_bytes(
            b"resource-image"
        )
        (static_dir / "img" / "logo.png").write_bytes(b"logo-image")
        (static_dir / "js").mkdir()
        (static_dir / "js" / "app.js").write_text(
            "console.log('cache');",
            encoding="utf-8",
        )
        (static_dir / "fonts").mkdir()
        (static_dir / "fonts" / "icons.woff2").write_bytes(b"font-data")

        app = FastAPI()
        app.mount("/static", CachedStaticFiles(directory=static_dir), name="static")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def test_resource_image_uses_long_immutable_cache(self):
        response = self.client.get(
            "/static/img/resources/projetor-a1b2c3d4e5.webp"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), IMMUTABLE_CACHE_CONTROL)

    def test_versioned_asset_uses_long_immutable_cache(self):
        response = self.client.get("/static/js/app.js?v=build-123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), IMMUTABLE_CACHE_CONTROL)

    def test_hashed_font_query_uses_immutable_cache_and_font_content_type(self):
        response = self.client.get("/static/fonts/icons.woff2?e34853135f9e39ac")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), IMMUTABLE_CACHE_CONTROL)
        self.assertEqual(response.headers.get("Content-Type"), "font/woff2")

    def test_common_image_uses_short_cache(self):
        response = self.client.get("/static/img/logo.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), IMAGE_CACHE_CONTROL)

    def test_unversioned_asset_requires_revalidation(self):
        response = self.client.get("/static/js/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), REVALIDATE_CACHE_CONTROL)

    def test_etag_allows_conditional_request(self):
        first_response = self.client.get("/static/js/app.js?v=build-123")
        etag = first_response.headers.get("ETag")

        second_response = self.client.get(
            "/static/js/app.js?v=build-123",
            headers={"If-None-Match": etag},
        )

        self.assertTrue(etag)
        self.assertEqual(second_response.status_code, 304)
        self.assertEqual(
            second_response.headers.get("Cache-Control"),
            IMMUTABLE_CACHE_CONTROL,
        )


if __name__ == "__main__":
    unittest.main()
