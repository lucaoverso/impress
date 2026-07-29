import re
from datetime import datetime

from fastapi import HTTPException

from routers.common import normalizar_cargo_usuario, usuario_eh_professor, validar_senha_forte
from services.auth_service import hash_senha
from security.nt_hash import generate_nt_hash

from . import repository
from .schemas import ProfileUpdateIn

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+$")
DIAS_SEMANA = (
    ("SEGUNDA", "Segunda"),
    ("TERCA", "Terça"),
    ("QUARTA", "Quarta"),
    ("QUINTA", "Quinta"),
    ("SEXTA", "Sexta"),
)
APC_STATUS_LABELS = {
    "PENDENTE": "Aguardando revisão",
    "APROVADO": "Aprovado",
    "AJUSTES": "Precisa de ajustes",
    "REJEITADO": "Precisa de ajustes",
    "IMPRESSO": "Impresso",
}
PRINT_STATUS_LABELS = {
    "PENDENTE": "Aguardando",
    "AGUARDANDO": "Aguardando",
    "PROCESSANDO": "Processando",
    "IMPRIMINDO": "Imprimindo",
    "CONCLUIDO": "Pronto",
    "FINALIZADO": "Pronto",
    "CANCELADO": "Cancelado",
    "ERRO": "Não concluído",
    "FALHA": "Não concluído",
}


def update_own_profile(user: dict, payload: ProfileUpdateIn) -> None:
    name = " ".join(payload.nome.split())
    email = payload.email.strip().lower()
    password = payload.nova_senha.strip()

    if len(name) < 2:
        raise HTTPException(400, "Informe seu nome.")
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(400, "Informe um e-mail válido.")
    if repository.email_belongs_to_another_user(email, int(user["id"])):
        raise HTTPException(409, "Este e-mail já está em uso.")

    password_hash = None
    nt_hash = None
    if password:
        validar_senha_forte(password)
        password_hash = hash_senha(password)
        nt_hash = generate_nt_hash(password)

    if not repository.update_profile(
        int(user["id"]), name, email, password_hash=password_hash, nt_hash=nt_hash
    ):
        raise HTTPException(404, "Usuário não encontrado.")


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def _status(value, labels: dict[str, str], fallback: str) -> tuple[str, str]:
    status = _clean(value).upper() or fallback
    return status, labels.get(status, status.replace("_", " ").capitalize())


def _student_supports(rows: list[dict]) -> list[dict]:
    students: dict[int, dict] = {}
    support_seen: dict[int, set[str]] = {}
    recommendation_seen: dict[int, set[str]] = {}

    for row in rows:
        student_id = int(row.get("estudante_id") or 0)
        if student_id <= 0:
            continue
        student = students.setdefault(
            student_id,
            {
                "id": student_id,
                "nome": _clean(row.get("estudante_nome")),
                "turma_id": int(row.get("turma_id") or 0),
                "turma_nome": _clean(row.get("turma_nome")),
                "apoios": [],
                "recomendacoes": [],
            },
        )
        support_seen.setdefault(student_id, set())
        recommendation_seen.setdefault(student_id, set())

        support = _clean(row.get("apoio_nome"))
        if support and support.casefold() not in support_seen[student_id]:
            support_seen[student_id].add(support.casefold())
            student["apoios"].append(support)

        recommendation = _clean(row.get("recomendacoes_pedagogicas"))
        if recommendation and recommendation.casefold() not in recommendation_seen[student_id]:
            recommendation_seen[student_id].add(recommendation.casefold())
            student["recomendacoes"].append(recommendation)

    result = []
    for student in students.values():
        summary = ""
        if student["apoios"]:
            summary = ", ".join(student["apoios"][:2])
        elif student["recomendacoes"]:
            summary = student["recomendacoes"][0]
        else:
            summary = "Acompanhamento pedagógico registrado"
        result.append({**student, "resumo_apoio": summary})
    return result


def _identity(identity: dict, links: list[dict]) -> dict:
    return {
        "id": int(identity["id"]),
        "nome": _clean(identity.get("nome")),
        "email": _clean(identity.get("email")).lower(),
        "cargo": normalizar_cargo_usuario(identity),
        "data_nascimento": _clean(identity.get("data_nascimento")),
        "turmas": sorted(
            {_clean(item.get("turma_nome")) for item in links if _clean(item.get("turma_nome"))},
            key=str.casefold,
        ),
        "disciplinas": sorted(
            {
                _clean(item.get("disciplina_nome"))
                for item in links
                if _clean(item.get("disciplina_nome"))
            },
            key=str.casefold,
        ),
    }


def _teacher_dashboard(user_id: int, school_year: int, students: list[dict]) -> dict:
    support_class_ids = {int(item["turma_id"]) for item in students}
    schedule_items = [
        {
            "id": int(item["id"]),
            "dia_semana": _clean(item.get("dia_semana")).upper(),
            "aula_numero": int(item.get("aula_numero") or 0),
            "faixa_global": int(item.get("faixa_global") or item.get("aula_numero") or 0),
            "turma_id": int(item.get("turma_id") or 0),
            "turma_nome": _clean(item.get("turma_nome")),
            "turno": _clean(item.get("turno")).upper(),
            "disciplina_id": int(item.get("disciplina_id") or 0),
            "disciplina_nome": _clean(item.get("disciplina_nome")),
            "tem_estudante_apoio": int(item.get("turma_id") or 0) in support_class_ids,
        }
        for item in repository.list_teacher_schedule(user_id, school_year)
    ]
    slots = [
        {
            "aula_numero": int(item.get("aula_numero") or 0),
            "ordem_visual": int(item.get("ordem_visual") or 0),
            "nome": _clean(item.get("nome")) or f"{int(item.get('aula_numero') or 0)}ª aula",
            "horario_inicio": _clean(item.get("horario_inicio")),
            "horario_fim": _clean(item.get("horario_fim")),
        }
        for item in repository.list_schedule_slots()
    ]

    submissions = []
    for item in repository.list_recent_apc_submissions(user_id)[:3]:
        status, label = _status(item.get("status"), APC_STATUS_LABELS, "PENDENTE")
        submissions.append(
            {
                "id": int(item["id"]),
                "arquivo": _clean(item.get("arquivo")) or "Arquivo enviado",
                "turma_nome": _clean(item.get("turma_nome")),
                "disciplina_nome": _clean(item.get("disciplina_nome")),
                "enviado_em": _clean(item.get("enviado_em")),
                "status": status,
                "status_label": label,
            }
        )

    print_jobs = []
    for item in repository.list_recent_print_jobs(user_id)[:3]:
        status, label = _status(item.get("status"), PRINT_STATUS_LABELS, "PENDENTE")
        print_jobs.append(
            {
                "id": int(item["id"]),
                "arquivo": _clean(item.get("arquivo")) or "Arquivo sem nome",
                "copias": max(int(item.get("copias") or 0), 0),
                "paginas_totais": max(int(item.get("paginas_totais") or 0), 0),
                "criado_em": _clean(item.get("criado_em")),
                "status": status,
                "status_label": label,
            }
        )

    bookings = []
    for item in repository.list_upcoming_bookings(user_id)[:3]:
        status, label = _status(item.get("status"), {"ATIVO": "Confirmado"}, "ATIVO")
        bookings.append(
            {
                "id": int(item["id"]),
                "recurso_nome": _clean(item.get("recurso_nome")) or "Recurso",
                "recurso_tipo": _clean(item.get("recurso_tipo")),
                "data": _clean(item.get("data")),
                "aula": _clean(item.get("aula")),
                "horario_inicio": _clean(item.get("horario_inicio")),
                "horario_fim": _clean(item.get("horario_fim")),
                "turma": _clean(item.get("turma")),
                "tema_aula": _clean(item.get("tema_aula")),
                "status": status,
                "status_label": label,
            }
        )

    return {
        "horario": {
            "ano_letivo": int(school_year),
            "dias_semana": [{"id": key, "nome": label} for key, label in DIAS_SEMANA],
            "faixas": slots,
            "itens": schedule_items,
        },
        "estudantes": {"total": len(students), "itens": students[:3]},
        "envios_apc": submissions,
        "impressoes": print_jobs,
        "agendamentos": bookings,
    }


def get_own_profile_overview(user: dict, school_year: int | None = None) -> dict:
    user_id = int(user.get("id") or 0)
    identity = repository.get_profile_identity(user_id)
    if not identity:
        raise HTTPException(404, "Usuário não encontrado.")

    year = int(school_year or datetime.now().year)
    links = repository.list_teacher_links(user_id, year) if usuario_eh_professor(identity) else []
    payload = {"usuario": _identity(identity, links), "teacher_dashboard": None}
    if usuario_eh_professor(identity):
        students = _student_supports(repository.list_teacher_student_supports(user_id, year))
        payload["teacher_dashboard"] = _teacher_dashboard(user_id, year, students)
    return payload


def list_own_profile_students(user: dict, school_year: int | None = None) -> dict:
    if not usuario_eh_professor(user):
        raise HTTPException(403, "O acompanhamento pedagógico está disponível para professores.")
    user_id = int(user.get("id") or 0)
    year = int(school_year or datetime.now().year)
    students = _student_supports(repository.list_teacher_student_supports(user_id, year))
    return {"total": len(students), "itens": students}
