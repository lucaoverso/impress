"""Domain entities for pre-conselho."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class PreConselhoPeriodo:
    id: int
    nome: str
    ano_letivo: int
    etapa: int
    data_inicio: str = ""
    data_fim: str = ""
    status: str = ""


@dataclass(slots=True)
class PreConselhoMotivo:
    id: int
    categoria: str
    codigo: str
    descricao: str
    ativo: bool = True
    ordem: int = 0


@dataclass(slots=True)
class PreConselhoRegistro:
    id: int
    periodo_id: int | None
    professor_id: int
    turma_id: int
    disciplina_id: int | None
    estudante_id: int
    nivel_atencao: str = ""
    observacao_professor: str = ""
    texto_gerado: str = ""
    motivo_ids: list[int] = field(default_factory=list)
