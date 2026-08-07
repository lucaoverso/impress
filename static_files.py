import mimetypes
from pathlib import PurePosixPath

from fastapi.staticfiles import StaticFiles


mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
IMAGE_CACHE_CONTROL = "public, max-age=86400"
REVALIDATE_CACHE_CONTROL = "public, max-age=0, must-revalidate"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
FONT_EXTENSIONS = {".woff", ".woff2"}


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = self._cache_control(path, scope)
        return response

    @staticmethod
    def _cache_control(path: str, scope) -> str:
        normalized_path = path.replace("\\", "/").lstrip("/")
        has_version_query = bool(scope.get("query_string", b""))
        extension = PurePosixPath(normalized_path).suffix.lower()
        resource_image_mount = str(scope.get("root_path", "")).rstrip("/").endswith(
            "/static/img/resources"
        )

        if (
            resource_image_mount
            or normalized_path.startswith("img/resources/")
            or (extension in FONT_EXTENSIONS and has_version_query)
        ):
            return IMMUTABLE_CACHE_CONTROL

        if extension in IMAGE_EXTENSIONS:
            return IMAGE_CACHE_CONTROL

        # CSS and JavaScript must revalidate even if a deployment accidentally
        # reuses STATIC_ASSET_VERSION. ETags keep unchanged responses cheap.
        return REVALIDATE_CACHE_CONTROL
