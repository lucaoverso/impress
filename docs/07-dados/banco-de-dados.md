# Banco De Dados

Status: visao inicial consolidada.

## Tecnologia E Localizacao

| Item | Descricao | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Banco | SQLite. | `AGENTS.md`; `db/core.py`; `database.py`. | Confirmada pelo codigo |
| Caminho | Configuravel por `DB_PATH`; scripts de migration usam caminho padrao fora do repo quando `DB_PATH` nao existe. | `db/core.py`; migrations com `_default_db_path`. | Confirmada pelo codigo |
| Bootstrap | `database.criar_tabelas()` cria schema base, aplica migrations, compatibilidade, indices e seeds. | `database.py`: `criar_tabelas`. | Confirmada pelo codigo |
| Acesso a dados | Projeto ainda usa `database.py` grande e proxies em `db/`; modulos refatorados usam repositories. | `database.py`; `db/_proxy.py`; `modules/*/repository.py`. | Confirmada pelo codigo |

## Fronteiras De Acesso

| Camada/area | Papel atual | Evidencia | Classificacao |
| --- | --- | --- | --- |
| `database.py` | Schema, funcoes de persistencia legadas, seeds, indices e compatibilidade. | `database.py`. | Confirmada pelo codigo |
| `db/*.py` | Proxies/fachadas por area para funcoes de `database.py`. | `db/_proxy.py`, `db/agendamento.py`, `db/impressao.py`, `db/preconselho.py`. | Confirmada pelo codigo |
| `modules/*/repository.py` | Persistencia em modulos ja modularizados. | `modules/printing/repository.py`, `modules/scheduling/repository.py`, `modules/audit/repository.py`. | Confirmada pelo codigo |
| `migrations/` | Evolucao versionada do schema. | `migrations/*.py`; `db/schema_migrations.py`. | Confirmada pelo codigo |

## Indices E Restricoes

- O schema cria indices para filas de impressao, tokens, agendamentos, APC, pre-conselho, ocorrencias, estudantes e horario escolar. **Confirmada pelo codigo**: `database.py`: `_criar_indices_schema`; migrations especificas.
- Algumas relacoes centrais usam FK fisica (`agendamentos`, pre-conselho, ocorrencias, APC, auditoria). **Confirmada pelo codigo**.
- Algumas relacoes importantes ainda sao logicas, sem FK fisica declarada no trecho de criacao (`jobs.usuario_id`, `cotas.usuario_id`, `tokens.usuario_id`). **Inferida** pelo schema e uso em consultas.

## Riscos E Pendencias

- Validar schema real do banco de producao antes de qualquer migration, porque ha compatibilidade legada aplicada em runtime. **Pendente de validacao**.
- Confirmar politica de backup/restore do SQLite. **Pendente de validacao**.
- Confirmar se todas as tabelas de vinculo antigas continuam funcionais ou se algumas sao legado em transicao. **Pendente de validacao**.
