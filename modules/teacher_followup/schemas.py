from pydantic import BaseModel, Field

from .models import FollowupRecordType


class FollowupRecordCreate(BaseModel):
    teacher_id: int = Field(gt=0)
    record_type: FollowupRecordType
    category: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    record_date: str = Field(min_length=10, max_length=10)
