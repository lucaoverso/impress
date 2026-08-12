from starlette.types import ASGIApp, Receive, Scope, Send


class BlogSubdomainMiddleware:
    """Mapeia URLs limpas do subdominio para as rotas internas /blog."""

    def __init__(self, app: ASGIApp, *, public_host: str):
        self.app = app
        self.public_host = str(public_host or "").strip().lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.public_host:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        host = headers.get(b"host", b"").decode("latin-1").split(":", 1)[0].lower()
        path = str(scope.get("path") or "/")
        if host != self.public_host or path.startswith(("/blog", "/static", "/health")):
            await self.app(scope, receive, send)
            return

        mapped_scope = dict(scope)
        mapped_path = "/blog/" if path == "/" else f"/blog{path}"
        mapped_scope["path"] = mapped_path
        mapped_scope["raw_path"] = mapped_path.encode("utf-8")
        await self.app(mapped_scope, receive, send)
