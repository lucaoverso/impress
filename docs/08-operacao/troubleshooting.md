# Operacao: Troubleshooting

## Health check

Endpoint:

```text
GET /health
```

O health check valida:

- conexao com SQLite por `SELECT 1`;
- migrations pendentes por `get_pending_migration_names`;
- estado de boot registrado em `app.state.boot_status`;
- modo do worker (`embedded` ou `external`).

Respostas observadas:

- `200` com `status: ok`;
- `503` com `status: error` se banco falhar;
- `503` com `status: degraded` se houver migrations pendentes ou boot nao pronto.

Evidencia: `routers/system_router.py`: `health`.

Classificacao: **Confirmada pelo codigo**.

## Diagnosticos comuns

| Sintoma | Verificacao | Evidencia | Classificacao |
| --- | --- | --- | --- |
| `/health` retorna migrations pendentes | Executar `python -m db.schema_migrations upgrade` com `.env` carregado. | `DEPLOY_LOCAL.md`; `db/schema_migrations.py`. | Confirmada pela documentacao |
| Worker nao imprime | Verificar `journalctl -u sistema-impress-worker -f`, CUPS, `lpstat -p`, `CUPS_PRINTER` e `CUPS_LP_COMMAND`. | `DEPLOY_LOCAL.md`; `services/printer.py`. | Confirmada pelo codigo/documentacao |
| Jobs ficam em `ERRO` | Conferir erro registrado pelo worker e existencia do arquivo em `arquivo_path`. | `services/worker.py`; `services/printer.py`. | Confirmada pelo codigo |
| Upload/preview/reimpressao falha | Conferir permissao e espaco em `SPOOL_DIR`. | `modules/printing/service.py`; `services/worker.py`. | Inferida |
| CUPS indisponivel | Conferir `cups.service`, `lp`, fila padrao e permissao do usuario `sistema-impress` no grupo `lp`. | `DEPLOY_LOCAL.md`; systemd. | Confirmada pela documentacao |
| Deploy automatizado falha com senha sudo | Revisar regra `NOPASSWD` do runner self-hosted. | `DEPLOY_LOCAL.md`. | Confirmada pela documentacao |
| Endpoint Radius retorna 403 | Conferir `RADIUS_INTERNAL_SECRET` e header `X-RADIUS-SECRET`. | `routers/system_router.py`. | Confirmada pelo codigo |
| Download YouTube falha por runtime JS | Conferir `node`, `YTDLP_JS_RUNTIMES` e configuracoes yt-dlp. | `services/youtube_download_service.py`; `.env.example`. | Confirmada pelo codigo |

## Riscos de seguranca em troubleshooting

| Risco | Observacao | Classificacao |
| --- | --- | --- |
| Compartilhar `.env` em suporte pode vazar segredos. | `.env` pode conter `RADIUS_INTERNAL_SECRET`. | Inferida |
| Logs podem conter nomes de arquivos e caminhos internos. | `services/printer.py` registra comando CUPS. | Confirmada pelo codigo |
| Testes com credenciais iniciais em ambiente real podem manter senhas fracas. | Credenciais iniciais sao conhecidas. | Confirmada pelo codigo |
