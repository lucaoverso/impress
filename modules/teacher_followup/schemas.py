from pydantic import BaseModel, Field

from .models import FollowupMode, FollowupRecordType, FollowupTargetRole


class FollowupRecordCreate(BaseModel):
    teacher_id: int = Field(gt=0)
    criterion_id: int = Field(gt=0)
    record_type: FollowupRecordType
    description: str = Field(min_length=1, max_length=2000)
    record_date: str = Field(min_length=10, max_length=10)


class FollowupDimensionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    active: bool = True


class FollowupCriterionCreate(BaseModel):
    dimension_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    record_type: FollowupRecordType
    mode: FollowupMode = FollowupMode.MANUAL
    target_role: FollowupTargetRole = FollowupTargetRole.TEACHER
    active: bool = True


class FollowupCriterionUpdate(BaseModel):
    dimension_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    record_type: FollowupRecordType
    mode: FollowupMode = FollowupMode.MANUAL
    target_role: FollowupTargetRole = FollowupTargetRole.TEACHER
    active: bool = True


class FollowupModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_role: FollowupTargetRole = FollowupTargetRole.TEACHER
    description: str = Field(default="", max_length=500)
    criterion_ids: list[int] = Field(default_factory=list)
    active: bool = True
