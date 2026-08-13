from starlette.datastructures import MutableHeaders
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_BLOG_CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; "
    "frame-ancestors 'none'; form-action 'self'"
)


class BlogSubdomainMiddleware:
    """Mapeia URLs limpas do subdominio para as rotas internas /blog."""

    def __init__(self, app: ASGIApp, *, public_host: str):
        self.app = app
        self.public_host = str(public_host or "").strip().lower().rstrip(".")

    @staticmethod
    def _request_host(scope: Scope) -> str:
        headers = dict(scope.get("headers") or [])
        return headers.get(b"host", b"").decode("latin-1").split(":", 1)[0].lower().rstrip(".")

    @staticmethod
    def _clean_blog_url(scope: Scope, path: str) -> str:
        clean_path = path.removeprefix("/blog") or "/"
        query = bytes(scope.get("query_string") or b"").decode("latin-1")
        return f"{clean_path}?{query}" if query else clean_path

    @staticmethod
    def _secure_send(scope: Scope, send: Send):
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Content-Security-Policy"] = _BLOG_CSP
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                if scope.get("scheme") == "https":
                    headers["Strict-Transport-Security"] = "max-age=31536000"
            await send(message)

        return send_with_headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.public_host:
            await self.app(scope, receive, send)
            return

        host = self._request_host(scope)
        path = str(scope.get("path") or "/")
        if host != self.public_host:
            await self.app(scope, receive, send)
            return

        secure_send = self._secure_send(scope, send)
        if path == "/blog" or path.startswith("/blog/"):
            response = RedirectResponse(self._clean_blog_url(scope, path), status_code=308)
            await response(scope, receive, secure_send)
            return
        if path == "/health" or path == "/static" or path.startswith("/static/"):
            await self.app(scope, receive, secure_send)
            return

        mapped_scope = dict(scope)
        mapped_path = "/blog/" if path == "/" else f"/blog{path}"
        mapped_scope["path"] = mapped_path
        mapped_scope["raw_path"] = mapped_path.encode("utf-8")
        await self.app(mapped_scope, receive, secure_send)
