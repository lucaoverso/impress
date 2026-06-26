from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .config import ASSET_VERSION, PRINT_CANCEL_WINDOW_SECONDS, render_template_response

router = APIRouter()


@router.get("/login-page")
def login_page(request: Request):
    return render_template_response(
        request,
        "login.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/servicos")
def servicos_page(request: Request):
    return render_template_response(
        request,
        "servicos.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/impressao")
def impressao_page(request: Request):
    return render_template_response(
        request,
        "professor.html",
        {
            "cancel_window_seconds": PRINT_CANCEL_WINDOW_SECONDS,
            "asset_version": ASSET_VERSION,
        },
        cache_control="no-store",
    )


@router.get("/professor")
def professor_redirect():
    return RedirectResponse(url="/impressao", status_code=302)


@router.get("/agendamento")
def agendamento_page(request: Request):
    return render_template_response(
        request,
        "agendamento.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/relatorios")
def relatorios_page(request: Request):
    return render_template_response(
        request,
        "relatorios.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/download")
def download_page(request: Request):
    return render_template_response(
        request,
        "download.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/download/detalhes")
def download_details_page(request: Request):
    return render_template_response(
        request,
        "download.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/pcpi")
def pcpi_page(request: Request):
    return render_template_response(
        request,
        "pcpi.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/preconselho")
def preconselho_page(request: Request):
    return render_template_response(
        request,
        "preconselho.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/cadastro-professor")
def cadastro_professor_page(request: Request):
    return render_template_response(
        request,
        "cadastro_professor.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/admin")
def admin_page(request: Request):
    return render_template_response(
        request,
        "admin.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/coordenacao")
def coordenacao_page(request: Request):
    return render_template_response(
        request,
        "coordenacao/index.html",
        {
            "asset_version": ASSET_VERSION,
        },
        cache_control="no-store",
    )


@router.get("/coordenacao/ocorrencias/nova")
def coordenacao_nova_ocorrencia_page(request: Request):
    return render_template_response(
        request,
        "coordenacao/nova-ocorrencia.html",
        {
            "asset_version": ASSET_VERSION,
        },
        cache_control="no-store",
    )


@router.get("/horario-escolar")
def horario_escolar_page(request: Request):
    return render_template_response(
        request,
        "horario_escolar.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )


@router.get("/apc")
def apc_page(request: Request):
    return render_template_response(
        request,
        "apc.html",
        {"asset_version": ASSET_VERSION},
        cache_control="no-store",
    )
