"""Pydantic schemas for pre-conselho APIs."""

from pydantic import BaseModel, Field


class PreConselhoPeriodoOut(BaseModel):
    id: int
    nome: str
    ano_letivo: int
    etapa: int
    data_inicio: str = ""
    data_fim: str = ""
    status: str = ""
    tem_rav: bool = False
    editavel: bool = False


class PreConselhoPeriodoCreateIn(BaseModel):
    nome: str = ""
    ano_letivo: int
    etapa: int
    data_inicio: str
    data_fim: str
    status: str = ""
    tem_rav: bool = False


class PreConselhoPeriodoUpdateIn(BaseModel):
    nome: str = ""
    ano_letivo: int
    etapa: int
    data_inicio: str
    data_fim: str
    tem_rav: bool = False


class PreConselhoPeriodoStatusIn(BaseModel):
    status: str


class PreConselhoMotivoOut(BaseModel):
    id: int
    categoria: str
    codigo: str
    descricao: str
    ativo: int | bool = True
    ordem: int = 0
    criado_em: str = ""
    atualizado_em: str = ""


class PreConselhoMotivoCreateIn(BaseModel):
    categoria: str
    codigo: str
    descricao: str
    ordem: int = 0


class PreConselhoMotivoUpdateIn(BaseModel):
    categoria: str
    descricao: str
    ordem: int = 0


class PreConselhoMotivoStatusIn(BaseModel):
    ativo: bool


class PreConselhoRavHabilidadeOut(BaseModel):
    id: int
    periodo_id: int | None = None
    periodo_nome: str = ""
    disciplina_id: int
    disciplina_nome: str = ""
    codigo: str = ""
    descricao: str
    turma_ids: list[int] = Field(default_factory=list)
    turmas: list[dict] = Field(default_factory=list)
    ativo: int | bool = True
    ordem: int = 0
    criado_em: str = ""
    atualizado_em: str = ""


class PreConselhoRavHabilidadeCreateIn(BaseModel):
    periodo_id: int
    disciplina_id: int
    codigo: str = ""
    descricao: str
    turma_ids: list[int] = Field(default_factory=list)
    ordem: int = 0


class PreConselhoRavHabilidadeUpdateIn(BaseModel):
    periodo_id: int
    disciplina_id: int
    codigo: str = ""
    descricao: str
    turma_ids: list[int] = Field(default_factory=list)
    ordem: int = 0


class PreConselhoRavHabilidadeStatusIn(BaseModel):
    ativo: bool


class PreConselhoRavHabilidadeJsonItemIn(BaseModel):
    codigo: str = ""
    texto: str = ""
    descricao: str = ""
    disciplina_id: int | None = None
    disciplina: str = ""
    periodo_id: int | None = None
    periodo: str = ""
    turma_ids: list[int] = Field(default_factory=list)
    turma: str = ""
    turmas: list[str] = Field(default_factory=list)
    ordem: int = 0


class PreConselhoRavHabilidadeImportIn(BaseModel):
    periodo_id: int | None = None
    periodo: str = ""
    habilidades: list[PreConselhoRavHabilidadeJsonItemIn] = Field(default_factory=list)


class PreConselhoRavHabilidadeImportOut(BaseModel):
    total_recebido: int = 0
    criadas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0
    erros: list[str] = Field(default_factory=list)


class PreConselhoTurmaOut(BaseModel):
    id: int
    nome: str
    turno: str = ""
    quantidade_estudantes: int = 0


class PreConselhoDisciplinaOut(BaseModel):
    id: int
    nome: str


class PreConselhoProfessorOut(BaseModel):
    id: int
    nome: str
    email: str = ""
    label: str = ""


class PreConselhoTurmaDisciplinaOut(BaseModel):
    turma_id: int
    turma_nome: str = ""
    turno: str = ""
    disciplina_id: int
    disciplina_nome: str = ""
    total_estudantes: int = 0
    total_sinalizados: int = 0
    total_pendentes: int = 0


class PreConselhoContextoOut(BaseModel):
    cargo: str = ""
    pode_configurar: bool = False
    pode_consolidar: bool = False
    pode_relatorio: bool = False
    pode_editar_periodo_fechado: bool = False
    professor_id: int | None = None
    professor_nome: str = ""
    periodos: list[PreConselhoPeriodoOut] = Field(default_factory=list)
    turmas: list[PreConselhoTurmaOut] = Field(default_factory=list)
    disciplinas: list[PreConselhoDisciplinaOut] = Field(default_factory=list)
    motivos: list[PreConselhoMotivoOut] = Field(default_factory=list)
    rav_habilidades: list[PreConselhoRavHabilidadeOut] = Field(default_factory=list)
    professores: list[PreConselhoProfessorOut] = Field(default_factory=list)
    niveis_atencao: list[dict] = Field(default_factory=list)
    motivos_pos_preconselho: dict[str, list[dict[str, str]]] = Field(default_factory=dict)
    minhas_turmas_disciplinas: list[PreConselhoTurmaDisciplinaOut] = Field(default_factory=list)


class PreConselhoEstudantePainelOut(BaseModel):
    estudante_id: int
    nome: str
    turma_id: int
    turma_nome: str = ""
    sinalizado: bool = False
    registro_id: int | None = None
    nivel_atencao: str = ""
    observacao_professor: str = ""
    texto_gerado: str = ""
    motivo_ids: list[int] = Field(default_factory=list)
    motivos: list[PreConselhoMotivoOut] = Field(default_factory=list)
    pos_preconselho_recuperado: bool | None = None
    pos_preconselho_motivo_ids: list[str] = Field(default_factory=list)
    pos_preconselho_motivos: list[str] = Field(default_factory=list)
    pos_preconselho_observacao: str = ""
    estudante_em_rav: bool = False
    rav_habilidade_ids: list[int] = Field(default_factory=list)
    rav_habilidades: list[PreConselhoRavHabilidadeOut] = Field(default_factory=list)
    rav_acoes: str = ""


class PreConselhoRegistroSaveIn(BaseModel):
    periodo_id: int
    turma_id: int
    disciplina_id: int
    estudante_id: int
    sinalizar: bool = True
    motivo_ids: list[int] = Field(default_factory=list)
    observacao_professor: str = ""
    nivel_atencao: str | None = None
    pos_preconselho_recuperado: bool | None = None
    pos_preconselho_motivo_ids: list[str] = Field(default_factory=list)
    pos_preconselho_observacao: str = ""
    estudante_em_rav: bool = False
    rav_habilidade_ids: list[int] = Field(default_factory=list)
    rav_acoes: str = ""
    professor_id: int | None = None


class PreConselhoTextoPreviewIn(BaseModel):
    motivo_ids: list[int] = Field(default_factory=list)
    observacao_professor: str = ""
    nivel_atencao: str | None = None
    estudante_nome: str = ""
    periodo_id: int | None = None
    turma_id: int | None = None
    disciplina_id: int | None = None
    disciplina_nome: str = ""
    pos_preconselho_recuperado: bool | None = None
    pos_preconselho_motivo_ids: list[str] = Field(default_factory=list)
    pos_preconselho_observacao: str = ""
    estudante_em_rav: bool = False
    rav_habilidade_ids: list[int] = Field(default_factory=list)
    rav_acoes: str = ""


class PreConselhoRegistroOut(BaseModel):
    id: int
    periodo_id: int | None = None
    periodo_nome: str = ""
    ano_letivo: int = 0
    etapa: int = 0
    professor_nome: str = ""
    professor_id: int
    turma_id: int
    turma_nome: str = ""
    disciplina_id: int | None = None
    disciplina_nome: str = ""
    estudante_id: int
    estudante_nome: str = ""
    nivel_atencao: str = ""
    observacao_professor: str = ""
    criado_em: str = ""
    atualizado_em: str = ""
    texto_gerado: str = ""
    motivo_ids: list[int] = Field(default_factory=list)
    motivos: list[PreConselhoMotivoOut] = Field(default_factory=list)
    pos_preconselho_recuperado: bool | None = None
    pos_preconselho_motivo_ids: list[str] = Field(default_factory=list)
    pos_preconselho_motivos: list[str] = Field(default_factory=list)
    pos_preconselho_observacao: str = ""
    estudante_em_rav: bool = False
    rav_habilidade_ids: list[int] = Field(default_factory=list)
    rav_habilidades: list[PreConselhoRavHabilidadeOut] = Field(default_factory=list)
    rav_acoes: str = ""
    editavel: bool = False


class PreConselhoRegistrosOut(BaseModel):
    total_registros: int = 0
    itens: list[PreConselhoRegistroOut] = Field(default_factory=list)


class PreConselhoTextoOut(BaseModel):
    texto: str = ""
    fragmentos: list[str] = Field(default_factory=list)


class PreConselhoConsolidadoEstudanteOut(BaseModel):
    estudante_id: int = 0
    estudante_nome: str = ""
    turma_nome: str = ""
    nivel_atencao: str = ""
    total_registros: int = 0
    disciplinas: list[str] = Field(default_factory=list)
    motivos: list[str] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)
    professores: list[str] = Field(default_factory=list)
    estudante_em_rav: bool = False
    texto: str = ""


class PreConselhoConsolidadoOut(BaseModel):
    periodo_id: int | None = None
    periodo_nome: str = ""
    turma_id: int | None = None
    turma_nome: str = ""
    disciplina_id: int | None = None
    disciplina_nome: str = ""
    professor_id: int | None = None
    professor_nome: str = ""
    total_registros: int = 0
    total_estudantes: int = 0
    motivos_frequentes: list[str] = Field(default_factory=list)
    texto: str = ""
    itens_agrupados: list[PreConselhoConsolidadoEstudanteOut] = Field(default_factory=list)
    itens: list[PreConselhoRegistroOut] = Field(default_factory=list)


class PreConselhoRelatorioItemOut(BaseModel):
    id: int | None = None
    nome: str = ""
    total_registros: int = 0
    extra: str = ""


class PreConselhoRelatorioTurmaOut(BaseModel):
    turma_id: int
    turma_nome: str = ""
    turno: str = ""
    quantidade_estudantes: int = 0
    total_registros: int = 0
    total_estudantes_sinalizados: int = 0
    professor_destaque: PreConselhoRelatorioItemOut = Field(
        default_factory=PreConselhoRelatorioItemOut
    )
    estudantes_destaque: list[PreConselhoRelatorioItemOut] = Field(default_factory=list)
    professores_relacionados: list[PreConselhoRelatorioItemOut] = Field(default_factory=list)
    motivos_frequentes: list[PreConselhoRelatorioItemOut] = Field(default_factory=list)
    pontos_atencao: list[str] = Field(default_factory=list)


class PreConselhoRelatorioOut(BaseModel):
    periodo_id: int | None = None
    periodo_nome: str = ""
    total_registros: int = 0
    total_estudantes_sinalizados: int = 0
    total_turmas_com_registros: int = 0
    total_professores_com_registros: int = 0
    turma_destaque: PreConselhoRelatorioItemOut = Field(default_factory=PreConselhoRelatorioItemOut)
    professor_destaque: PreConselhoRelatorioItemOut = Field(
        default_factory=PreConselhoRelatorioItemOut
    )
    motivos_frequentes: list[PreConselhoRelatorioItemOut] = Field(default_factory=list)
    pontos_criticos: list[str] = Field(default_factory=list)
    estudantes_destaque: list[PreConselhoRelatorioItemOut] = Field(default_factory=list)
    turmas: list[PreConselhoRelatorioTurmaOut] = Field(default_factory=list)


class PreConselhoRavTurmaOut(BaseModel):
    periodo_id: int | None = None
    turma_id: int | None = None
    total_estudantes: int = 0
    total_registros: int = 0
    itens: list[PreConselhoRegistroOut] = Field(default_factory=list)
