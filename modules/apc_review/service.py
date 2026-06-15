from fastapi import HTTPException

from modules.apc_review import repository
from modules.apc_review.models import ApcReviewStatus

MAX_REVIEW_MESSAGE_LENGTH = 1200
VALID_STATUSES = {item.value for item in ApcReviewStatus}


def update_submission_review(
    *,
    submission_id: int,
    status: str,
    message: str,
    reviewer: dict,
) -> dict:
    submission = repository.get_submission(submission_id)
    if not submission:
        raise HTTPException(404, "Envio nao encontrado.")

    normalized_status = str(status or "").strip().upper()
    if normalized_status not in VALID_STATUSES:
        raise HTTPException(400, "Situacao de revisao invalida.")

    normalized_message = str(message or "").strip()
    if len(normalized_message) > MAX_REVIEW_MESSAGE_LENGTH:
        raise HTTPException(
            400,
            f"A orientacao deve ter no maximo {MAX_REVIEW_MESSAGE_LENGTH} caracteres.",
        )

    updated = repository.update_review(
        submission_id=submission_id,
        status=normalized_status,
        message=normalized_message,
        reviewer_user_id=int(reviewer["id"]),
    )
    if not updated:
        raise HTTPException(404, "Envio nao encontrado.")
    return updated
