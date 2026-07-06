# Tabelas

Status: catalogo inicial do schema atual.

## Convencoes

- **PK**: chave primaria.
- **FK**: chave estrangeira declarada no schema/migration.
- **UNIQUE**: restricao unica declarada.
- **Confirmada pelo codigo**: tabela/coluna/chave aparece em `database.py` ou `migrations/`.
- **Inferida**: finalidade/cardinalidade deduzida pelo uso.

## Tabelas Por Area

| Area | Tabela | Chaves e restricoes principais | Atributos principais | Evidencia |
| --- | --- | --- | --- | --- |
| Autenticacao | `usuarios` | PK `id`; UNIQUE `email`. | `nome`, `email`, `senha_hash`, `nt_hash`, `perfil`, `cargo`, `acesso_coordenacao`, `data_nascimento`, `ativo`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Autenticacao | `tokens` | PK `token`; FK logica `usuario_id -> usuarios.id` sem FK declarada no trecho de criacao. | `usuario_id`, `criado_em`, `expira_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Impressao | `jobs` | PK `id`; FK logica `usuario_id -> usuarios.id` sem FK declarada no trecho de criacao. | Arquivo, opcoes de impressao, CUPS, `tags_json`, `status`, `prioridade`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Impressao | `cotas` | PK `id`; UNIQUE INDEX `idx_cotas_usuario_mes` em `usuario_id, mes`. | `limite_paginas`, `usadas_paginas`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`, `_criar_indices_schema`. |
| Impressao | `cota_regras` | PK `id` com CHECK `id = 1`. | `base_paginas`, `paginas_por_aula`, `paginas_por_turma`, `cota_mensal_escola`, `atualizado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Impressao | `impressao_status` | PK `id` com CHECK `id = 1`. | `sem_papel`, `mensagem`, `atualizado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260529_create_impressao_status.py`. |
| Agendamento | `recursos` | PK `id`; UNIQUE `nome`. | `nome`, `tipo`, `descricao`, `quantidade_itens`, `imagem_capa`, `ativo`. | Confirmada pelo codigo: `database.py`: `criar_tabelas` e compatibilidade de colunas. |
| Agendamento | `agendamentos` | PK `id`; FK `recurso_id -> recursos.id`; FK `usuario_id -> usuarios.id`. | `data`, `turno`, `aula`, `faixa_global`, `turma`, `tema_aula`, `observacao`, `status`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Catalogos academicos | `turmas` | PK `id`; UNIQUE `nome`. | `turno`, `aula_inicial`, `aula_final`, `quantidade_estudantes`, `ativo`, `criado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Catalogos academicos | `disciplinas` | PK `id`; UNIQUE `nome`. | `aulas_semanais`, `tem_apc`, `tem_prova_bimestral`, `ativo`, `criado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260517_add_disciplina_flags_e_tipo_entrega_apc.py`. |
| Catalogos academicos | `estudantes` | PK `id`; FK `turma_id -> turmas.id`. | `nome`, `ativo`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Docencia | `professores_carga` | PK/FK `usuario_id -> usuarios.id`. | `aulas_semanais`, `turmas_quantidade`, `turmas`, `disciplinas`, `atualizado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Docencia | `professores_turmas_disciplinas` | PK `id`; FK professor/turma/disciplina; UNIQUE `professor_usuario_id, turma_id, disciplina_id`. | `criado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Docencia | `turmas_disciplinas` | PK `id`; FK turma/disciplina/professor; UNIQUE `turma_id, disciplina_id`. | `carga_horaria`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260410_create_turmas_disciplinas.py`. |
| Grade | `configuracao_aulas` | PK `id`; INDEX por `ordem_visual`. | `tipo`, `aula_numero`, `nome`, horarios, `ativo`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Grade | `configuracao_turnos_segmentos` | PK `id`; UNIQUE `turno, periodo`. | `faixa_inicial`, `faixa_final`, `ordem`, `ativo`, datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260615_create_shift_segments.py`. |
| Horario escolar | `horarios_escolares` | PK `id`; FK turma/disciplina/professor; UNIQUE por slot de turma e por slot de professor. | `ano_letivo`, `dia_semana`, `aula_numero`, `faixa_global`, datas. | Confirmada pelo codigo: migrations `20260511_create_horario_escolar_module.py`, `20260511_fix_horario_escolar_faixa_global.py`. |
| PCPI | `pcpi_registros_manuais` | PK `id`; FK `agendamento_id`; FK usuarios criacao/atualizacao. | `data`, `turno`, `tipo_acao`, `origem`, `acao_realizada`, `resultado`, descricao e observacoes. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Pre-conselho | `pre_conselho_periodos` | PK `id`; UNIQUE `ano_letivo, etapa`. | `nome`, datas, `status`, `tem_rav`, datas de controle. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260706_add_rav_preconselho.py`. |
| Pre-conselho | `pre_conselho_motivos` | PK `id`; UNIQUE `codigo`. | `categoria`, `descricao`, `ativo`, `ordem`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Pre-conselho | `pre_conselho_registros` | PK `id`; FK periodo/disciplina/professor/turma/estudante; UNIQUE `professor_usuario_id, estudante_id, disciplina, ano_letivo, bimestre`. | Atencao, motivos JSON, observacoes, campos pos-preconselho, `estudante_em_rav`, texto. | Confirmada pelo codigo: `database.py`: `criar_tabelas`; migration `20260706_add_rav_preconselho.py`. |
| Pre-conselho | `pre_conselho_registro_motivos` | PK `id`; FK `registro_id` com `ON DELETE CASCADE`; FK `motivo_id`; UNIQUE `registro_id, motivo_id`. | `criado_em`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Ocorrencias | `ocorrencias` | PK `id`; FK estudante/turma/professor; CHECK em `tipo_registro`, `quem_assina`, `acao_aplicada`, `status`. | Dados do fato, assinatura, acao, status e datas. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Ocorrencias | `leis`, `artigos`, `incisos`, `alineas` | PKs; FK hierarquica; UNIQUE por pai/numero. | Nomes, numeros, descricoes. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Ocorrencias | `ocorrencia_regimento_itens` | PK `id`; FK `ocorrencia_id`, `artigo_id`, `inciso_id`, `alinea_id`. | Snapshot textual da base legal e `ordem`. | Confirmada pelo codigo: `database.py`: `criar_tabelas`. |
| Ocorrencias | `ocorrencia_estudantes` | PK composta inferida por migration; FK ocorrencia/estudante/turma. | Posicao e snapshot de estudante. | Confirmada pelo codigo: migration `20260517_refine_ocorrencias_vinculos_multiplos.py`. |
| Ocorrencias | `ocorrencia_professores` | PK composta inferida por migration; FK ocorrencia/professor. | Posicao e snapshot de professor. | Confirmada pelo codigo: migration `20260517_refine_ocorrencias_vinculos_multiplos.py`. |
| Pre-registros | `occurrence_reasons` | PK `id`; UNIQUE `name`; CHECK `active IN (0,1)`. | `name`, `active`, datas. | Confirmada pelo codigo: migration `20260611_create_occurrence_pre_registrations.py`. |
| Pre-registros | `occurrence_pre_registrations` | PK `id`; FK estudante/motivo/professor/ocorrencia; CHECK `responsible_contact`; CHECK `status`. | `status`, contato, disciplina/aula/data, datas. | Confirmada pelo codigo: migrations `20260611_create_occurrence_pre_registrations.py`, `20260612_expand_occurrence_pre_registrations.py`. |
| Pre-registros | `occurrence_pre_registration_students` | PK composta `pre_registration_id, student_id`; FK com `ON DELETE CASCADE`. | `position`. | Confirmada pelo codigo: migration `20260612_expand_occurrence_pre_registrations.py`. |
| Pre-registros | `occurrence_pre_registration_reasons` | PK composta `pre_registration_id, reason_id`; FK com `ON DELETE CASCADE`. | `position`. | Confirmada pelo codigo: migration `20260612_expand_occurrence_pre_registrations.py`. |
| APC | `apc_periodos` | PK `id`; UNIQUE `ano_letivo, data_referencia`; FK criador. | Prazo, titulo, observacao, tipo de entrega, datas. | Confirmada pelo codigo: migrations `20260511_create_apc_module.py`, `20260512_refactor_apc_entregas.py`, `20260517_add_disciplina_flags_e_tipo_entrega_apc.py`. |
| APC | `apc_periodo_destinatarios` | PK `id`; FK periodo/professor/turma/disciplina; UNIQUE `periodo_id, professor_usuario_id, turma_id, disciplina_id`. | `criado_em`. | Confirmada pelo codigo: migration `20260521_add_apc_destinatarios_selecionados.py`. |
| APC | `apc_envios` | PK `id`; FK periodo/professor/turma/disciplina; UNIQUE por periodo/professor/turma/disciplina na versao refatorada. | Dados de arquivo, `review_status`, revisao, datas, `primeiro_envio_em`. | Confirmada pelo codigo: migrations `20260512_add_apc_envios_por_disciplina.py`, `20260615_add_apc_submission_review.py`, `20260622_add_apc_submission_history.py`. |
| APC | `apc_envio_historico` | PK `id`; FK envio com `ON DELETE CASCADE`; FK periodo/professor. | Snapshot de arquivo, turma/disciplina, `acao`, datas. | Confirmada pelo codigo: migration `20260622_add_apc_submission_history.py`. |
| APC | `apc_preview_jobs` | PK `id`; UNIQUE `envio_id`; FK envio com `ON DELETE CASCADE`. | Paths, `status`, erro, tentativas, datas. | Confirmada pelo codigo: migration `20260622_create_apc_preview_jobs.py`. |
| Auditoria | `audit_events` | PK `id`; FK `actor_user_id -> usuarios.id ON DELETE SET NULL`; indices por data/filtros. | Categoria, acao, resultado, ator, entidade, metadados. | Confirmada pelo codigo: migration `20260615_create_audit_events.py`. |

## Pontos Pendentes

- Confirmar se `tokens.usuario_id`, `jobs.usuario_id` e `cotas.usuario_id` devem ganhar FK fisica em migration futura. **Pendente de validacao**.
- Confirmar a tabela/armazenamento persistente de downloads de video; o serviço atual parece manter jobs em memoria/processo. **Pendente de validacao**.
- Validar schema final real em banco existente via `PRAGMA table_info` antes de qualquer migration, pois ha compatibilidade legada em `database.py`. **Pendente de validacao**.
