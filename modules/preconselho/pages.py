"""Rendered pages for the pre-conselho module."""

from fastapi import APIRouter, Request

from routers.config import ASSET_VERSION, render_template_response

router = APIRouter()


def _render_page(request: Request, page: str):
    return render_template_response(
        request,
        "preconselho/index.html",
        {"asset_version": ASSET_VERSION, "preconselho_page": page},
        cache_control="no-store",
    )


@router.get("/preconselho")
def preconselho_page(request: Request):
    return _render_page(request, "docente")


@router.get("/preconselho/consolidacao")
def preconselho_consolidation_page(request: Request):
    return _render_page(request, "consolidacao")


@router.get("/preconselho/reavaliacao")
def preconselho_review_page(request: Request):
    return _render_page(request, "reavaliacao")


@router.get("/preconselho/relatorios")
def preconselho_report_page(request: Request):
    return _render_page(request, "relatorio")


@router.get("/preconselho/rav")
def preconselho_rav_page(request: Request):
    return _render_page(request, "rav")


@router.get("/preconselho/configuracoes")
def preconselho_settings_page(request: Request):
    return _render_page(request, "configuracoes")
