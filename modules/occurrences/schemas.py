from typing import Literal

from pydantic import BaseModel


ResponsibleContact = Literal["none", "communicate", "summon"]


class ReasonCreate(BaseModel):
    name: str


class ReasonUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class PreRegistrationCreate(BaseModel):
    student_ids: list[int]
    reason_ids: list[int]
    responsible_contact: ResponsibleContact
    discipline: str | None = None
    complementary_report: str | None = None


class PreRegistrationComplete(BaseModel):
    occurrence_id: int
