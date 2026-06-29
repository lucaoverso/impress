# Operacao: Logs

## Configuracao de logs

`app_logging.py` configura logging com:

- nivel definido por `LOG_LEVEL`;
- padrao `INFO`;
- formato `%(asctime)s %(levelname)s [%(name)s] %(message)s`.

`main.py` chama `setup_logging()` na aplicacao. `worker_main.py` tambem chama `setup_logging()` antes de iniciar o worker externo.

Classificacao: **Confirmada pelo codigo**.

## Logs da API

No deploy systemd, a API roda por `sistema-impress-api.service`. Os logs ficam disponiveis via journald:

```bash
journalctl -u sistema-impress-api -f
```

Evidencia: `DEPLOY_LOCAL.md`; `deploy/systemd/sistema-impress-api.service`.

Classificacao: **Confirmada pela documentacao/configuracao**.

## Logs do worker

No deploy systemd, o worker roda por `sistema-impress-worker.service`. Os logs ficam disponiveis via:

```bash
journalctl -u sistema-impress-worker -f
```

`services/worker.py` registra:

- normalizacao inicial de fila;
- inicio do worker;
- limpeza automatica do spool;
- erros ao imprimir job;
- falhas ao processar preview APC.

`services/printer.py` registra:

- comando enviado ao CUPS;
- aceite do job pelo CUPS.

Classificacao: **Confirmada pelo codigo/documentacao**.

## Auditoria versus logs

Eventos de auditoria sao dados de negocio gravados na tabela `audit_events`, nao logs operacionais. Exemplos:

- login bem-sucedido ou recusado;
- envio de impressao;
- criacao de agendamento;
- redefinicao administrativa de senha.

Evidencia: `modules/audit/service.py`, `modules/audit/repository.py`, `auth.py`, `modules/printing/job_creation.py`, `modules/scheduling/router.py`, `routers/admin_router.py`.

Classificacao: **Confirmada pelo codigo**.

## Riscos

| Risco | Evidencia | Classificacao |
| --- | --- | --- |
| Logs do CUPS podem incluir nomes de arquivos enviados para impressao. | `services/printer.py` registra comando com titulo/caminho. | Confirmada pelo codigo |
| Nao foi identificada configuracao propria de rotacao de logs no app; depende do journald/systemd. | Systemd usado; sem arquivo de log dedicado no codigo. | Inferida |
| Nivel `DEBUG` em producao pode expor informacoes operacionais excessivas. | `LOG_LEVEL` controla nivel global. | Inferida |
