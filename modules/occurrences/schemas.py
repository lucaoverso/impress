from typing import Literal

from pydantic import BaseModel


ResponsibleContact = Literal["none", "communicate", "summon"]


class ReasonCreate(BaseModel):
    name: str


class ReasonUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class PreRegistrationCreate(BaseModel):
    student_id: int
    reason_id: int
    responsible_contact: ResponsibleContact


class PreRegistrationComplete(BaseModel):
    occurrence_id: int
