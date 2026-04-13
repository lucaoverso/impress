# Sprint 5

## Objetivo

Unificar a evolucao de schema em um fluxo versionado, separando bootstrap inicial, migrations registradas e seeds padrao.

## Escopo

- [x] Criar runner oficial de migrations com tabela `schema_migrations`
- [x] Integrar o bootstrap para aplicar migrations pendentes de forma explicita
- [x] Separar em `database.py` as etapas de compatibilidade legada, indices e seeds
- [x] Padronizar comandos de manutencao para `upgrade` e `status` das migrations
- [x] Validar lint e testes apos a reorganizacao

## Estrutura

- `db/schema_migrations.py`
- `migrations/*.py`
- `database.py`

## Fluxo oficial

1. `database.criar_tabelas()` faz o bootstrap base do schema atual.
2. `db.schema_migrations` registra e aplica migrations versionadas pendentes.
3. O bloco de compatibilidade legada permanece como camada temporaria de seguranca.
4. Seeds e indices continuam aplicados separadamente do passo de migration.

## Comandos

```bash
make migrate
make migrations-status
```

## Observacoes

- Instalacoes novas continuam subindo com o schema atual sem depender de replay completo das migrations.
- Instalacoes existentes passam a registrar o historico aplicado em `schema_migrations`.
- Os `_garantir_colunas_*` seguem como compatibilidade temporaria e devem ser removidos gradualmente conforme novas migrations substituirem esse backlog.
