# Modulos

Status: inventario inicial consolidado a partir do codigo atual.

## Convencoes

- **Confirmada pelo codigo**: evidenciada por router, service, repository, schema, migration, tabela, template, JS ou teste.
- **Inferida**: finalidade deduzida pelo uso combinado dos arquivos.
- **Pendente de validacao**: precisa de confirmacao de produto/operacao.

## Resumo Dos Modulos

| Modulo | Objetivo | Organizacao atual | Classificacao |
| --- | --- | --- | --- |
| Autenticacao | Login, token, usuario logado e integracao Radius. | Router simples + service. | Confirmada pelo codigo |
| Usuarios/professores | Cadastro, recuperacao de senha, cargos, coordenadores e atribuicoes docentes. | Rotas legadas em `routers/` e persistencia em `database.py`/`db/`. | Confirmada pelo codigo |
| Impressao | Upload, preview, cota, fila, historico, reimpressao e worker CUPS. | Modulo em `modules/printing`. | Confirmada pelo codigo |
| Agendamento | Reserva de recursos por data/turma/aula/professor. | Modulo em `modules/scheduling`. | Confirmada pelo codigo |
| Recursos | Cadastro e uso de recursos reservaveis. | Embutido em admin + agendamento. | Inferida |
| APC/anexos | Solicitacoes, envios, revisao, historico, preview e impressao de anexos. | Router legado + services + `modules/apc_review`. | Confirmada pelo codigo |
| Ocorrencias/coordenacao | Ocorrencias, regimento/base legal, PDF e pre-registros. | Router legado + `modules/occurrences`. | Confirmada pelo codigo |
| Pre-conselho | Periodos, motivos, registros, consolidado e relatorios. | Modulo em `modules/preconselho`. | Confirmada pelo codigo |
| PCPI | Registros manuais e acompanhamento de acoes pedagogicas. | Service/routers legados. | Confirmada pelo codigo |
| Relatorios | Dashboards e relatorios de impressao, recursos e anexos. | Router + `db/relatorios.py`. | Confirmada pelo codigo |
| Horario escolar | Grade anual por turma, professor, disciplina e aula. | Router + service + migrations. | Confirmada pelo codigo |
| Auditoria | Registro e consulta de eventos. | Modulo em `modules/audit`. | Confirmada pelo codigo |
| Download de videos | Consulta, jobs, tickets e download de videos. | Router + services em memoria/processo. | Confirmada pelo codigo |
| Operacao/sistema | Healthcheck, paginas, static assets, worker e deploy. | Routers de sistema/paginas + deploy. | Confirmada pelo codigo |

## Autenticacao

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Autenticar usuarios, emitir tokens, validar Bearer token e expor usuario atual. |
| Atores | Usuario comum, admin, coordenador, professor; servico interno Radius. |
| Endpoints | `POST /login`; `GET /me`; `POST /internal/radius/ensure-nt-hash`; `GET /health` como suporte operacional. |
| Paginas | `GET /login-page` renderiza `templates/login.html`. |
| Arquivos principais | `auth.py`; `services/auth_service.py`; `routers/system_router.py`; `services/radius_service.py`; `static/js/core/auth.js`. |
| Tabelas utilizadas | `usuarios`, `tokens`, `audit_events`; `radcheck`/view Radius pendente de detalhe. |
| Dependencias | SQLite, auditoria, Radius interno, localStorage/sessionStorage no frontend. |
| Regras de negocio | RN-AUT-001, RN-AUT-002, RN-AUT-003 em `docs/02-requisitos/regras-de-negocio.md`. |
| Integracoes | FreeRADIUS/RADIUS via `X-RADIUS-SECRET`; auditoria. |
| Testes existentes | `tests/test_nt_hash_integration.py`; `tests/test_radius_internal_endpoint.py`; uso de Bearer em testes de routers. |
| Dividas tecnicas | Hash de senha usa `sha256` simples em `services/auth_service.py`; paginas HTML nao exigem auth no render, apenas APIs. |
| Duvidas pendentes | Confirmar politica de senha/hash forte e ciclo de vida de tokens em producao. |

## Usuarios / Professores

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Administrar usuarios docentes/gestores, cargos, coordenadores, cargas, turmas, disciplinas e recuperacao de senha. |
| Atores | Admin; gestor em consultas limitadas; professor no cadastro/recuperacao. |
| Endpoints | `GET /professores/opcoes`; `POST /professores/cadastro`; `POST /professores/recuperar-senha`; grupo `/admin/professores`; `/admin/coordenadores`; `/admin/professores/{id}/senha`; `/admin/professores/{id}/promover-coordenador`; `/admin/professores/{id}/carga`; `/admin/atribuicoes-docentes*`; `/admin/turmas-disciplinas*`. |
| Paginas | `GET /cadastro-professor`; `GET /admin`. |
| Arquivos principais | `routers/professores_router.py`; `routers/professores_common.py`; `routers/admin_router.py`; `routers/common.py`; `db/usuarios.py`; `db/docencia.py`; `services/atribuicoes_docentes_import_service.py`; `static/js/cadastro-professor.js`; `static/js/admin/atribuicoes.js`. |
| Tabelas utilizadas | `usuarios`, `professores_carga`, `professores_turmas_disciplinas`, `turmas_disciplinas`, `turmas`, `disciplinas`. |
| Dependencias | Autenticacao, permissoes, catalogos academicos, importacao JSON. |
| Regras de negocio | Senha forte e validacao de nascimento em `routers/common.py`; permissoes em `docs/04-dominio/permissoes.md`. |
| Integracoes | Radius por `nt_hash`; importacao de atribuicoes docentes. |
| Testes existentes | `tests/test_professor_exclusao.py`; `tests/test_admin_atribuicoes_docentes.py`; `tests/test_admin_turmas_disciplinas.py`; `tests/test_atribuicoes_docentes_import_service.py`; `tests/test_coordenacao_opcoes.py`. |
| Dividas tecnicas | SQL e regras ainda concentrados em `database.py`/`admin_router.py`; usuarios ainda nao possuem modulo `modules/users`. |
| Duvidas pendentes | Separar `perfil` legado de `cargo` definitivo; confirmar quem pode auto-cadastrar professor em producao. |

## Impressao

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Gerenciar impressao escolar com upload, preview, fila, prioridade, cota, historico e reimpressao. |
| Atores | Professor; admin/coordenador; professor com `acesso_coordenacao`; worker. |
| Endpoints | `GET /impressao/turmas`; `GET /impressao/tags`; `GET /impressao/status`; `POST /imprimir`; `POST /impressao/preview`; `GET /fila`; `GET /jobs/{id}/preview`; `POST /jobs/{id}/reimprimir`; `POST /jobs/{id}/cancelar`; `POST /jobs/{id}/prioridade`; `GET /meus-jobs`; `GET /minha-cota`; admin: `/admin/fila`, `/admin/impressao/status`, `/admin/historico`, `/admin/relatorio/impressao`, `/admin/cotas/*`. |
| Paginas | `GET /impressao`; `GET /professor` redireciona para `/impressao`; `GET /admin`. |
| Arquivos principais | `modules/printing/*`; `routers/impressao_router.py`; `services/worker.py`; `services/printer.py`; `services/file_service.py`; `services/cota_service.py`; `worker_main.py`; `static/js/professor.js`; `static/js/printing/*`; `templates/professor.html`. |
| Tabelas utilizadas | `jobs`, `cotas`, `cota_regras`, `impressao_status`, `usuarios`, `turmas`, `estudantes`. |
| Dependencias | CUPS/lp, LibreOffice, PDF service, spool, worker, autenticacao, cota, auditoria indireta. |
| Regras de negocio | RN-IMP-001 a RN-IMP-008; RF-IMP-001 a RF-IMP-015. |
| Integracoes | CUPS via `services/printer.py`; LibreOffice via `services/file_service.py`; systemd worker. |
| Testes existentes | `tests/test_printing_service.py`; `tests/test_print_layout_options.py`; `tests/test_impressao_reuso_historico.py`; `tests/test_impressao_status.py`; `tests/test_worker_spool_retention.py`. |
| Dividas tecnicas | Arquivos `_job_*` duplicados/legados coexistem com arquivos atuais; repos ainda delegam para `db/impressao.py`/`database.py`; modulo critico em producao requer cautela. |
| Duvidas pendentes | Confirmar lifecycle completo de status `FINALIZADO` versus `CONCLUIDO`; confirmar politica de retencao de spool em producao. |

## Agendamento

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Reservar recursos escolares por data, aula/faixa, turma, professor, tema e observacao. |
| Atores | Usuario autenticado; professor; admin; gestor/professor com acesso de coordenacao para selecao de professor. |
| Endpoints | `GET /agendamento/recursos`; `GET /agendamento/opcoes`; `GET /agendamento/professores`; `GET /agendamento/reservas`; `POST /agendamento/reservas`; `POST /agendamento/reservas/{id}/cancelar`; admin: `/admin/configuracao-aulas*`. |
| Paginas | `GET /agendamento`. |
| Arquivos principais | `modules/scheduling/*`; `db/agendamento.py`; `db/catalogos.py`; `db/horario_escolar.py`; `templates/agendamento.html`; `static/js/agendamento.js`; `static/js/scheduling/*`. |
| Tabelas utilizadas | `agendamentos`, `recursos`, `turmas`, `configuracao_aulas`, `configuracao_turnos_segmentos`, `usuarios`. |
| Dependencias | Autenticacao, permissoes compartilhadas, auditoria, catalogos, grade global, frontend de repeticao/visao do dia. |
| Regras de negocio | RN-AGE-001 a RN-AGE-010; RF-AGE-001 a RF-AGE-014. |
| Integracoes | Auditoria interna; sem integracao externa identificada. |
| Testes existentes | `tests/test_scheduling_service.py`; `tests/test_scheduling_router.py`; `tests/test_scheduling_day_overview.py`; `tests/test_scheduling_repeat_step.py`; `tests/test_schedule_repair_migration.py`. |
| Dividas tecnicas | Permissao de scheduling reaproveita nome `usuario_pode_gerir_impressoes`; SQL final ainda em `database.py`; recursos nao estao em modulo proprio. |
| Duvidas pendentes | Coordenador deve criar reserva em nome de professor? A listagem permite gestor, mas resolver de professor selecionado tem regra propria. |

## Recursos

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Manter catalogo de recursos reservaveis, capacidade, imagem e status ativo. |
| Atores | Gestor/admin na administracao; usuarios autenticados no consumo via agendamento. |
| Endpoints | Admin: `GET /admin/recursos`; `POST /admin/recursos/upload-imagem`; `POST /admin/recursos`; `PUT /admin/recursos/{id}`; `PUT /admin/recursos/{id}/status`; consumo: `GET /agendamento/recursos`. |
| Paginas | `GET /admin`; `GET /agendamento`. |
| Arquivos principais | `routers/admin_router.py`; `modules/scheduling/repository.py`; `modules/scheduling/models.py`; `db/catalogos.py`; `database.py`; `static/img/resources/*`. |
| Tabelas utilizadas | `recursos`, `agendamentos`. |
| Dependencias | Agendamento, admin, upload de imagem/static assets. |
| Regras de negocio | Recursos inativos nao podem ser reservados: RN-AGE-001. |
| Integracoes | Static files/cache para imagens; sem integracao externa propria. |
| Testes existentes | Coberto indiretamente por `tests/test_scheduling_service.py`, `tests/test_scheduling_router.py`, `tests/test_static_files_cache.py`. |
| Dividas tecnicas | Nao existe `modules/resources`; regra e persistencia vivem entre admin, scheduling e database. |
| Duvidas pendentes | Deve virar modulo independente antes de futuras mudancas? |

## APC / Anexos

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Solicitar, receber, revisar, visualizar, historizar e imprimir anexos/APC por periodo, professor, turma e disciplina. |
| Atores | Professor; gestao APC: admin/coordenador/professor com acesso de coordenacao. |
| Endpoints | `GET /apc/contexto`; `GET /apc/destinatarios/opcoes`; `GET /apc/calendario`; `GET /apc/solicitacoes`; `GET /apc/periodos/{id}`; `POST /apc/periodos`; `PUT /apc/periodos/{id}`; `DELETE /apc/periodos/{id}`; `POST /apc/periodos/{id}/envio`; `PUT /apc/envios/{id}/revisao`; `DELETE /apc/envios/{id}`; `GET /apc/envios/{id}/arquivo`; `GET /apc/envios/{id}/preview`; `POST /apc/envios/{id}/imprimir`. |
| Paginas | `GET /apc`. |
| Arquivos principais | `routers/apc_router.py`; `services/apc_service.py`; `services/apc_recipient_service.py`; `services/apc_preview_service.py`; `services/apc_preview_worker.py`; `modules/apc_review/*`; `modules/printing/attachment_printing.py`; `db/apc.py`; `templates/apc.html`; `static/js/apc.js`. |
| Tabelas utilizadas | `apc_periodos`, `apc_periodo_destinatarios`, `apc_envios`, `apc_envio_historico`, `apc_preview_jobs`, `usuarios`, `turmas`, `disciplinas`, `horarios_escolares`, `audit_events`. |
| Dependencias | Autenticacao, permissoes, horario escolar, impressão, PDF/preview, APC dir/spool, auditoria. |
| Regras de negocio | RN-ANE-001 a RN-ANE-007; RF-ANE-001 a RF-ANE-007. |
| Integracoes | Impressao de anexos via modulo printing; conversao/preview PDF; worker para preview. |
| Testes existentes | `tests/test_apc_router.py`. |
| Dividas tecnicas | Router APC concentra muitos fluxos; review esta modularizado parcialmente em `modules/apc_review`; regras/persistencia ainda espalhadas. |
| Duvidas pendentes | Confirmar transicoes permitidas de `review_status`; confirmar limites de upload APC. |

## Ocorrencias / Coordenacao

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Registrar e acompanhar ocorrencias disciplinares/pedagogicas, base legal/regimento, PDF e pre-registros. |
| Atores | Professor; gestor/coordenacao; admin. |
| Endpoints | Legado em `routers/admin_router.py`/coordenacao pendente de detalhar; modulo novo: `GET /occurrences/context`; `GET /occurrences/students`; `GET /occurrences/reasons`; `POST /occurrences/reasons`; `GET /occurrences/pre-registrations`; `POST /occurrences/pre-registrations`; `POST /occurrences/pre-registrations/{id}/complete`. |
| Paginas | `GET /coordenacao`. |
| Arquivos principais | `modules/occurrences/*`; `routers/admin_router.py`; `services/ocorrencia_disciplina_service.py`; `services/ocorrencia_pdf_service.py`; `db/ocorrencias.py`; `templates/coordenacao.html`; `static/js/coordenacao/*`; `static/js/coordenacao.js`. |
| Tabelas utilizadas | `ocorrencias`, `estudantes`, `turmas`, `usuarios`, `leis`, `artigos`, `incisos`, `alineas`, `ocorrencia_regimento_itens`, `ocorrencia_estudantes`, `ocorrencia_professores`, `occurrence_reasons`, `occurrence_pre_registrations`, tabelas N:N de pre-registro. |
| Dependencias | Autenticacao, permissoes, catalogos academicos, horario escolar para contexto, PDF. |
| Regras de negocio | Status/acoes/tipos em `docs/04-dominio/estados-e-status.md`; regras ainda pendentes de catalogo RN especifico. |
| Integracoes | Geracao de PDF; sem integracao externa identificada. |
| Testes existentes | `tests/test_ocorrencias_router.py`; `tests/test_ocorrencia_pdf_service.py`; `tests/test_ocorrencia_disciplina_service.py`; `tests/test_occurrence_pre_registrations.py`; `tests/test_regimento_ocorrencias.py`. |
| Dividas tecnicas | Parte do modulo esta em `modules/occurrences`, parte em `database.py`, services e `admin_router.py`; endpoints legados precisam mapeamento fino. |
| Duvidas pendentes | Delimitar fronteira entre coordenacao, ocorrencias e pre-registros; decidir se base legal vira submodulo. |

## Pre-Conselho

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Coletar e consolidar apontamentos por periodo/turma/disciplina/estudante, com motivos e texto gerado. |
| Atores | Professor; coordenador/gestor; admin. |
| Endpoints | `GET /preconselho/contexto`; `GET /preconselho/turmas-disciplinas`; `GET /preconselho/estudantes`; `POST /preconselho/texto/preview`; `POST /preconselho/registros`; `DELETE /preconselho/registros/{id}`; `GET /preconselho/registros`; `GET /preconselho/consolidado`; `GET /preconselho/relatorio`; `GET/POST/PUT /preconselho/periodos*`; `GET/POST/PUT /preconselho/motivos*`; `GET /preconselho/niveis-atencao`. |
| Paginas | `GET /preconselho`. |
| Arquivos principais | `modules/preconselho/*`; `services/preconselho_service.py`; `db/preconselho.py`; `templates/preconselho.html`; `static/js/preconselho.js`. |
| Tabelas utilizadas | `pre_conselho_periodos`, `pre_conselho_motivos`, `pre_conselho_registros`, `pre_conselho_registro_motivos`, `usuarios`, `turmas`, `disciplinas`, `estudantes`, `turmas_disciplinas`. |
| Dependencias | Autenticacao, permissoes, usuarios/docencia, catalogos, relatorios/texto. |
| Regras de negocio | Periodo aberto/fechado; escopo docente por atribuicoes; motivos e niveis de atencao. Catalogo RN especifico ainda pendente. |
| Integracoes | Sem integracao externa identificada. |
| Testes existentes | `tests/test_preconselho_service.py`; `tests/test_preconselho_router.py`. |
| Dividas tecnicas | Coexistem `services/preconselho_service.py` e modulo `modules/preconselho`; precisa definir fronteira final. |
| Duvidas pendentes | Confirmar regras de edicao pos-preconselho e permissoes de gestor versus admin. |

## PCPI

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Registrar acoes pedagogicas/administrativas do turno, inclusive a partir de agendamentos e impressao. |
| Atores | Coordenador/gestor; admin. |
| Endpoints | `GET /pcpi/sugestoes`; `GET /pcpi/registros-manuais`; `POST /pcpi/registros-manuais`; `GET /pcpi/texto`; `POST /pcpi/texto/preview`; `POST /pcpi/texto/pdf`. |
| Paginas | `GET /pcpi`. |
| Arquivos principais | `pcpi_router.py`; `services/pcpi_service.py`; `services/pcpi_pdf_service.py`; `db/pcpi.py`; `templates/pcpi.html`; `static/js/pcpi.js`. |
| Tabelas utilizadas | `pcpi_registros_manuais`, `agendamentos`, `usuarios`. |
| Dependencias | Agendamento, impressao, usuarios, PDF. |
| Regras de negocio | Tipos de acao PCPI em `services/pcpi_service.py`; regras RN especificas pendentes. |
| Integracoes | Geracao de PDF. |
| Testes existentes | `tests/test_pcpi_service.py`; `tests/test_pcpi_registro.py`. |
| Dividas tecnicas | Router esta na raiz (`pcpi_router.py`) e nao em `routers/` ou `modules/pcpi`; modulo ainda nao segue estrutura modular alvo. |
| Duvidas pendentes | Confirmar finalidade operacional exata do PCPI e se deve virar `modules/pcpi`. |

## Relatorios

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Expor dashboard e relatorios de uso, impressao, recursos e anexos. |
| Atores | Admin, coordenador, professor com `acesso_coordenacao`. |
| Endpoints | `GET /api/relatorios/dashboard`; `GET /api/relatorios/anexos`; admin: `/admin/relatorio`, `/admin/relatorio/impressao`, `/admin/relatorio/recursos`. |
| Paginas | `GET /relatorios`; `GET /admin`. |
| Arquivos principais | `routers/relatorios_router.py`; `db/relatorios.py`; `routers/admin_router.py`; `templates/relatorios.html`; `static/js/relatorios.js`. |
| Tabelas utilizadas | `jobs`, `agendamentos`, `recursos`, `usuarios`, `apc_*`, `turmas`, `disciplinas`; detalhes em `db/relatorios.py`. |
| Dependencias | Autenticacao, permissao de coordenacao, dados de impressao/agendamento/APC. |
| Regras de negocio | Acesso restrito por `usuario_tem_acesso_coordenacao`; periodo inicial/final validado. |
| Integracoes | Sem integracao externa identificada. |
| Testes existentes | `tests/test_relatorios_router.py`. |
| Dividas tecnicas | Consultas e agregacoes em `db/relatorios.py`; modulo ainda nao tem `modules/reports`. |
| Duvidas pendentes | Confirmar indicadores oficiais e granularidade esperada dos relatorios. |

## Horario Escolar

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Gerenciar e consultar horario escolar por ano, turma, disciplina, professor, dia e aula global. |
| Atores | Professor para visualizacao; gestor/admin para gestao. |
| Endpoints | `GET /horario-escolar/contexto`; `GET /horario-escolar/registros`; `GET /horario-escolar/turmas/{id}/matriz`; `POST /horario-escolar/registros`; `PUT /horario-escolar/registros/{id}`; `DELETE /horario-escolar/registros/{id}`; `GET /horario-escolar/professores-do-dia`. |
| Paginas | `GET /horario-escolar`. |
| Arquivos principais | `routers/horario_escolar_router.py`; `services/horario_escolar_service.py`; `db/horario_escolar.py`; `templates/horario_escolar.html`; `static/js/horario_escolar.js`; migrations de horario/global schedule. |
| Tabelas utilizadas | `horarios_escolares`, `configuracao_aulas`, `configuracao_turnos_segmentos`, `turmas`, `disciplinas`, `usuarios`. |
| Dependencias | Autenticacao, permissoes, catalogos academicos, configuracao global de aulas. |
| Regras de negocio | Gestores gerem; professores visualizam; unicidade por slot de turma/professor via indices. |
| Integracoes | Sem integracao externa identificada. |
| Testes existentes | `tests/test_horario_escolar_service.py`; `tests/test_horario_escolar_router.py`; `tests/test_schedule_repair_migration.py`. |
| Dividas tecnicas | Usa router/service fora de `modules/horario_escolar`; migrations fazem reparos/backfills de grade. |
| Duvidas pendentes | Confirmar consumo de `configuracao_turnos_segmentos` em runtime e regra final para integral/vespertino. |

## Auditoria

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Registrar eventos de autenticacao, agendamento, anexos e permitir consulta administrativa. |
| Atores | Sistema registra; admin consulta. |
| Endpoints | `GET /admin/audit/events`. |
| Paginas | Painel incluído em `templates/includes/admin_audit_panel.html` e navegacao admin. |
| Arquivos principais | `modules/audit/*`; `migrations/20260615_create_audit_events.py`; `templates/includes/admin_audit_panel.html`; `static/js/admin/audit.js`. |
| Tabelas utilizadas | `audit_events`, `usuarios`. |
| Dependencias | Autenticacao, permissoes admin, routers que chamam `record_event`. |
| Regras de negocio | Consulta restrita a admin; categorias e resultados em `modules/audit/models.py`. |
| Integracoes | Sem integracao externa identificada. |
| Testes existentes | `tests/test_audit_module.py`. |
| Dividas tecnicas | Nem todos os fluxos sensiveis parecem auditados; cobertura de eventos ainda precisa inventario. |
| Duvidas pendentes | Definir politica de retencao e quais acoes devem gerar auditoria obrigatoria. |

## Download De Videos

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Obter informacoes, criar jobs, gerar tickets e baixar arquivos de video para apoio pedagogico. |
| Atores | Usuario autenticado. |
| Endpoints | `POST /download/info`; `POST /download/jobs`; `GET /download/jobs/{id}`; `POST /download/jobs/{id}/ticket`; `GET /download/jobs/{id}/arquivo`; `POST /download/arquivo`. |
| Paginas | `GET /download`; `GET /download/detalhes`. |
| Arquivos principais | `routers/download_router.py`; `services/youtube_download_service.py`; `services/youtube_download_jobs.py`; `templates/download.html`; `static/js/download.js`. |
| Tabelas utilizadas | Nenhuma tabela persistente confirmada; jobs parecem geridos em memoria/processo. |
| Dependencias | Autenticacao, yt-dlp/Node runtime, filesystem para arquivo gerado. |
| Regras de negocio | Apenas usuario autenticado; status `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `ERRO`. |
| Integracoes | YouTube/yt-dlp; runtime JS configuravel em `.env.example`. |
| Testes existentes | `tests/test_youtube_download_service.py`; `tests/test_youtube_download_jobs.py`. |
| Dividas tecnicas | Persistencia/retomada de jobs nao confirmada; restricao por perfil nao existe alem de autenticacao. |
| Duvidas pendentes | Confirmar se download deve ser permitido a todos os autenticados e se jobs precisam persistencia. |

## Operacao / Sistema / Paginas

| Campo | Mapeamento |
| --- | --- |
| Objetivo | Servir paginas, assets, healthcheck, boot, worker, static cache e deploy. |
| Atores | Usuario autenticado no frontend; operador/TI; systemd/Nginx. |
| Endpoints | `GET /`; `GET /health`; paginas em `routers/pages_router.py`; static assets via configuracao da app. |
| Paginas | `/login-page`, `/servicos`, `/impressao`, `/agendamento`, `/relatorios`, `/download`, `/pcpi`, `/preconselho`, `/cadastro-professor`, `/admin`, `/coordenacao`, `/horario-escolar`, `/apc`. |
| Arquivos principais | `main.py`; `routers/pages_router.py`; `routers/system_router.py`; `static_files.py`; `app_logging.py`; `worker_main.py`; `deploy/systemd/*`; `deploy/nginx/*`; `templates/includes/*`. |
| Tabelas utilizadas | Healthcheck consulta banco/migrations; demais paginas dependem das APIs. |
| Dependencias | FastAPI, Jinja2, static files, SQLite, migrations, worker, systemd, Nginx. |
| Regras de negocio | Healthcheck retorna `503` em falha/degraded; paginas HTML sao renderizadas sem auth backend, APIs protegidas. |
| Integracoes | systemd, Nginx, CUPS via worker, filesystem/spool. |
| Testes existentes | `tests/test_system_health.py`; `tests/test_static_files_cache.py`; `tests/test_pages_router_assets.py`; `tests/test_schema_migrations.py`; `tests/test_demo_seed.py`. |
| Dividas tecnicas | Politica de backup/restore pendente; paginas dependem do frontend para redirecionar usuario sem token. |
| Duvidas pendentes | Definir checklist operacional de producao, logs, backup e restore. |

## Demais Pontos Transversais

| Tema | Situacao | Classificacao |
| --- | --- | --- |
| Banco de dados | SQLite com schema central em `database.py`, migrations versionadas e proxies em `db/`. | Confirmada pelo codigo |
| Frontend | Templates Jinja2 + JS estatico por pagina/modulo. | Confirmada pelo codigo |
| Permissoes | Backend valida acoes criticas; frontend controla visibilidade. | Confirmada pelo codigo |
| Modularizacao | Impressao, agendamento, auditoria, ocorrencias e pre-conselho ja tem `modules/`; usuarios, recursos, relatorios, horario e PCPI ainda estao mais legados. | Inferida |
