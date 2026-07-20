# Produto

Status: visao geral inicial extraida do codigo e da documentacao existente.

## Convencoes

- **Confirmada pelo codigo**: evidenciada por arquivos, rotas, services, migrations, templates ou configuracoes.
- **Inferida**: conclusao deduzida pela combinacao de nomes, fluxos e entidades existentes.
- **Pendente de validacao**: precisa de confirmacao de usuario, operacao ou produto.

## Problema Que O Sistema Resolve

O sistema centraliza servicos escolares operacionais que hoje dependem de fluxos administrativos, professores e coordenacao: impressao com fila/cota/historico, reserva de recursos pedagogicos, acompanhamento de ocorrencias, pre-conselho, APC/anexos, horario escolar, relatorios e apoio de operacao.

Classificacao: **Inferida**.  
Evidencias: `AGENTS.md` descreve a aplicacao escolar com modulos de impressao, agendamento, recursos, usuarios, autenticacao e relatorios; `main.py` registra routers de impressao, agendamento, admin, relatorios, APC, horario escolar, auditoria e pre-conselho; `templates/servicos.html` e templates por area indicam telas de uso.

## Quem Utiliza

| Usuario/perfil | Uso aparente | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Professor | Imprimir materiais, consultar historico/cota, agendar recursos, enviar APC/anexos, preencher pre-conselho e interagir com ocorrencias/pre-registros quando autorizado. | `routers/common.py`: `MODULOS_POR_CARGO`; `modules/printing/router.py`; `modules/scheduling/router.py`; `routers/apc_router.py`; `modules/preconselho/router.py`. | Confirmada pelo codigo |
| Coordenador | Acessar relatorios/coordenacao, gerir impressoes, acompanhar APC, PCPI, pre-conselho, horario e ocorrencias. | `routers/common.py`: `MODULOS_POR_CARGO`; `routers/admin_router.py`; `routers/relatorios_router.py`; `routers/apc_router.py`; `templates/coordenacao.html`. | Confirmada pelo codigo |
| Administrador | Administrar usuarios, estrutura academica, operacao de impressao, auditoria e configuracoes. | `routers/common.py`: `MODULOS_POR_CARGO`; `routers/admin_router.py`; `modules/audit/router.py`; `templates/admin.html`. | Confirmada pelo codigo |
| Servico/operacao | Executar API e worker, processar fila de impressao e previews APC. | `main.py`: `lifespan`; `worker_main.py`; `services/worker.py`; `deploy/systemd/*.service`. | Confirmada pelo codigo |

## Areas Da Escola Atendidas

| Area | Necessidades atendidas | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Sala dos professores/docencia | Impressao, agendamento de recursos, envio de documentos, pre-conselho. | `templates/printing/index.html`; `modules/printing/*`; `modules/scheduling/*`; `modules/preconselho/*`. | Confirmada pelo codigo |
| Coordenacao pedagogica | Ocorrencias, PCPI, relatorios, APC, acompanhamento de professores/turmas. | `templates/coordenacao.html`; `routers/apc_router.py`; `services/pcpi_service.py`; `modules/occurrences/*`; `routers/relatorios_router.py`. | Confirmada pelo codigo |
| Secretaria/gestao escolar | Cadastros, usuarios, turmas, disciplinas, estudantes e atribuicoes docentes. | `routers/admin_router.py`; `services/csv_import_service.py`; `services/atribuicoes_docentes_import_service.py`; `database.py`: tabelas academicas. | Inferida |
| TI/operacao | Deploy, worker, CUPS, banco SQLite, logs, healthcheck, Nginx e systemd. | `.env.example`; `routers/system_router.py`; `deploy/systemd`; `deploy/nginx`; `docs/08-operacao/*`. | Confirmada pelo codigo |

## Funcionalidades Principais

| Funcionalidade | Descricao | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Autenticacao e perfis | Login, token, cargos/perfis e autorizacao por modulo. | `auth.py`; `services/auth_service.py`; `routers/common.py`. | Confirmada pelo codigo |
| Impressao | Upload/preview, criacao de jobs, fila, cancelamento, prioridade, cota, status operacional, historico e reimpressao. | `modules/printing/router.py`; `modules/printing/job_creation.py`; `services/worker.py`; `services/printer.py`; `tests/test_impressao_reuso_historico.py`. | Confirmada pelo codigo |
| Agendamento | Listagem de recursos, opcoes, professores, reservas, criacao e cancelamento. | `modules/scheduling/router.py`; `modules/scheduling/service.py`; `templates/scheduling/*`; `tests/test_scheduling_router.py`. | Confirmada pelo codigo |
| Recursos escolares | Cadastro/uso de recursos reservaveis com capacidade e status ativo. | `database.py`: `recursos`; `modules/scheduling/models.py`: `SchedulingResource`; `docs/03-modulos/agendamento.md`. | Confirmada pelo codigo |
| APC/anexos | Periodos, publico alvo, envio de arquivos por professor, revisao, historico, preview e impressao de anexos. | `routers/apc_router.py`; `services/apc_service.py`; `modules/apc_review/*`; migrations APC; `tests/test_apc_router.py`. | Confirmada pelo codigo |
| Ocorrencias | Registro/consulta de ocorrencias, base legal/regimento, PDF e pre-registros. | `database.py`: `ocorrencias`; `modules/occurrences/*`; `services/ocorrencia_pdf_service.py`; `tests/test_ocorrencias_router.py`. | Confirmada pelo codigo |
| Pre-conselho | Periodos, motivos, registros por professor/turma/estudante, texto gerado e relatorios. | `modules/preconselho/*`; `services/preconselho_service.py`; `tests/test_preconselho_router.py`. | Confirmada pelo codigo |
| PCPI | Registros manuais e acompanhamento de acoes pedagogicas/turnos. | `services/pcpi_service.py`; `templates/pcpi.html`; `tests/test_pcpi_service.py`. | Confirmada pelo codigo |
| Horario escolar | Configuracao e consulta de horarios por professor/turma/disciplina. | `routers/horario_escolar_router.py`; `services/horario_escolar_service.py`; migrations de horario; `tests/test_horario_escolar_router.py`. | Confirmada pelo codigo |
| Relatorios | Relatorios por periodo, impressao e indicadores operacionais/pedagogicos. | `routers/relatorios_router.py`; `db/relatorios.py`; `tests/test_relatorios_router.py`. | Confirmada pelo codigo |
| Download de videos | Download/estado de jobs de video para apoio pedagogico. | `routers/download_router.py`; `services/youtube_download_service.py`; `services/youtube_download_jobs.py`; `tests/test_youtube_download_service.py`. | Confirmada pelo codigo |
| Auditoria | Registro e consulta administrativa de eventos de auth, impressao, agendamento e anexos. | `modules/audit/*`; migration `20260615_create_audit_events.py`; `tests/test_audit_module.py`. | Confirmada pelo codigo |
| Healthcheck e operacao | Healthcheck, worker embutido/externo, logs e deploy. | `routers/system_router.py`; `main.py`: `lifespan`; `worker_main.py`; `deploy/systemd`; `deploy/nginx`. | Confirmada pelo codigo |

## Tecnologias Utilizadas

| Tecnologia | Uso | Evidencia | Classificacao |
| --- | --- | --- | --- |
| FastAPI | Backend HTTP/API. | `AGENTS.md`; `ARCHITECTURE.md`; `main.py`. | Confirmada pelo codigo |
| SQLite | Banco de dados principal. | `AGENTS.md`; `ARCHITECTURE.md`; `database.py`; `db/core.py`. | Confirmada pelo codigo |
| Jinja2/templates | Renderizacao das paginas. | `AGENTS.md`; `routers/config.py`: `Jinja2Templates`; `templates/`. | Confirmada pelo codigo |
| HTML/CSS/JavaScript estatico | Frontend das telas do sistema. | `static/js/`; `static/css/`; `templates/`. | Confirmada pelo codigo |
| CUPS/lp | Envio de impressao para impressora. | `.env.example`: `CUPS_PRINTER`, `CUPS_LP_COMMAND`; `services/printer.py`. | Confirmada pelo codigo |
| LibreOffice | Conversao de DOC/DOCX para PDF. | `.env.example`: `LIBREOFFICE_COMMAND`; `services/file_service.py`. | Confirmada pelo codigo |
| yt-dlp/Node runtimes | Extracao/download de videos. | `.env.example`: variaveis de runtime JS/cliente; `services/youtube_download_service.py`. | Confirmada pelo codigo |
| systemd e Nginx | Operacao em servidor. | `deploy/systemd/*.service`; `deploy/nginx/sistema-impress.conf`. | Confirmada pelo codigo |

## Integracoes Externas

| Integracao | Finalidade | Evidencia | Classificacao |
| --- | --- | --- | --- |
| CUPS | Imprimir jobs via comando `lp`. | `services/printer.py`; `.env.example`. | Confirmada pelo codigo |
| LibreOffice | Converter arquivos de texto/apresentacao para PDF antes de imprimir/preview. | `services/file_service.py`; `.env.example`. | Confirmada pelo codigo |
| FreeRADIUS/RADIUS | Garantir/consultar hash NT para autenticacao externa. | `routers/system_router.py`: `internal_radius_ensure_nt_hash`; `services/radius_service.py`; `.env.example`: `RADIUS_INTERNAL_SECRET`; `tests/test_radius_internal_endpoint.py`. | Confirmada pelo codigo |
| YouTube/yt-dlp | Baixar videos para uso escolar. | `services/youtube_download_service.py`; `services/youtube_download_jobs.py`; `.env.example`. | Confirmada pelo codigo |
| Nginx | Proxy/reverse proxy para a API. | `deploy/nginx/sistema-impress.conf`. | Confirmada pelo codigo |
| systemd | Servicos de API e worker. | `deploy/systemd/sistema-impress-api.service`; `deploy/systemd/sistema-impress-worker.service`. | Confirmada pelo codigo |

## Funcionalidades Que Parecem Estar Em Producao

| Funcionalidade | Sinal de producao | Classificacao |
| --- | --- | --- |
| Impressao | AGENTS alerta para cuidado no modulo de impressao em producao; ha CUPS, worker, spool, cota, historico, tests e unit files. | Inferida |
| Agendamento | Modulo com router/service/repository, templates, testes e docs especificas. | Inferida |
| Autenticacao/usuarios | Login, token, perfis, tokens expiraveis, hash e integracao Radius. | Inferida |
| APC/anexos | Fluxos amplos, migrations recentes, preview worker, revisao, historico e testes. | Inferida |
| Ocorrencias/coordenacao | Rotas, services, PDF, base legal, pre-registros e testes. | Inferida |
| Pre-conselho | Modulo completo com admin/context/records/reports, migrations, seeds e testes. | Inferida |
| Horario escolar | Router/service/templates/migrations/testes. | Inferida |
| Auditoria | Migration, modulo e teste dedicado. | Inferida |
| Operacao API/worker | systemd, Nginx, healthcheck e variaveis em `.env.example`. | Inferida |

## Pendencias De Validacao

- Confirmar quais modulos estao efetivamente liberados para usuarios finais no ambiente real.
- Confirmar se download de videos esta em uso cotidiano ou apenas disponivel tecnicamente.
- Confirmar escopo real de uso de APC, PCPI e pre-registros de ocorrencia por area da escola.
- Confirmar procedimento operacional de backup/restore do SQLite e arquivos de spool/APC.
