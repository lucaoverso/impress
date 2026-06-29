# Migrations E Seeds

Status: mapa inicial extraido do codigo.

## Bootstrap Do Banco

| Item | Comportamento | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Criacao base | `database.py`: `criar_tabelas` cria tabelas centrais, aplica migrations versionadas, compatibilidade legada, indices e seeds iniciais. | `database.py`: `criar_tabelas`, `_aplicar_migracoes_versionadas`, `_aplicar_compatibilidade_schema_legada`, `_criar_indices_schema`, `_aplicar_seeds_iniciais`. | Confirmada pelo codigo |
| Migrations versionadas | Aplicacao delegada para `db/schema_migrations.py`. | `database.py`: `_aplicar_migracoes_versionadas`; `db/schema_migrations.py`. | Confirmada pelo codigo |
| Compatibilidade legada | Funcoes `_garantir_colunas_*` adicionam colunas/tabelas ausentes como backstop temporario. | `database.py`: `_aplicar_compatibilidade_schema_legada`. | Confirmada pelo codigo |
| Banco configuravel | Caminho usa `DB_PATH` quando informado. | `db/core.py`; scripts de migration usam `_default_db_path`. | Confirmada pelo codigo |

## Migrations Identificadas

| Migration | Finalidade | Entidades/tabelas impactadas | Classificacao |
| --- | --- | --- | --- |
| `20260305_add_nt_hash_to_usuarios.py` | Adicionar hash NT para integracao Radius. | `usuarios.nt_hash`. | Confirmada pelo codigo |
| `20260305_create_radcheck_view.py` | Criar view/estrutura de compatibilidade Radius. | Radius/usuarios. | Pendente de detalhe |
| `20260311_add_estudantes_e_referencias_ocorrencias.py` | Adicionar estudantes e referencias de ocorrencias. | `estudantes`, `ocorrencias`. | Confirmada pelo codigo |
| `20260311_create_ocorrencias.py` | Criar modulo inicial de ocorrencias. | `ocorrencias`. | Confirmada pelo codigo |
| `20260401_create_pcpi_registros_manuais.py` | Criar registros manuais PCPI. | `pcpi_registros_manuais`. | Confirmada pelo codigo |
| `20260410_create_pre_conselho_module.py` | Criar estrutura inicial de pre-conselho. | `pre_conselho_*`. | Confirmada pelo codigo |
| `20260410_create_professores_turmas_disciplinas.py` | Criar vinculo professor/turma/disciplina. | `professores_turmas_disciplinas`. | Confirmada pelo codigo |
| `20260410_create_turmas_disciplinas.py` | Criar oferta turma/disciplina. | `turmas_disciplinas`. | Confirmada pelo codigo |
| `20260416_add_acesso_coordenacao_to_usuarios.py` | Adicionar permissao de coordenacao ao usuario. | `usuarios.acesso_coordenacao`. | Confirmada pelo codigo |
| `20260511_create_apc_module.py` | Criar APC inicial. | `apc_periodos`, `apc_envios`. | Confirmada pelo codigo |
| `20260511_create_horario_escolar_module.py` | Criar horario escolar. | `horarios_escolares`. | Confirmada pelo codigo |
| `20260511_fix_horario_escolar_faixa_global.py` | Ajustar faixa global no horario. | `horarios_escolares.faixa_global`, indices. | Confirmada pelo codigo |
| `20260512_add_apc_envios_por_disciplina.py` | Refatorar envios APC por periodo/professor/turma/disciplina. | `apc_envios`. | Confirmada pelo codigo |
| `20260512_refactor_apc_entregas.py` | Refatorar periodos/entregas APC. | `apc_periodos`. | Confirmada pelo codigo |
| `20260514_add_apc_envio_nome_cliente.py` | Guardar nome de arquivo do cliente. | `apc_envios`. | Confirmada pelo codigo |
| `20260517_add_disciplina_flags_e_tipo_entrega_apc.py` | Adicionar flags de disciplina e tipo de entrega APC. | `disciplinas`, `apc_periodos`. | Confirmada pelo codigo |
| `20260517_expand_ocorrencias_central_registros.py` | Expandir ocorrencias para central de registros. | `ocorrencias`. | Confirmada pelo codigo |
| `20260517_refine_ocorrencias_vinculos_multiplos.py` | Adicionar vinculos multiplos em ocorrencias. | `ocorrencia_estudantes`, `ocorrencia_professores`. | Confirmada pelo codigo |
| `20260521_add_apc_destinatarios_selecionados.py` | Selecionar destinatarios APC. | `apc_periodo_destinatarios`. | Confirmada pelo codigo |
| `20260529_create_impressao_status.py` | Criar status operacional de impressao. | `impressao_status`. | Confirmada pelo codigo |
| `20260611_create_occurrence_pre_registrations.py` | Criar pre-registros de ocorrencia. | `occurrence_reasons`, `occurrence_pre_registrations`. | Confirmada pelo codigo |
| `20260612_expand_occurrence_pre_registrations.py` | Expandir pre-registro para multiplos estudantes/motivos. | `occurrence_pre_registration_students`, `occurrence_pre_registration_reasons`. | Confirmada pelo codigo |
| `20260613_create_global_schedule_config.py` | Criar/ajustar configuracao global de aulas. | `configuracao_aulas`. | Confirmada pelo codigo |
| `20260613_repair_global_schedule_config.py` | Reparar/seedar configuracao global de aulas. | `configuracao_aulas`. | Confirmada pelo codigo |
| `20260614_add_quem_assina_to_ocorrencias.py` | Adicionar assinatura em ocorrencias. | `ocorrencias.quem_assina`. | Confirmada pelo codigo |
| `20260615_add_apc_submission_review.py` | Adicionar revisao de envios APC. | `apc_envios.review_status` e campos de revisao. | Confirmada pelo codigo |
| `20260615_create_audit_events.py` | Criar auditoria. | `audit_events`. | Confirmada pelo codigo |
| `20260615_create_shift_segments.py` | Criar segmentos de turno. | `configuracao_turnos_segmentos`. | Confirmada pelo codigo |
| `20260615_repair_global_schedule_config.py` | Reparar/seedar grade global. | `configuracao_aulas`. | Confirmada pelo codigo |
| `20260622_add_apc_submission_history.py` | Criar historico de envios APC. | `apc_envio_historico`, `apc_envios.primeiro_envio_em`. | Confirmada pelo codigo |
| `20260622_create_apc_preview_jobs.py` | Criar fila de preview APC. | `apc_preview_jobs`. | Confirmada pelo codigo |

## Seeds Iniciais

| Seed | Dados criados/garantidos | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Catalogos academicos padrao | Insere `TURMAS_PADRAO` em `turmas` e `DISCIPLINAS_PADRAO` em `disciplinas`. | `database.py`: `_seed_catalogos_academicos`. | Confirmada pelo codigo |
| Periodos de pre-conselho | Insere periodos retornados por `periodos_padrao_pre_conselho()`. | `database.py`: `_seed_pre_conselho_periodos`; `services/preconselho_service.py`. | Confirmada pelo codigo |
| Motivos de pre-conselho | Insere catalogo retornado por `catalogo_motivos_iniciais_pre_conselho()`. | `database.py`: `_seed_pre_conselho_motivos`; `services/preconselho_service.py`. | Confirmada pelo codigo |
| Regras de cota | Garante linha unica `cota_regras.id = 1`. | `database.py`: `_aplicar_seeds_iniciais`. | Confirmada pelo codigo |
| Status operacional de impressao | Garante linha unica `impressao_status.id = 1`. | `database.py`: `_aplicar_seeds_iniciais`. | Confirmada pelo codigo |
| Segmentos de turno | Insere combinacoes padrao `MATUTINO`, `VESPERTINO`, `VESPERTINO_EM`, `INTEGRAL`. | `database.py`: `criar_tabelas`; migration `20260615_create_shift_segments.py`. | Confirmada pelo codigo |
| Recursos padrao | Existe chamada para seed de recursos padrao no seed de demonstracao. | `db/demo_seed.py`: `seed_demo_data` chama `database.seed_recursos_padrao()`. | Confirmada pelo codigo |

## Criacao Automatica De Usuarios Ou Dados

| Origem | Dados criados | Observacao | Classificacao |
| --- | --- | --- | --- |
| `db/demo_seed.py`: `seed_demo_data` | Admin `admin@escola`, professor `professor@escola`, coordenacao e professores demo. | Usa `database.criar_usuario_se_nao_existir` para admin/professor base e `_upsert_usuario` para usuarios demo. | Confirmada pelo codigo |
| `db/demo_seed.py`: `seed_demo_data` | Turmas, disciplinas, estudantes, atribuicoes, agendamentos, PCPI, pre-conselho, ocorrencias, jobs e cotas demo. | Seed idempotente para visualizacao local; tambem reativa usuarios base. | Confirmada pelo codigo |
| `database.py`: `_migrar_catalogos_academicos` | Cria turmas/disciplinas a partir de dados legados em carga docente e agendamentos. | Backfill para compatibilidade. | Confirmada pelo codigo |
| `database.py`: `_migrar_turmas_disciplinas_legado` | Popula `turmas_disciplinas` a partir de `professores_turmas_disciplinas`. | Mantem compatibilidade entre modelos de atribuicao. | Confirmada pelo codigo |
| `migrations/20260612_expand_occurrence_pre_registrations.py` | Backfill de estudantes/motivos em tabelas N:N a partir dos campos antigos. | Usa `INSERT OR IGNORE`. | Confirmada pelo codigo |
| `migrations/20260622_add_apc_submission_history.py` | Backfill de `apc_envio_historico` a partir de `apc_envios`. | Gera acao inicial `ENVIO`. | Confirmada pelo codigo |

## Pendencias

- Confirmar se `db/demo_seed.py` deve ser descrito como seed apenas local ou tambem ferramenta operacional de homologacao. **Pendente de validacao**.
- Confirmar politica de rollback para migrations executadas em producao. **Pendente de validacao**.
- Confirmar se o backstop de compatibilidade em `database.py` deve continuar ou migrar totalmente para migrations versionadas. **Pendente de validacao**.
