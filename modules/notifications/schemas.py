from pydantic import BaseModel, Field, field_validator


def _validate_action_url(value: str) -> str:
    normalized = str(value or "/").strip() or "/"
    if not normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError("O link deve ser interno e começar com uma única barra (/).")
    return normalized


class PushKeysIn(BaseModel):
    p256dh: str = Field(min_length=20, max_length=500)
    auth: str = Field(min_length=8, max_length=500)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2048)
    keys: PushKeysIn

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        endpoint = value.strip()
        if not endpoint.startswith("https://"):
            raise ValueError("O endpoint de push deve usar HTTPS.")
        return endpoint


class PushSubscriptionDeleteIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=2048)


class EstimateIn(BaseModel):
    audiences: list[str] = Field(default_factory=list, max_length=3)
    user_ids: list[int] = Field(default_factory=list, max_length=500)


class BatchCreateIn(EstimateIn):
    title: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=300)
    action_url: str = Field(default="/", max_length=500)
    priority: str = Field(default="normal")
    scheduled_at: str | None = None

    @field_validator("action_url")
    @classmethod
    def validate_action_url(cls, value: str) -> str:
        return _validate_action_url(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"normal", "urgent"}:
            raise ValueError("Prioridade inválida.")
        return normalized
