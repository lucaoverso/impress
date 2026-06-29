# Entidades Do Dominio

Status: catalogo inicial extraido do schema atual.

## Convencoes

- **Confirmada pelo codigo**: entidade/tabela/campo existe no schema, migration, model ou service lido.
- **Inferida**: a finalidade foi deduzida por nomes, chaves e uso no codigo.
- **Pendente de validacao**: precisa de confirmacao funcional ou decisao de produto.

## Entidades Principais

| Entidade | Finalidade aparente | Atributos principais | Tabelas | Evidencia |
| --- | --- | --- | --- | --- |
| Usuario | Identidade, login e perfil de acesso. | `id`, `nome`, `email`, `senha_hash`, `nt_hash`, `perfil`, `cargo`, `acesso_coordenacao`, `data_nascimento`, `ativo`. | `usuarios`, `tokens`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/auth_service.py`: `hash_senha`, `autenticar_usuario`. |
| Token | Sessao/API token de usuario autenticado. | `token`, `usuario_id`, `criado_em`, `expira_em`. | `tokens`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/auth_service.py`: `validar_token`. |
| Job de impressao | Solicita e acompanha uma impressao. | `id`, `usuario_id`, `arquivo`, `arquivo_path`, `copias`, `paginas_por_folha`, `duplex`, `orientacao`, `paginas_totais`, `tags_json`, `status`, `prioridade`, `criado_em`, `finalizado_em`. | `jobs`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `modules/printing/models.py`: `PrintJobSummary`. |
| Cota de impressao | Controla limite e uso mensal por usuario. | `usuario_id`, `mes`, `limite_paginas`, `usadas_paginas`. | `cotas`, `cota_regras`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/cota_service.py`: `validar_e_consumir_cota`. |
| Status operacional de impressao | Indica bloqueio operacional da impressora. | `sem_papel`, `mensagem`, `atualizado_em`. | `impressao_status`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`, `_aplicar_seeds_iniciais`; `modules/printing/policies.py`: `ensure_print_is_available`. |
| Recurso agendavel | Bem/recurso reservado por professores. | `id`, `nome`, `tipo`, `descricao`, `quantidade_itens`, `imagem_capa`, `ativo`. | `recursos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `modules/scheduling/models.py`: `SchedulingResource`. |
| Agendamento | Reserva de recurso por usuario/professor em data/aula. | `id`, `recurso_id`, `usuario_id`, `data`, `turno`, `aula`, `faixa_global`, `turma`, `tema_aula`, `observacao`, `status`, `criado_em`, `cancelado_em`. | `agendamentos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `modules/scheduling/models.py`: `SchedulingReservation`. |
| Turma | Catalogo de turmas escolares. | `id`, `nome`, `turno`, `aula_inicial`, `aula_final`, `quantidade_estudantes`, `ativo`, `criado_em`. | `turmas`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`, `_seed_catalogos_academicos`. |
| Disciplina | Catalogo de componentes curriculares. | `id`, `nome`, `aulas_semanais`, `tem_apc`, `tem_prova_bimestral`, `ativo`, `criado_em`. | `disciplinas`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/apc_service.py`: tipos de entrega. |
| Estudante | Aluno vinculado a uma turma. | `id`, `nome`, `turma_id`, `ativo`, `criado_em`, `atualizado_em`. | `estudantes`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Atribuicao docente | Vinculo entre professor, turma e disciplina. | `professor_usuario_id`, `turma_id`, `disciplina_id`, `carga_horaria`, datas. | `professores_turmas_disciplinas`, `turmas_disciplinas`, `professores_carga`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`, `_migrar_turmas_disciplinas_legado`. |
| Grade/aula global | Configuracao de aulas, intervalos e segmentos de turno. | `tipo`, `aula_numero`, `nome`, `horario_inicio`, `horario_fim`, `turno`, `periodo`, `faixa_inicial`, `faixa_final`, `ativo`. | `configuracao_aulas`, `configuracao_turnos_segmentos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `modules/scheduling/lesson_config.py`. |
| Horario escolar | Alocacao anual de turma/disciplina/professor por dia e faixa. | `ano_letivo`, `turma_id`, `disciplina_id`, `professor_usuario_id`, `dia_semana`, `aula_numero`, `faixa_global`. | `horarios_escolares`. | Confirmada pelo codigo: `migrations/20260511_create_horario_escolar_module.py`; `migrations/20260511_fix_horario_escolar_faixa_global.py`. |
| Registro PCPI | Registro manual ou originado de agendamento para acompanhamento/acao pedagogica. | `data`, `turno`, `tipo_acao`, `origem`, `agendamento_id`, `acao_realizada`, `resultado`, usuarios de criacao/atualizacao. | `pcpi_registros_manuais`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Periodo de pre-conselho | Janela de coleta por ano/etapa. | `nome`, `ano_letivo`, `etapa`, `data_inicio`, `data_fim`, `status`. | `pre_conselho_periodos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/preconselho_service.py`. |
| Motivo de pre-conselho | Catalogo de motivos usados em registros. | `categoria`, `codigo`, `descricao`, `ativo`, `ordem`. | `pre_conselho_motivos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`, `_seed_pre_conselho_motivos`. |
| Registro de pre-conselho | Registro do professor sobre estudante/disciplina/periodo. | `periodo_id`, `disciplina_id`, `professor_usuario_id`, `turma_id`, `estudante_id`, `nivel_atencao`, `motivos`, `observacoes`, campos pos-preconselho, `texto_gerado`. | `pre_conselho_registros`, `pre_conselho_registro_motivos`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Ocorrencia | Registro disciplinar/pedagogico envolvendo estudante, professor ou geral. | `tipo_registro`, `estudante_id`, `turma_id`, `professor_requerente_id`, `disciplina`, `data_ocorrencia`, `aula`, `descricao`, `quem_assina`, `acao_aplicada`, `status`. | `ocorrencias`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; `services/ocorrencia_disciplina_service.py`. |
| Item de regimento | Base legal hierarquica associada a ocorrencias. | Lei, artigo, inciso, alinea, descricoes e snapshots no vinculo. | `leis`, `artigos`, `incisos`, `alineas`, `ocorrencia_regimento_itens`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Pre-registro de ocorrencia | Rascunho/triagem antes de virar ocorrencia. | `student_id`, `reason_id`, `professor_id`, `responsible_contact`, `status`, `occurrence_id`, `discipline`, `lesson`, `occurred_at`. | `occurrence_pre_registrations`, `occurrence_reasons`, tabelas de vinculo. | Confirmada pelo codigo: `migrations/20260611_create_occurrence_pre_registrations.py`; `migrations/20260612_expand_occurrence_pre_registrations.py`; `modules/occurrences/schemas.py`. |
| Periodo APC | Solicita entregas/anexos de APC por prazo. | `ano_letivo`, `data_referencia`, `prazo_envio`, `titulo`, `observacao`, `tipo_entrega`, `criado_por_usuario_id`. | `apc_periodos`, `apc_periodo_destinatarios`. | Confirmada pelo codigo: `migrations/20260511_create_apc_module.py`; `migrations/20260521_add_apc_destinatarios_selecionados.py`; `services/apc_service.py`. |
| Envio APC | Arquivo enviado por professor para periodo/turma/disciplina. | `periodo_id`, `professor_usuario_id`, `turma_id`, `disciplina_id`, dados do arquivo, `review_status`, `reviewed_by_usuario_id`, `primeiro_envio_em`. | `apc_envios`, `apc_envio_historico`, `apc_preview_jobs`. | Confirmada pelo codigo: `migrations/20260512_add_apc_envios_por_disciplina.py`; `migrations/20260615_add_apc_submission_review.py`; `migrations/20260622_add_apc_submission_history.py`. |
| Evento de auditoria | Registro de evento de seguranca/negocio. | `category`, `action`, `outcome`, `actor_user_id`, `description`, `entity_type`, `entity_id`, `metadata_json`, `created_at`. | `audit_events`. | Confirmada pelo codigo: `migrations/20260615_create_audit_events.py`; `modules/audit/models.py`. |

## Exclusoes Logicas

| Entidade | Campo | Comportamento aparente | Evidencia |
| --- | --- | --- | --- |
| Usuario | `ativo` | Usuario pode ser inativado sem remover o registro. | Confirmada pelo codigo: `database.py`: `usuarios`, `_clausula_usuario_ativo`; `tests/test_professor_exclusao.py`. |
| Turma | `ativo` | Turmas podem permanecer no banco e sair de listagens ativas. | Confirmada pelo codigo: `database.py`: `turmas`. |
| Disciplina | `ativo` | Disciplinas podem permanecer no banco e sair de listagens ativas. | Confirmada pelo codigo: `database.py`: `disciplinas`. |
| Estudante | `ativo` | Estudantes podem ser inativados preservando historico. | Confirmada pelo codigo: `database.py`: `estudantes`. |
| Recurso | `ativo` | Recursos inativos nao devem ser reservados. | Confirmada pelo codigo: `database.py`: `recursos`; `modules/scheduling/service.py`: `ensure_resource_is_active`. |
| Motivo de pre-conselho | `ativo` | Motivos podem ser ocultados sem perder registros anteriores. | Confirmada pelo codigo: `database.py`: `pre_conselho_motivos`. |
| Motivo de pre-registro | `active` | Razoes podem ser inativadas. | Confirmada pelo codigo: `migrations/20260611_create_occurrence_pre_registrations.py`. |

## Registros Historicos E Auditoria

| Tipo | Tabelas | Observacao | Evidencia |
| --- | --- | --- | --- |
| Historico de impressao | `jobs` | Jobs finalizados permanecem consultaveis e reutilizaveis quando arquivo existe. | Confirmada pelo codigo: `database.py`: `listar_historico`; `modules/printing/policies.py`: `print_job_can_be_reused`. |
| Historico de envio APC | `apc_envio_historico` | Guarda snapshots de envios/reenvios por envio/periodo/professor. | Confirmada pelo codigo: `migrations/20260622_add_apc_submission_history.py`. |
| Auditoria geral | `audit_events` | Guarda eventos por categoria, acao, resultado e ator. | Confirmada pelo codigo: `migrations/20260615_create_audit_events.py`; `modules/audit/models.py`. |
| Ocorrencias | `ocorrencias`, vinculos e snapshots de regimento | O registro mantem texto/snapshot de itens legais usados. | Confirmada pelo codigo: `database.py`: `ocorrencia_regimento_itens`. |
| Pre-conselho | `pre_conselho_registros` | Mantem texto gerado, observacoes e campos pos-preconselho. | Confirmada pelo codigo: `database.py`: `pre_conselho_registros`. |
