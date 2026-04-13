# Sprint 7

## Objetivo

Endurecer a operacao do projeto com verificacoes de deploy, healthcheck mais util e logging padronizado para API e worker.

## Escopo

- [x] Padronizar logging da aplicacao e do worker
- [x] Melhorar o endpoint `/health` com checagem real de banco, migrations e estado do bootstrap
- [x] Endurecer o deploy com etapa explicita de migrations, validacao de `systemd` e healthcheck apos restart
- [x] Atualizar artefatos operacionais (`.env.example`, `systemd` e guia de deploy)
- [x] Validar com testes automatizados

## Estrutura

- `app_logging.py`
- `db/core.py`
- `routers/system_router.py`
- `.github/workflows/deploy.yml`
- `deploy/systemd/*.service`
- `tests/test_system_health.py`

## Observacoes

- O healthcheck continua compativel com o consumo atual por manter `status = ok` no caso saudavel.
- O deploy agora falha antes de concluir se migrations, restart ou healthcheck nao fecharem corretamente.
- O worker e a impressao passam a registrar eventos no journal com logging padronizado em vez de `print`.
