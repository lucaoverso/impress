from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from routers.config import render_template_response

from . import service
from .config import BLOG_PUBLIC_HOST, BLOG_PUBLIC_URL
from .public_content import sanitize_public_html


router = APIRouter(prefix="/blog", tags=["Blog público"])

_MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _uses_public_host(request: Request) -> bool:
    host = request.headers.get("host", "").split(":", 1)[0].lower().rstrip(".")
    return bool(BLOG_PUBLIC_HOST) and host == BLOG_PUBLIC_HOST


def _base_path(request: Request) -> str:
    return "" if _uses_public_host(request) else "/blog"


def _mark_page_indexing(response: Response, request: Request, *, index: bool = True) -> Response:
    if not index or not _uses_public_host(request):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _date_label(value) -> str:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    return f"{parsed.day} de {_MONTHS[parsed.month - 1]} de {parsed.year}"


def _public_post_summary(post: dict, *, base_path: str) -> dict:
    cover_token = str(post.get("cover_token") or "")
    return {
        **post,
        "published_label": _date_label(post.get("published_at")),
        "article_url": f"{base_path}/artigos/{post['slug']}",
        "cover_url": f"{base_path}/images/{cover_token}" if cover_token else "",
        "cover_thumbnail_url": (
            f"{base_path}/images/{cover_token}?thumbnail=true" if cover_token else ""
        ),
    }


def _all_public_posts() -> list[dict]:
    posts: list[dict] = []
    offset = 0
    while True:
        batch = service.list_public_posts(limit=50, offset=offset)
        posts.extend(batch)
        if len(batch) < 50:
            return posts
        offset += len(batch)


def _last_modified(value) -> str:
    text = str(value or "").strip().replace(" ", "T")
    return f"{text}Z" if text and not text.endswith(("Z", "+00:00")) else text


@router.get("/", include_in_schema=False)
def public_blog_home(request: Request):
    base_path = _base_path(request)
    posts = [
        _public_post_summary(post, base_path=base_path)
        for post in service.list_public_posts(limit=30)
    ]
    response = render_template_response(
        request,
        "blog/index.html",
        {
            "posts": posts,
            "featured_post": posts[0] if posts else None,
            "remaining_posts": posts[1:],
            "blog_base_path": base_path,
            "canonical_url": f"{BLOG_PUBLIC_URL}/",
            "page_title": "Blog da Escola",
            "page_description": "Noticias, projetos e historias da nossa comunidade escolar.",
        },
        cache_control="public, max-age=60, stale-while-revalidate=300",
    )
    return _mark_page_indexing(response, request)


@router.get("/artigos/{slug}", include_in_schema=False)
def public_blog_article(request: Request, slug: str):
    base_path = _base_path(request)
    try:
        post = service.get_public_post(slug)
    except service.BlogNotFoundError:
        response = render_template_response(
            request,
            "blog/404.html",
            {
                "blog_base_path": base_path,
                "canonical_url": f"{BLOG_PUBLIC_URL}/",
                "page_title": "Artigo não encontrado",
                "page_description": "Este artigo não está disponível.",
            },
            cache_control="public, max-age=60",
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return _mark_page_indexing(response, request, index=False)

    view = _public_post_summary(post, base_path=base_path)
    view["body_public_html"] = sanitize_public_html(
        str(post.get("body_html") or ""),
        image_base_path=f"{base_path}/images",
        images=post.get("images") or [],
    )
    canonical_url = f"{BLOG_PUBLIC_URL}/artigos/{post['slug']}"
    response = render_template_response(
        request,
        "blog/article.html",
        {
            "post": view,
            "blog_base_path": base_path,
            "canonical_url": canonical_url,
            "page_title": str(post.get("title") or "Blog da Escola"),
            "page_description": str(post.get("summary") or ""),
            "og_image_url": (
                f"{BLOG_PUBLIC_URL}/images/{post['cover_token']}"
                if post.get("cover_token")
                else ""
            ),
        },
        cache_control="public, max-age=60, stale-while-revalidate=300",
    )
    return _mark_page_indexing(response, request)


@router.get("/robots.txt", include_in_schema=False)
def public_blog_robots():
    content = "\n".join(
        (
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /api/",
            f"Sitemap: {BLOG_PUBLIC_URL}/sitemap.xml",
            "",
        )
    )
    return Response(
        content,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/sitemap.xml", include_in_schema=False)
def public_blog_sitemap():
    entries = [f"  <url><loc>{escape(BLOG_PUBLIC_URL)}/</loc></url>"]
    for post in _all_public_posts():
        location = escape(f"{BLOG_PUBLIC_URL}/artigos/{post['slug']}")
        last_modified = escape(_last_modified(post.get("updated_at")))
        lastmod = f"<lastmod>{last_modified}</lastmod>" if last_modified else ""
        entries.append(f"  <url><loc>{location}</loc>{lastmod}</url>")
    content = "\n".join(
        ('<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
         *entries, "</urlset>", "")
    )
    return Response(
        content,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/images/{token}", include_in_schema=False)
def public_blog_image(request: Request, token: str, thumbnail: bool = Query(default=False)):
    try:
        resolved = service.resolve_image(token, public=True, thumbnail=thumbnail)
    except service.BlogNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Disposition": f'inline; filename="{resolved["filename"]}"',
    }
    if not _uses_public_host(request):
        headers["X-Robots-Tag"] = "noindex, noimageindex"
    return FileResponse(
        resolved["path"],
        media_type=resolved["media_type"],
        headers=headers,
    )
