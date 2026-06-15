from pydantic import BaseModel, Field


class AuditEventOut(BaseModel):
    id: int
    category: str
    action: str
    outcome: str
    actor_user_id: int | None = None
    actor_name: str = ""
    actor_email: str = ""
    description: str
    entity_type: str = ""
    entity_id: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: str


class AuditEventPage(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int
    pages: int
