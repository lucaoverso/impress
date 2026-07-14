from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from routers.config import ASSET_VERSION, render_template_response

router = APIRouter()

PAGE_TITLES = {
    "professores": "Professores",
    "atribuicoes": "Atribuições docentes",
    "turmas": "Turmas e disciplinas",
    "aulas": "Cadastro de aulas",
    "recursos": "Recursos",
    "impressao": "Gestão de impressão",
    "relatorios": "Relatórios administrativos",
    "auditoria": "Atividades do sistema",
}

DEDICATED_TEMPLATES = {
    "aulas": "admin/aulas.html",
    "impressao": "admin/impressao.html",
    "recursos": "admin/recursos.html",
}


@router.get("/admin")
def admin_page():
    return RedirectResponse(url="/admin/professores", status_code=302)


def _render_admin_page(request: Request, active_tab: str):
    return render_template_response(
        request,
        DEDICATED_TEMPLATES.get(active_tab, "admin/index.html"),
        {
            "asset_version": ASSET_VERSION,
            "admin_active_tab": active_tab,
            "admin_page_title": PAGE_TITLES[active_tab],
        },
        cache_control="no-store",
    )


@router.get("/admin/professores")
def admin_professores_page(request: Request):
    return _render_admin_page(request, "professores")


@router.get("/admin/atribuicoes")
def admin_atribuicoes_page(request: Request):
    return _render_admin_page(request, "atribuicoes")


@router.get("/admin/turmas")
def admin_turmas_page(request: Request):
    return _render_admin_page(request, "turmas")


@router.get("/admin/aulas")
def admin_aulas_page(request: Request):
    return _render_admin_page(request, "aulas")


@router.get("/admin/recursos")
def admin_recursos_page(request: Request):
    return _render_admin_page(request, "recursos")


@router.get("/admin/impressao")
def admin_impressao_page(request: Request):
    return _render_admin_page(request, "impressao")


@router.get("/admin/relatorios")
def admin_relatorios_page(request: Request):
    return _render_admin_page(request, "relatorios")


@router.get("/admin/auditoria")
def admin_auditoria_page(request: Request):
    return _render_admin_page(request, "auditoria")
