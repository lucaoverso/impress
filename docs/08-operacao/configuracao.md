# Operacao: Configuracao

Este documento mapeia configuracoes operacionais disponiveis no codigo e nos arquivos de deploy.

## Variaveis de ambiente

| Variavel | Uso atual | Padrao observado | Evidencia | Classificacao |
| --- | --- | --- | --- | --- |
| `DB_PATH` | Define caminho do banco SQLite. Se relativo, e resolvido a partir da base do projeto. | `data/impressao.db`; ha migracao/copia a partir de `impressao.db` legado quando aplicavel. | `database.py`; `.env.example`; `DEPLOY_LOCAL.md`. | Confirmada pelo codigo |
| `TOKEN_TTL_DIAS` | TTL do token de login. | `7`; somente `7` ou `15` sao aceitos, outros valores voltam ao padrao. | `database.py`; `.env.example`. | Confirmada pelo codigo |
| `SPOOL_DIR` | Diretorio de spool para uploads, PDFs, historico e downloads. | `spool/` dentro do projeto. | `routers/config.py`; `modules/printing/config.py`; `services/youtube_download_service.py`; `.env.example`. | Confirmada pelo codigo |
| `APC_DIR` | Diretorio para arquivos APC. | `spool/apc`. | `routers/config.py`; testes APC. | Confirmada pelo codigo |
| `CUPS_PRINTER` | Nome da impressora/fila CUPS padrao. | Vazio quando nao configurado. | `routers/config.py`; `modules/printing/config.py`; `services/printer.py`; `.env.example`. | Confirmada pelo codigo |
| `CUPS_LP_COMMAND` | Comando usado para enviar impressao ao CUPS. | `lp`. | `services/printer.py`; `.env.example`. | Confirmada pelo codigo |
| `CUPS_LP_TIMEOUT_SECONDS` | Timeout do comando `lp`. | `30`. | `services/printer.py`; `.env.example`. | Confirmada pelo codigo |
| `ENABLE_EMBEDDED_WORKER` | Define se a API sobe o worker no mesmo processo. | `false`/desativado se nao definido. | `routers/config.py`; `main.py`; `.env.example`; `DEPLOY_LOCAL.md`. | Confirmada pelo codigo |
| `KEEP_SPOOL_FILES` | Mantem arquivos do spool apos impressao. | `true`. | `services/worker.py`; `.env.example`. | Confirmada pelo codigo |
| `SPOOL_RETENTION_DAYS` | Remove arquivos antigos do spool quando maior que zero. | `0`, retencao desativada. | `services/worker.py`; `.env.example`; testes de retencao. | Confirmada pelo codigo |
| `PRINT_CANCEL_WINDOW_SECONDS` | Janela minima antes do worker enviar job ao CUPS, permitindo cancelamento. | `15`. | `routers/config.py`; `services/worker.py`; `.env.example`. | Confirmada pelo codigo |
| `LOG_LEVEL` | Nivel de log da API/worker. | `INFO`. | `app_logging.py`; `.env.example`. | Confirmada pelo codigo |
| `STATIC_ASSET_VERSION` | Versao de cache busting dos assets; `dynamic` gera valor novo por chamada. | Timestamp do start quando ausente. | `routers/config.py`; `.env.example`. | Confirmada pelo codigo |
| `RADIUS_INTERNAL_SECRET` | Segredo do endpoint interno de integracao Radius. | Vazio; endpoint retorna 403 se vazio ou divergente. | `routers/config.py`; `routers/system_router.py`; `.env.example`. | Confirmada pelo codigo |
| `LIBREOFFICE_COMMAND` | Binario usado para converter DOC/DOCX. | `soffice`. | `.env.example`; uso inferido pelo servico de arquivo/conversao. | Inferida |
| `YTDLP_JS_RUNTIMES` | Runtime JS usado pelo yt-dlp/YouTube. | Tenta `node` se estiver no PATH. | `services/youtube_download_service.py`; `.env.example`. | Confirmada pelo codigo |
| `YTDLP_YOUTUBE_PLAYER_CLIENTS` | Clientes opcionais do extrator YouTube. | Lista vazia. | `services/youtube_download_service.py`; `.env.example`. | Confirmada pelo codigo |
| `YOUTUBE_INFO_CACHE_TTL_SECONDS` | TTL do cache de informacoes de video. | `600`. | `services/youtube_download_service.py`. | Confirmada pelo codigo |
| `YTDLP_CONCURRENT_FRAGMENTS` | Concorrencia de fragmentos do yt-dlp. | `4`, minimo `1`. | `services/youtube_download_service.py`. | Confirmada pelo codigo |

## Inicializacao

Na inicializacao da API, `main.py` executa o `lifespan`:

- configura logging via `app_logging.setup_logging`;
- registra `started_at`, `boot_status` e `worker_mode` em `app.state`;
- chama `criar_tabelas()`;
- cria usuarios iniciais `admin@escola` e `professor@escola` quando ausentes;
- executa `seed_recursos_padrao()`;
- inicia o worker embutido quando `ENABLE_EMBEDDED_WORKER` esta ativo;
- registra routers e monta `/static`.

Evidencia: `main.py`: `lifespan`; `app_logging.py`: `setup_logging`; `db/bootstrap.py`.

Classificacao: **Confirmada pelo codigo**.

## Credenciais iniciais

| Usuario | Senha | Origem | Classificacao |
| --- | --- | --- | --- |
| `admin@escola` | `admin123` | Criado no boot se ausente. Tambem documentado em `CONTRIBUTING.md`. | Confirmada pelo codigo |
| `professor@escola` | `prof123` | Criado no boot se ausente. Tambem documentado em `CONTRIBUTING.md`. | Confirmada pelo codigo |
| Usuarios demo | `demo123` e credenciais especificas impressas pelo seed | `db/demo_seed.py`. | Confirmada pelo codigo |

## Dados de demonstracao

`db/demo_seed.py` contem seed idempotente para dados de demonstracao: usuarios, turmas, disciplinas, estudantes, atribuicoes, agendamentos, PCPI, pre-conselho, ocorrencias, jobs e cotas demo.

Evidencia: `db/demo_seed.py`: `seed_demo_data`; `tests/test_demo_seed.py`.

Classificacao: **Confirmada pelo codigo**.

## Riscos de seguranca

| Risco | Evidencia | Classificacao |
| --- | --- | --- |
| Credenciais iniciais conhecidas podem permanecer ativas em producao se nao forem trocadas. | `main.py` cria `admin@escola/admin123` e `professor@escola/prof123` quando ausentes. | Confirmada pelo codigo |
| `RADIUS_INTERNAL_SECRET` vazio desativa o endpoint interno, mas se configurado fraco permite tentativa contra endpoint sensivel. | `routers/system_router.py`: `internal_radius_ensure_nt_hash`. | Inferida |
| `KEEP_SPOOL_FILES=true` preserva arquivos enviados/impressos, que podem conter dados sensiveis. | `services/worker.py`; `.env.example`. | Confirmada pelo codigo |
| `SPOOL_RETENTION_DAYS=0` desativa limpeza automatica do spool. | `services/worker.py`; `.env.example`. | Confirmada pelo codigo |
| Nginx de exemplo escuta HTTP porta 80 sem TLS. | `deploy/nginx/sistema-impress.conf`. | Confirmada pelo codigo |
| Nao foi encontrada politica automatica de backup/rotacao/criptografia de banco e spool no codigo. | Ausencia de rotina identificada; `backup.md` documenta pendencia. | Pendente de validacao |
