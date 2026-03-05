from database import buscar_usuario_por_email, preencher_nt_hash_se_ausente
from services.auth_service import hash_senha


def ensure_nt_hash_for_radius(username: str, password: str) -> bool:
    login = str(username or "").strip().lower()
    senha = str(password or "")
    if not login or not senha:
        return False

    usuario = buscar_usuario_por_email(login)
    if not usuario:
        return False

    if hash_senha(senha) != usuario["senha_hash"]:
        return False

    preencher_nt_hash_se_ausente(int(usuario["id"]), senha)
    return True
