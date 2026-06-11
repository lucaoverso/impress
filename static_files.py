from pathlib import PurePosixPath
from urllib.parse import parse_qs

from fastapi.staticfiles import StaticFiles


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
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))

        if normalized_path.startswith("img/resources/") or query.get("v"):
            return IMMUTABLE_CACHE_CONTROL

        if PurePosixPath(normalized_path).suffix.lower() in IMAGE_EXTENSIONS:
            return IMAGE_CACHE_CONTROL

        return REVALIDATE_CACHE_CONTROL
