# Operacao: Backup e restauracao

## Dados que precisam de backup

| Item | Caminho/configuracao | Motivo | Classificacao |
| --- | --- | --- | --- |
| Banco SQLite | `DB_PATH`, recomendado como `/opt/sistema-impress-data/impressao.db`. | Contem usuarios, tokens, jobs, agendamentos, catalogos, auditoria e demais dados. | Confirmada pelo codigo |
| Spool | `SPOOL_DIR`, recomendado como `/var/spool/sistema-impress`. | Contem arquivos enviados/preparados e historico reutilizavel para preview/reimpressao quando `KEEP_SPOOL_FILES=true`. | Confirmada pelo codigo |
| `.env` | `/opt/sistema-impress/.env` no deploy local. | Contem configuracoes operacionais e segredos como `RADIUS_INTERNAL_SECRET`. | Confirmada pela documentacao |
| Arquivos APC/downloads | `APC_DIR` e subpastas dentro de `SPOOL_DIR`. | Dados de apoio operacional. | Inferida |

## Backup automatico

Nao foi encontrada rotina automatica de backup no codigo atual.

Classificacao: **Pendente de validacao**.

## Restauracao

Nao foi encontrada rotina automatica de restauracao no codigo atual.

Pelo desenho atual, uma restauracao manual precisaria preservar coerencia entre:

- arquivo SQLite apontado por `DB_PATH`;
- arquivos fisicos em `SPOOL_DIR`;
- configuracoes em `.env`;
- versao do codigo/migrations.

Classificacao: **Inferida**.

## Migracoes e banco

O banco e preparado por `database.criar_tabelas()` e por migrations versionadas em `db/schema_migrations.py`. O deploy local tambem documenta execucao manual:

```bash
.venv/bin/python -m db.schema_migrations upgrade
```

Evidencia: `db/schema_migrations.py`; `DEPLOY_LOCAL.md`.

Classificacao: **Confirmada pelo codigo/documentacao**.

## Riscos

| Risco | Evidencia | Classificacao |
| --- | --- | --- |
| Sem backup automatico documentado/implementado, perda do arquivo SQLite implica perda operacional relevante. | Ausencia de rotina encontrada. | Pendente de validacao |
| Backup apenas do banco pode nao restaurar previews/reimpressoes se o spool nao for salvo. | Jobs armazenam `arquivo_path`; `KEEP_SPOOL_FILES=true` preserva arquivos. | Inferida |
| Backup de `.env` pode expor segredos se armazenado sem protecao. | `.env` contem `RADIUS_INTERNAL_SECRET` e parametros sensiveis. | Inferida |
| Restaurar banco em versao de codigo divergente pode exigir migrations/compatibilidade. | `database.criar_tabelas()` aplica compatibilidades e migrations. | Inferida |
