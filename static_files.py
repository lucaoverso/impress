import mimetypes
from pathlib import PurePosixPath

from fastapi.staticfiles import StaticFiles


mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
IMAGE_CACHE_CONTROL = "public, max-age=86400"
REVALIDATE_CACHE_CONTROL = "public, max-age=0, must-revalidate"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = self._cache_control(path, scope)
        return response

    @staticmethod
    def _cache_control(path: str, scope) -> str:
        normalized_path = path.replace("\\", "/").lstrip("/")
        has_version_query = bool(scope.get("query_string", b""))

        if normalized_path.startswith("img/resources/") or has_version_query:
            return IMMUTABLE_CACHE_CONTROL

        if PurePosixPath(normalized_path).suffix.lower() in IMAGE_EXTENSIONS:
            return IMAGE_CACHE_CONTROL

        return REVALIDATE_CACHE_CONTROL
