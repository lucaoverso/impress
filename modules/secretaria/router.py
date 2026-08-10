from fastapi import APIRouter, Request

from routers.config import ASSET_VERSION, render_template_response


router = APIRouter(tags=["secretaria"])


def _render(request: Request, template: str, **context):
    return render_template_response(
        request,
        template,
        {"asset_version": ASSET_VERSION, **context},
        cache_control="no-store",
    )


@router.get("/secretaria")
def secretaria_page(request: Request):
    return _render(request, "secretaria.html")


@router.get("/secretaria/estudantes")
def secretaria_estudantes_page(request: Request):
    return _render(request, "coordenacao.html", secretaria_estudantes=True)


@router.get("/secretaria/horarios")
def secretaria_horarios_page(request: Request):
    return _render(request, "horario_escolar.html", secretaria_edicao=True)


def _render_admin_surface(request: Request, template: str, active_tab: str, title: str):
    return _render(
        request,
        template,
        admin_active_tab=active_tab,
        admin_page_title=title,
        secretaria_mode=True,
    )


@router.get("/secretaria/professores")
def secretaria_professores_page(request: Request):
    return _render_admin_surface(request, "admin/professores.html", "professores", "Professores")


@router.get("/secretaria/atribuicoes")
def secretaria_atribuicoes_page(request: Request):
    return _render_admin_surface(request, "admin/atribuicoes.html", "atribuicoes", "Atribuições docentes")


@router.get("/secretaria/turmas")
def secretaria_turmas_page(request: Request):
    return _render_admin_surface(request, "admin/turmas.html", "turmas", "Turmas e disciplinas")


@router.get("/secretaria/aulas")
def secretaria_aulas_page(request: Request):
    return _render_admin_surface(request, "admin/aulas.html", "aulas", "Configuração das aulas")
