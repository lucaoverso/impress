# Requisitos Nao Funcionais

Status: catalogo inicial extraido de evidencias do codigo.

## Convencoes

- `RNF-SEG-*`: seguranca.
- `RNF-AUT-*`: autenticacao/autorizacao.
- `RNF-DES-*`: desempenho/cache.
- `RNF-DIS-*`: disponibilidade/saude.
- `RNF-LOG-*`: logs.
- `RNF-AUD-*`: auditoria.
- `RNF-BKP-*`: backup/retencao.
- `RNF-UX-*`: responsividade/acessibilidade.
- `RNF-UPL-*`: upload.
- `RNF-ERR-*`: tratamento de erros.
- `RNF-MAN-*`: manutencao.
- `RNF-COMP-*`: compatibilidade.
- `RNF-OPS-*`: operacao em producao.

Classificacao:

- `Confirmada pelo codigo`: ha implementacao direta.
- `Confirmada por teste`: ha implementacao direta e teste automatizado relacionado.
- `Pendente de validacao`: evidencia nao encontrada ou insuficiente.

## Seguranca

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-SEG-001 | Endpoints protegidos devem exigir token Bearer. | `auth.py`: `get_usuario_logado`; uso de `Depends(get_usuario_logado)` em routers | `tests/test_scheduling_router.py` usa `Authorization: Bearer` | Confirmada pelo codigo |
| RNF-SEG-002 | Caminhos de arquivos reutilizados/baixados devem ser validados contra diretorio permitido. | `modules/printing/policies.py`: `resolve_job_pdf_path`; `routers/apc_router.py`: `_resolver_caminho_envio_seguro`, `_resolver_caminho_preview_seguro` | `tests/test_impressao_reuso_historico.py`; `tests/test_apc_router.py` | Confirmada por teste |
| RNF-SEG-003 | Endpoint interno do RADIUS deve exigir segredo compartilhado. | `routers/system_router.py`: `internal_radius_ensure_nt_hash`; `routers/config.py`: `RADIUS_INTERNAL_SECRET` | `tests/test_radius_internal_endpoint.py` | Confirmada por teste |
| RNF-SEG-004 | Senhas nao devem ser armazenadas em texto puro. | `services/auth_service.py`: `hash_senha`; `database.py` usa `senha_hash` em usuarios | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-SEG-005 | Politica de hash de senha forte/criptografico moderno. | Uso atual e `sha256` simples em `services/auth_service.py`: `hash_senha`; nao ha evidencia de salt/adaptativo. | Pendente | Pendente de validacao |

## Autenticacao E Autorizacao

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-AUT-001 | Tokens devem ter expiracao. | `services/auth_service.py`: `autenticar_usuario` calcula `expira_em`; `obter_ttl_token_dias`; `db.usuarios`: `TOKEN_TTL_DIAS` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUT-002 | Tokens expirados devem ser limpos no login. | `services/auth_service.py`: `autenticar_usuario` chama `limpar_tokens_expirados` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUT-003 | Permissoes por cargo devem ser centralizadas. | `routers/common.py`: `MODULOS_POR_CARGO`, `normalizar_cargo_usuario`, `modulos_por_usuario`; `routers/system_router.py`: `eu` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUT-004 | Autorizacoes criticas devem ser validadas no backend. | `routers/common.py`: `exigir_admin`, `exigir_gestor`, `resolver_usuario_professor_selecionado`; services de dominio validam dono/gestor | Pendente de mapeamento | Confirmada pelo codigo |

## Desempenho

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-DES-001 | Arquivos estaticos versionados ou imagens de recursos devem usar cache longo imutavel. | `static_files.py`: `CachedStaticFiles`, `IMMUTABLE_CACHE_CONTROL` | `tests/test_static_files_cache.py`: `test_resource_image_uses_long_immutable_cache`, `test_versioned_asset_uses_long_immutable_cache` | Confirmada por teste |
| RNF-DES-002 | Imagens comuns devem usar cache curto. | `static_files.py`: `IMAGE_CACHE_CONTROL` | `tests/test_static_files_cache.py`: `test_common_image_uses_short_cache` | Confirmada por teste |
| RNF-DES-003 | Assets sem versao devem exigir revalidacao. | `static_files.py`: `REVALIDATE_CACHE_CONTROL` | `tests/test_static_files_cache.py`: `test_unversioned_asset_requires_revalidation` | Confirmada por teste |
| RNF-DES-004 | Downloads de video devem limitar concorrencia de workers. | `services/youtube_download_jobs.py`: `YOUTUBE_DOWNLOAD_MAX_WORKERS`, `ThreadPoolExecutor` | Pendente de mapeamento | Confirmada pelo codigo |

## Disponibilidade

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-DIS-001 | Sistema deve expor healthcheck com banco, migrations, boot e uptime. | `routers/system_router.py`: `health` | `tests/test_system_health.py` | Confirmada por teste |
| RNF-DIS-002 | Healthcheck deve retornar `503` quando boot nao esta pronto, banco falha ou migrations pendem. | `routers/system_router.py`: `health` | `tests/test_system_health.py`: `test_health_retorna_503_quando_boot_nao_esta_ready` | Confirmada por teste |
| RNF-DIS-003 | Worker pode operar embutido ou externo. | `main.py`: `lifespan`; `routers/config.py`: `ENABLE_EMBEDDED_WORKER`; `worker_main.py` | Pendente de mapeamento | Confirmada pelo codigo |

## Logs

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-LOG-001 | Aplicacao deve configurar logging por variavel `LOG_LEVEL`. | `app_logging.py`: `setup_logging`, `_resolver_log_level`; `main.py`: `setup_logging()` | Pendente | Confirmada pelo codigo |
| RNF-LOG-002 | Falhas criticas de startup, worker, impressao e previews devem ser registradas. | `main.py`: `logger.exception`; `services/worker.py`: `logger.exception`, `logger.warning`; `modules/printing/job_creation.py`: `logger.exception`; `routers/apc_router.py`: `logger.exception` | Pendente | Confirmada pelo codigo |
| RNF-LOG-003 | Politica de retencao/centralizacao de logs em producao. | Nao localizada documentacao especifica. | Pendente | Pendente de validacao |

## Auditoria

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-AUD-001 | Login deve registrar eventos de auditoria de sucesso e falha. | `auth.py`: `login`; `modules.audit.service`: `record_event` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUD-002 | Criacao de agendamento deve registrar auditoria de sucesso/falha. | `modules/scheduling/router.py`: `criar_reserva_agendamento` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUD-003 | Envio/revisao de anexos deve registrar auditoria. | `routers/apc_router.py`: `enviar_arquivo_apc_api`, `revisar_envio_apc_api` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-AUD-004 | Modulo de auditoria deve permitir consulta administrativa de eventos. | `modules/audit/router.py`: endpoint de eventos; `modules/audit/service.py` | `tests/test_audit_module.py` | Confirmada por teste |

## Backup E Retencao

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-BKP-001 | Estrategia de backup do SQLite deve existir. | Nao localizada implementacao/documentacao especifica de backup. | Pendente | Pendente de validacao |
| RNF-BKP-002 | Spool deve ter politica configuravel de retencao/limpeza. | `services/worker.py`: `SPOOL_RETENTION_DAYS`, `KEEP_SPOOL_FILES`, `limpar_spool_expirado` | `tests/test_worker_spool_retention.py` | Confirmada por teste |
| RNF-BKP-003 | Arquivos em processamento no spool nao devem ser removidos pela limpeza. | `services/worker.py`: `_listar_arquivos_spool_protegidos`, `limpar_spool_expirado` | `tests/test_worker_spool_retention.py`: `test_limpeza_remove_arquivos_expirados_e_preserva_jobs_em_andamento` | Confirmada por teste |

## Responsividade E Acessibilidade

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-UX-001 | Telas devem usar atributos ARIA em fluxos interativos principais. | `templates/scheduling/*`, `templates/printing/index.html`, `templates/apc.html`, `templates/admin.html` contem `aria-*`, `role`, `aria-live` | `tests/test_scheduling_day_overview.py` cobre presenca de partes do template | Confirmada pelo codigo |
| RNF-UX-002 | Responsividade visual deve ser garantida por CSS responsivo. | Existem CSS por pagina em `static/css/pages/`; revisao completa nao realizada. | Pendente | Pendente de validacao |
| RNF-UX-003 | Acessibilidade deve ser validada por teste automatizado/auditoria dedicada. | Nao localizado teste axe/lighthouse ou equivalente. | Pendente | Pendente de validacao |

## Limites De Upload

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-UPL-001 | Importacoes CSV/JSON de estudantes/base legal devem limitar arquivos a 2 MB. | `services/csv_import_service.py`: `LIMITE_ARQUIVO_IMPORTACAO_BYTES`, `_carregar_linhas_csv`, `_extrair_linhas_base_legal_json`, `_extrair_linhas_estudantes_json` | `tests/test_csv_import_service.py` | Confirmada por teste |
| RNF-UPL-002 | Importacao de atribuicoes docentes deve limitar arquivo JSON a 2 MB. | `services/atribuicoes_docentes_import_service.py`: mensagens de limite de 2 MB | `tests/test_atribuicoes_docentes_import_service.py` | Confirmada por teste |
| RNF-UPL-003 | Uploads de impressao/anexos devem validar formato suportado. | `services/file_service.py`: `arquivo_suportado`; `modules/printing/router.py`: `imprimir`, `preview_impressao`; `routers/apc_router.py`: `enviar_arquivo_apc_api` | `tests/test_apc_router.py`; pendente para impressao | Confirmada pelo codigo |
| RNF-UPL-004 | Limite maximo de tamanho para upload de impressao/APC. | Nao localizado limite de bytes especifico para uploads de impressao/APC. | Pendente | Pendente de validacao |

## Tratamento De Erros

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-ERR-001 | Falhas conhecidas devem retornar `HTTPException` com codigo e mensagem controlados. | Uso amplo de `HTTPException` em routers/services; exemplos: `modules/printing/job_creation.py`, `modules/scheduling/service.py`, `routers/apc_router.py` | `tests/test_impressao_reuso_historico.py`: erros controlados de PDF/banco; `tests/test_scheduling_service.py` | Confirmada por teste |
| RNF-ERR-002 | Falhas de PDF/banco na criacao de job devem remover arquivo temporario. | `modules/printing/job_creation.py`: `create_job_from_ready_pdf` com `limpar_em_falha` | `tests/test_impressao_reuso_historico.py`: `test_criar_job_pdf_invalido_retorna_http_500_controlado`, `test_criar_job_falha_no_banco_retorna_http_500_controlado` | Confirmada por teste |
| RNF-ERR-003 | Healthcheck deve degradar ao detectar falhas de banco/migrations/boot. | `routers/system_router.py`: `health` | `tests/test_system_health.py` | Confirmada por teste |

## Manutencao

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-MAN-001 | Projeto deve seguir organizacao modular por dominio em refatoracao gradual. | `AGENTS.md`; `ARCHITECTURE.md`; existencia de `modules/printing`, `modules/scheduling`, `modules/audit` | Pendente | Confirmada pelo codigo |
| RNF-MAN-002 | SQL especifico deve migrar para repositories/proxies por dominio. | `modules/*/repository.py`; `db/*.py` proxies para `database.py` | Pendente | Confirmada pelo codigo |
| RNF-MAN-003 | Arquivos grandes ainda devem ser monitorados como divida tecnica. | `AGENTS.md`; `docs/05-arquitetura/dividas-tecnicas.md`; `database.py`, `routers/admin_router.py` grandes | Pendente | Pendente de validacao |

## Compatibilidade

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-COMP-001 | Sistema deve operar com SQLite configuravel por `DB_PATH`. | `.env.example`; testes configuram `DB_PATH`; `db/core.py`/`database.py` usam caminho de banco | Varios testes usam `DB_PATH`, ex. `tests/test_system_health.py` | Confirmada por teste |
| RNF-COMP-002 | Conversao de documentos deve depender de LibreOffice configuravel. | `.env.example`: `LIBREOFFICE_COMMAND`; `services/file_service.py`: `converter_para_pdf` | Pendente de mapeamento | Confirmada pelo codigo |
| RNF-COMP-003 | Fontes web devem servir `woff/woff2` com content-type correto. | `static_files.py`: `mimetypes.add_type` | `tests/test_static_files_cache.py`: `test_hashed_font_query_uses_immutable_cache_and_font_content_type` | Confirmada por teste |

## Operacao Em Producao

| ID | Descricao | Evidencia | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- |
| RNF-OPS-001 | Aplicacao deve suportar servico API e worker via systemd. | `deploy/systemd/sistema-impress-api.service`; `deploy/systemd/sistema-impress-worker.service` | Pendente | Confirmada pelo codigo |
| RNF-OPS-002 | Aplicacao deve ter configuracao Nginx versionada. | `deploy/nginx/sistema-impress.conf` | Pendente | Confirmada pelo codigo |
| RNF-OPS-003 | Variaveis operacionais devem estar documentadas em `.env.example`. | `.env.example`: `SPOOL_DIR`, `DB_PATH`, `KEEP_SPOOL_FILES`, `SPOOL_RETENTION_DAYS`, `LIBREOFFICE_COMMAND` | Pendente | Confirmada pelo codigo |
| RNF-OPS-004 | Procedimento de restore/backup em producao deve estar documentado. | Nao localizado documento especifico de restore/backup. | Pendente | Pendente de validacao |
