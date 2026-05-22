from typing import Literal

from pydantic import BaseModel, Field


TipoAcaoPcpi = Literal[
    "reuniao",
    "orientacao",
    "rede_social",
    "registro",
    "impressao",
    "adequacao_impressao",
    "projeto",
    "gremio",
    "colaboracao",
    "evento",
    "planejamento",
    "formulario2",
]


class PcpiRegistroManualIn(BaseModel):
    data: str
    turno: str
    tipo_acao: TipoAcaoPcpi
    professor_nome: str = ""
    componente: str = ""
    turma: str = ""
    descricao_curta: str
    observacoes: str = ""


class PcpiRegistroManualOut(BaseModel):
    id: int
    data: str
    turno: str
    tipo_acao: str
    professor_nome: str = ""
    componente: str = ""
    turma: str = ""
    descricao_curta: str
    observacoes: str = ""
    criado_por_usuario_id: int | None = None
    atualizado_por_usuario_id: int | None = None
    criado_em: str = ""
    atualizado_em: str = ""


class PcpiRegistrosManuaisOut(BaseModel):
    data: str
    turno: str
    turno_nome: str = ""
    total_registros: int = 0
    itens: list[PcpiRegistroManualOut] = Field(default_factory=list)


class PcpiSugestaoAutomaticaOut(BaseModel):
    agendamento_id: int
    data: str
    turno: str
    turno_nome: str = ""
    aula: str
    faixa_global: int = 0
    recurso_id: int
    recurso_nome: str
    recurso_tipo: str = ""
    professor_id: int
    professor_nome: str
    componentes: list[str] = Field(default_factory=list)
    turma: str = ""
    tema_aula: str = ""
    observacao: str = ""
    categoria_uso: str = ""


class PcpiResumoAutomaticoOut(BaseModel):
    total_agendamentos: int = 0
    total_professores: int = 0
    total_turmas: int = 0
    recursos: list[str] = Field(default_factory=list)
    categorias_uso: list[str] = Field(default_factory=list)


class PcpiSugestoesOut(BaseModel):
    data: str
    turno: str
    turno_nome: str = ""
    resumo: PcpiResumoAutomaticoOut = Field(default_factory=PcpiResumoAutomaticoOut)
    itens: list[PcpiSugestaoAutomaticaOut] = Field(default_factory=list)
    texto_base: str = ""


class PcpiTextoGeradoOut(BaseModel):
    data: str
    turno: str
    turno_nome: str = ""
    total_agendamentos: int = 0
    total_registros_manuais: int = 0
    frases_automaticas: list[str] = Field(default_factory=list)
    frases_manuais: list[str] = Field(default_factory=list)
    frase_fechamento: str = ""
    texto: str = ""


class PcpiTextoPreviewIn(BaseModel):
    data: str
    turno: str
    agendamento_ids: list[int] | None = None


__all__ = [
    "TipoAcaoPcpi",
    "PcpiRegistroManualIn",
    "PcpiRegistroManualOut",
    "PcpiRegistrosManuaisOut",
    "PcpiSugestaoAutomaticaOut",
    "PcpiResumoAutomaticoOut",
    "PcpiSugestoesOut",
    "PcpiTextoGeradoOut",
    "PcpiTextoPreviewIn",
]
