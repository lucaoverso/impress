# Operacao: Deploy

## Modelo de deploy disponivel

O repositorio possui um guia de deploy local para servidor escolar em `DEPLOY_LOCAL.md`. O modelo descrito usa:

- Ubuntu/Debian;
- Python virtualenv;
- CUPS local;
- Nginx como reverse proxy;
- dois servicos systemd: API e worker;
- banco SQLite fora da pasta do codigo;
- spool persistente fora da pasta do codigo.

Classificacao: **Confirmada pelo codigo/documentacao**.

## Dependencias do servidor

`DEPLOY_LOCAL.md` orienta instalar:

- `python3`, `python3-venv`, `python3-pip`;
- `cups`, `cups-client`;
- `nginx`;
- `libreoffice`;
- `nodejs`.

Classificacao: **Confirmada pela documentacao**.

## Servicos systemd

| Servico | Funcao | Comando | Evidencia |
| --- | --- | --- | --- |
| `sistema-impress-api.service` | Sobe FastAPI via Uvicorn. | `/opt/sistema-impress/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers` | `deploy/systemd/sistema-impress-api.service` |
| `sistema-impress-worker.service` | Sobe worker externo. | `/opt/sistema-impress/.venv/bin/python worker_main.py` | `deploy/systemd/sistema-impress-worker.service` |

Ambos usam:

- `User=sistema-impress`;
- `Group=lp`;
- `WorkingDirectory=/opt/sistema-impress`;
- `EnvironmentFile=/opt/sistema-impress/.env`;
- `Restart=always`;
- dependencia de `cups.service`.

Classificacao: **Confirmada pelo codigo/configuracao**.

## Nginx

`deploy/nginx/sistema-impress.conf`:

- escuta porta `80`;
- faz proxy para `http://127.0.0.1:8000`;
- define `client_max_body_size 50m`;
- repassa headers `Host`, `X-Real-IP`, `X-Forwarded-For` e `X-Forwarded-Proto`;
- usa `proxy_read_timeout 120s`.

Classificacao: **Confirmada pelo codigo/configuracao**.

## Health check pos-deploy

`DEPLOY_LOCAL.md` orienta validar:

- `curl http://127.0.0.1:8000/health`;
- `curl http://127.0.0.1/health`;
- worker ativo sem erro no `journalctl`;
- envio de impressao criando job e enviando ao CUPS.

O endpoint `/health` retorna:

- `status`;
- `service`;
- `boot_status`;
- `worker_mode`;
- `started_at`;
- `uptime_seconds`;
- `checks.database`;
- `checks.migrations`;
- `pending_migrations` quando houver.

Evidencia: `routers/system_router.py`: `health`.

Classificacao: **Confirmada pelo codigo/documentacao**.

## Deploy automatizado

`DEPLOY_LOCAL.md` menciona workflow em `.github/workflows/deploy.yml` e uso de `sudo -n` por runner self-hosted. A validacao completa dessa workflow nao foi feita nesta etapa.

Classificacao: **Pendente de validacao**.

## Riscos de seguranca

| Risco | Evidencia | Classificacao |
| --- | --- | --- |
| Nginx de exemplo usa HTTP sem TLS. | `deploy/nginx/sistema-impress.conf`. | Confirmada pelo codigo |
| Se o runner self-hosted tiver permissao ampla de `sudo`, o impacto de comprometimento aumenta. | `DEPLOY_LOCAL.md` recomenda `NOPASSWD` escopado e alerta contra runner como root. | Confirmada pela documentacao |
| CUPS nao deve ser exposto diretamente na internet. | `DEPLOY_LOCAL.md` orienta nao expor porta 631. | Confirmada pela documentacao |
| API roda atras de Nginx em `127.0.0.1`; exposicao direta do Uvicorn fora desse desenho precisa ser validada. | `deploy/systemd/sistema-impress-api.service`. | Inferida |
