from typing import Literal
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    copias: int


class JobOut(BaseModel):
    id: int
    arquivo: str
    copias: int
    status: str
    prioridade: int
    criado_em: str


class FilaOut(BaseModel):
    jobs: list[JobOut]


class LoginIn(BaseModel):
    email: str
    senha: str


class ProfessorRecuperarSenhaIn(BaseModel):
    email: str
    data_nascimento: str
    nova_senha: str


class ProfessorRedefinirSenhaAdminIn(BaseModel):
    nova_senha: str


class RadiusEnsureNtHashIn(BaseModel):
    username: str
    password: str


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    perfil: str
    cargo: str = ""


class AgendamentoIn(BaseModel):
    recurso_id: int
    data: str
    aula: str
    turma: str
    tema_aula: str
    professor_id: int | None = None
    observacao: str = ""


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


class PreConselhoPeriodoOut(BaseModel):
    id: int
    nome: str
    ano_letivo: int
    etapa: int
    data_inicio: str = ""
    data_fim: str = ""
    status: str = ""
    editavel: bool = False


class PreConselhoPeriodoCreateIn(BaseModel):
    nome: str = ""
    ano_letivo: int
    etapa: int
    data_inicio: str
    data_fim: str
    status: str = ""


class PreConselhoPeriodoUpdateIn(BaseModel):
    nome: str = ""
    ano_letivo: int
    etapa: int
    data_inicio: str
    data_fim: str


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
    professor_id: int | None = None


class PreConselhoTextoPreviewIn(BaseModel):
    motivo_ids: list[int] = Field(default_factory=list)
    observacao_professor: str = ""
    nivel_atencao: str | None = None
    estudante_nome: str = ""
    disciplina_nome: str = ""
    pos_preconselho_recuperado: bool | None = None
    pos_preconselho_motivo_ids: list[str] = Field(default_factory=list)
    pos_preconselho_observacao: str = ""


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


class ProfessorCreateIn(BaseModel):
    nome: str
    email: str
    senha: str
    data_nascimento: str
    aulas_semanais: int = 0
    turmas: list[str] = Field(default_factory=list)
    disciplinas: list[str] = Field(default_factory=list)
    acesso_coordenacao: bool = False


class ProfessorUpdateIn(BaseModel):
    nome: str
    email: str
    data_nascimento: str
    aulas_semanais: int = 0
    turmas: list[str] = Field(default_factory=list)
    disciplinas: list[str] = Field(default_factory=list)
    acesso_coordenacao: bool = False


class CoordenadorCreateIn(BaseModel):
    nome: str
    email: str
    senha: str
    data_nascimento: str


class ProfessorCargaIn(BaseModel):
    aulas_semanais: int
    turmas_quantidade: int


class ProfessorTurmaDisciplinaCreateIn(BaseModel):
    professor_id: int
    turma_id: int
    disciplina_id: int


class ProfessorDisciplinaTurmasSyncIn(BaseModel):
    professor_id: int
    disciplina_id: int
    turma_ids: list[int] = Field(default_factory=list)


class ProfessorTurmaDisciplinaOut(BaseModel):
    id: int
    professor_id: int
    professor_nome: str = ""
    professor_email: str = ""
    professor_ativo: bool = True
    turma_id: int
    turma_nome: str = ""
    turno: str = ""
    turma_ativa: bool = True
    disciplina_id: int
    disciplina_nome: str = ""
    disciplina_ativa: bool = True
    criado_em: str = ""


class TurmaDisciplinaCreateIn(BaseModel):
    turma_id: int
    disciplina_id: int | None = None
    disciplina_nome: str = ""
    carga_horaria: int = 0
    professor_id: int | None = None


class TurmaDisciplinaUpdateIn(BaseModel):
    carga_horaria: int
    professor_id: int | None = None


class TurmaDisciplinaOut(BaseModel):
    id: int
    turma_id: int
    turma_nome: str = ""
    turno: str = ""
    turma_ativa: bool = True
    disciplina_id: int
    disciplina_nome: str = ""
    disciplina_ativa: bool = True
    carga_horaria: int = 0
    carga_horaria_padrao: int = 0
    professor_id: int | None = None
    professor_nome: str = ""
    professor_email: str = ""
    professor_ativo: bool = True
    criado_em: str = ""
    atualizado_em: str = ""


class HorarioEscolarRegistroIn(BaseModel):
    ano_letivo: int
    turma_id: int
    disciplina_id: int
    professor_id: int
    dia_semana: str
    aula_numero: int


class HorarioEscolarRegistroUpdateIn(BaseModel):
    ano_letivo: int
    turma_id: int
    disciplina_id: int
    professor_id: int
    dia_semana: str
    aula_numero: int


class HorarioEscolarRegistroOut(BaseModel):
    id: int
    ano_letivo: int
    turma_id: int
    turma_nome: str = ""
    turno: str = ""
    disciplina_id: int
    disciplina_nome: str = ""
    professor_id: int
    professor_nome: str = ""
    professor_email: str = ""
    dia_semana: str
    dia_semana_nome: str = ""
    aula_numero: int
    criado_em: str = ""
    atualizado_em: str = ""


class TurmaCreateIn(BaseModel):
    nome: str
    turno: str
    quantidade_estudantes: int = 0


class TurmaUpdateIn(BaseModel):
    turno: str
    quantidade_estudantes: int


class DisciplinaCreateIn(BaseModel):
    nome: str
    aulas_semanais: int = 0


class DisciplinaUpdateIn(BaseModel):
    aulas_semanais: int


class RecursoCreateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1


class RecursoUpdateIn(BaseModel):
    nome: str
    tipo: str
    descricao: str = ""
    quantidade_itens: int = 1


class RecursoStatusIn(BaseModel):
    ativo: bool


class RegrasCotaIn(BaseModel):
    base_paginas: int
    paginas_por_aula: int
    paginas_por_turma: int
    cota_mensal_escola: int


class LeiCreateIn(BaseModel):
    nome: str


class LeiUpdateIn(BaseModel):
    nome: str


class LeiOut(BaseModel):
    id: int
    nome: str
    label: str = ""


class ArtigoCreateIn(BaseModel):
    lei_id: int
    numero: str
    descricao: str


class ArtigoUpdateIn(BaseModel):
    lei_id: int
    numero: str
    descricao: str


class ArtigoOut(BaseModel):
    id: int
    lei_id: int
    lei_nome: str = ""
    numero: str
    descricao: str
    referencia: str = ""
    label: str = ""


class IncisoCreateIn(BaseModel):
    artigo_id: int
    numero: str
    descricao: str


class IncisoUpdateIn(BaseModel):
    artigo_id: int
    numero: str
    descricao: str


class IncisoOut(BaseModel):
    id: int
    artigo_id: int
    lei_id: int | None = None
    lei_nome: str = ""
    artigo_numero: str = ""
    artigo_descricao: str = ""
    numero: str
    descricao: str
    referencia: str = ""
    label: str = ""


class AlineaCreateIn(BaseModel):
    inciso_id: int
    identificador: str
    descricao: str


class AlineaUpdateIn(BaseModel):
    inciso_id: int
    identificador: str
    descricao: str


class AlineaOut(BaseModel):
    id: int
    inciso_id: int
    artigo_id: int | None = None
    lei_id: int | None = None
    lei_nome: str = ""
    artigo_numero: str = ""
    inciso_numero: str = ""
    inciso_descricao: str = ""
    identificador: str
    descricao: str
    referencia: str = ""
    label: str = ""


class RegimentoItemCreateIn(BaseModel):
    lei_nome: str | None = None
    artigo_numero: str | None = None
    artigo_descricao: str | None = None
    inciso_numero: str | None = None
    inciso_descricao: str | None = None
    alinea_identificador: str | None = None
    alinea_descricao: str | None = None
    artigo: str | None = None
    descricao: str | None = None


class RegimentoItemUpdateIn(BaseModel):
    lei_nome: str | None = None
    artigo_numero: str | None = None
    artigo_descricao: str | None = None
    inciso_numero: str | None = None
    inciso_descricao: str | None = None
    alinea_identificador: str | None = None
    alinea_descricao: str | None = None
    artigo: str | None = None
    descricao: str | None = None
    ativo: bool = True


class RegimentoItemStatusIn(BaseModel):
    ativo: bool


class RegimentoItemOut(BaseModel):
    id: int
    tipo: str | None = None
    lei_id: int | None = None
    lei_nome: str | None = None
    artigo_id: int | None = None
    artigo_numero: str | None = None
    artigo_descricao: str | None = None
    inciso_id: int | None = None
    inciso_numero: str | None = None
    inciso_descricao: str | None = None
    alinea_id: int | None = None
    alinea_identificador: str | None = None
    alinea_descricao: str | None = None
    artigo: str
    descricao: str
    ativo: int | bool = True
    criado_em: str = ""
    atualizado_em: str = ""


class RegimentoItemOcorrenciaOut(BaseModel):
    regimento_item_id: int | None = None
    tipo: str | None = None
    artigo_id: int | None = None
    inciso_id: int | None = None
    alinea_id: int | None = None
    lei_nome: str | None = None
    artigo_numero: str | None = None
    artigo_descricao: str | None = None
    inciso_numero: str | None = None
    inciso_descricao: str | None = None
    alinea_identificador: str | None = None
    alinea_descricao: str | None = None
    artigo: str
    descricao: str
    ordem: int = 0


AcaoAplicadaOcorrencia = Literal[
    "advertencia_verbal",
    "retirada_sala_orientacao",
    "suspensao_extracurricular",
    "suspensao_orientada_2_dias",
    "suspensao_aulas_3_dias",
    "transferencia_compulsoria",
    "orientacao_verbal",
    "advertencia",
    "chamada_responsavel",
    "encaminhamento_direcao",
    "registro_informativo",
]

StatusOcorrencia = Literal[
    "registrado",
    "em_acompanhamento",
    "aguardando_responsavel",
    "resolvido",
]


class OcorrenciaCreateIn(BaseModel):
    nome_estudante: str | None = None
    estudante_id: int | None = None
    turma_id: int
    professor_requerente: str | None = None
    professor_requerente_id: int | None = None
    disciplina: str
    data_ocorrencia: str
    aula: str
    horario_ocorrencia: str
    descricao: str
    descricao_formatada: str | None = None
    regimento_item_ids: list[int] = Field(default_factory=list)
    acao_aplicada: AcaoAplicadaOcorrencia
    status: StatusOcorrencia | None = None


class OcorrenciaUpdateIn(BaseModel):
    nome_estudante: str | None = None
    estudante_id: int | None = None
    turma_id: int | None = None
    professor_requerente: str | None = None
    professor_requerente_id: int | None = None
    disciplina: str | None = None
    data_ocorrencia: str | None = None
    aula: str | None = None
    horario_ocorrencia: str | None = None
    descricao: str | None = None
    descricao_formatada: str | None = None
    regimento_item_ids: list[int] | None = None
    acao_aplicada: AcaoAplicadaOcorrencia | None = None
    status: StatusOcorrencia | None = None


class OcorrenciaOut(BaseModel):
    id: int
    nome_estudante: str
    estudante_id: int | None = None
    turma_id: int
    turma_nome: str = ""
    professor_requerente: str
    professor_requerente_id: int | None = None
    disciplina: str
    data_ocorrencia: str
    aula: str
    horario_ocorrencia: str
    descricao: str
    descricao_formatada: str = ""
    regimento_itens: list[RegimentoItemOcorrenciaOut] = Field(default_factory=list)
    acao_aplicada: str
    status: str
    criado_em: str
    atualizado_em: str


class EstudanteCreateIn(BaseModel):
    nome: str
    turma_id: int


class EstudanteUpdateIn(BaseModel):
    nome: str
    turma_id: int
    ativo: bool = True


class EstudanteStatusIn(BaseModel):
    ativo: bool


class EstudanteOut(BaseModel):
    id: int
    nome: str
    turma_id: int
    turma_nome: str = ""
    ativo: int | bool
    criado_em: str
    atualizado_em: str


class ImportacaoCsvOut(BaseModel):
    mensagem: str
    linhas_processadas: int
    importados: int
    criados: int
    atualizados: int
    erros: int
    detalhes_erros: list[str] = Field(default_factory=list)
