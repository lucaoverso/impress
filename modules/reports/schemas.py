from pydantic import BaseModel, Field


class TeacherReportEmailIn(BaseModel):
    destino_email: str | None = Field(default=None, max_length=255)
    assunto: str | None = Field(default=None, max_length=180)
    mensagem: str | None = Field(default=None, max_length=1200)
