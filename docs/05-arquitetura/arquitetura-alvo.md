# Arquitetura alvo

Este documento compara a arquitetura alvo definida em `AGENTS.md` e `ARCHITECTURE.md` com o codigo real observado no repositorio. O objetivo e registrar o grau de aderencia atual, sem propor reescrita completa.

## Fontes

- `AGENTS.md`: define refatoracao gradual, preservacao de comportamento, modularizacao por dominio e fluxo `router -> service -> repository -> database`.
- `ARCHITECTURE.md`: detalha estrutura alvo, responsabilidades das camadas, uso de `core/`, `shared/`, `modules/`, `templates/`, `static/` e `db/`.
- `docs/05-arquitetura/estado-atual.md`: consolida a organizacao real identificada no codigo.
- Codigo real: `main.py`, `database.py`, `models.py`, `auth.py`, `modules/`, `routers/`, `services/`, `db/`, `templates/` e `static/`.

## Sintese

A arquitetura alvo ja comecou a ser implementada, principalmente com a pasta `modules/` e alguns dominios estruturados com `router.py`, `service.py`, `repository.py`, `schemas.py` e `models.py`. Ao mesmo tempo, o sistema ainda depende fortemente de arquivos legados centrais, proxies de banco e routers antigos.

Classificacao: **Confirmada pelo codigo**.

## O que ja foi implementado

| Item da arquitetura alvo | Evidencia no codigo real | Status |
| --- | --- | --- |
| Pasta `modules/` por dominio | Existem `modules/printing`, `modules/scheduling`, `modules/audit`, `modules/occurrences`, `modules/preconselho` e `modules/apc_review`. | Confirmada pelo codigo |
| Estrutura modular em alguns dominios | `printing`, `scheduling`, `audit` e `occurrences` possuem combinacoes de `router.py`, `service.py`, `repository.py`, `schemas.py` e/ou `models.py`. | Confirmada pelo codigo |
| Separacao parcial entre router, service e repository | Modulos como `modules/printing` e `modules/scheduling` ja possuem camadas separadas. | Confirmada pelo codigo |
| Uso de Pydantic para contratos | Existem schemas em `models.py` e tambem em `modules/*/schemas.py`. | Confirmada pelo codigo |
| Uso de entidades/modelos simples por modulo | Existem dataclasses/enums em modulos como `modules/scheduling/models.py`, `modules/printing/models.py`, `modules/audit/models.py` e `modules/apc_review/models.py`. | Confirmada pelo codigo |
| Templates separados do backend Python | Templates ficam em `templates/` e sao renderizados por routers. | Confirmada pelo codigo |
| Arquivos estaticos separados | CSS, JS, imagens e vendor assets ficam em `static/`, servidos via `CachedStaticFiles`. | Confirmada pelo codigo |
| Worker separado da rota HTTP | O processamento de fila fica em `services/worker.py` e pode ser iniciado por `worker_main.py` ou pelo `lifespan`. | Confirmada pelo codigo |
| Migracoes versionadas | `db/schema_migrations.py` aplica arquivos em `migrations/`. | Confirmada pelo codigo |
| Refatoracao gradual em vez de ruptura | A convivencia entre modulos novos, routers legados e proxies indica migracao incremental. | Inferida |

## O que esta parcialmente implementado

| Alvo | Estado real | Lacuna atual | Status |
| --- | --- | --- | --- |
| Fluxo `router -> service -> repository -> database` | Existe em partes dos modulos modernos. | Ainda ha routers e services chamando `db/*.py` diretamente, e `db/*.py` muitas vezes so encaminha para `database.py`. | Confirmada pelo codigo |
| Repositories encapsulando SQL | Alguns repositories existem. | Grande parte da persistencia ainda esta em `database.py`; varias fachadas em `db/` sao proxies. | Confirmada pelo codigo |
| Services concentrando regras de negocio | Ha services em `modules/*` e em `services/`. | Regras ainda aparecem espalhadas entre services globais, routers, policies e banco legado. | Confirmada pelo codigo |
| Schemas por modulo | Varios modulos possuem `schemas.py`. | `models.py` global ainda concentra contratos de varios dominios. | Confirmada pelo codigo |
| Models por modulo | Alguns modulos possuem `models.py`. | Nem todos os dominios usam entidades explicitas; muitos fluxos ainda trafegam dicionarios. | Confirmada pelo codigo |
| Separacao de dominios | Ha dominios em `modules/`. | Alguns dominios continuam em `routers/`, `services/`, `database.py` e arquivos de raiz. | Confirmada pelo codigo |
| Reducao de arquivos grandes | Parte da logica foi dividida. | Persistem arquivos grandes como `database.py`, `routers/admin_router.py`, `routers/apc_router.py`, `services/pcpi_service.py`, `services/preconselho_service.py` e `services/ocorrencia_pdf_service.py`. | Confirmada pelo codigo |
| Modulo de impressao modular | `modules/printing` esta bem estruturado. | Ainda existe `routers/impressao_router.py` e arquivos de compatibilidade/duplicacao como `_job_creation.py`, `_job_access.py` e `_policies.py`. | Confirmada pelo codigo |
| Modulo de agendamento modular | `modules/scheduling` possui camadas e models. | Ainda depende de `db/agendamento.py`, configuracoes compartilhadas e integracoes externas ao modulo. | Confirmada pelo codigo |
| Operacao do worker | Worker esta isolado em `services/worker.py`. | A decisao entre worker embutido e externo depende de configuracao/runtime; o desenho operacional final precisa ser validado. | Pendente de validacao |

## O que ainda nao foi implementado

| Alvo declarado | Estado observado | Status |
| --- | --- | --- |
| Pasta `app/` como raiz da aplicacao | O projeto ainda usa arquivos e pastas na raiz: `main.py`, `database.py`, `models.py`, `auth.py`, `modules/`, `routers/`, `services/`. | Confirmada pelo codigo |
| Pasta `core/` com `config.py`, `database.py`, `security.py`, `exceptions.py` | Nao ha uma pasta `core/` equivalente. O papel de banco e inicializacao ainda esta dividido entre `database.py`, `db/core.py`, `db/bootstrap.py` e `main.py`. | Confirmada pelo codigo |
| Pasta `shared/` para dependencias compartilhadas | Nao ha uma pasta `shared/` equivalente. Dependencias comuns estao principalmente em `routers/common.py` e `routers/config.py`. | Confirmada pelo codigo |
| `modules/auth` | Autenticacao ainda esta principalmente em `auth.py` e `services/auth_service.py`. | Confirmada pelo codigo |
| `modules/users` | Usuarios ainda aparecem em `db/usuarios.py`, `routers/admin_router.py`, `routers/professores_router.py` e funcoes de `database.py`. | Confirmada pelo codigo |
| `modules/resources` | Recursos aparecem ligados a agendamento/banco, mas nao ha modulo `modules/resources`. | Confirmada pelo codigo |
| `modules/reports` | Relatorios ainda estao em `routers/relatorios_router.py`, `db/relatorios.py` e possivelmente services relacionados. | Confirmada pelo codigo |
| `core/database.py` como ponto unico de conexao | Existe `db/core.py`, mas a base real segue centrada em `database.py`. | Confirmada pelo codigo |
| Queries exclusivamente em repositories | Ainda ha persistencia concentrada em `database.py` e exposta por proxies em `db/`. | Confirmada pelo codigo |
| Remocao dos mecanismos de compatibilidade legados | Reexports em `main.py`, proxies em `db/` e routers legados ainda existem. | Confirmada pelo codigo |

## Divergencias entre alvo e codigo real

| Divergencia | Alvo em `AGENTS.md`/`ARCHITECTURE.md` | Codigo real | Classificacao |
| --- | --- | --- | --- |
| Estrutura raiz | Alvo sugere `app/` com `core/`, `shared/` e `modules/`. | O projeto permanece com `main.py`, `database.py`, `models.py`, `auth.py`, `routers/`, `services/`, `db/` e `modules/` na raiz. | Confirmada pelo codigo |
| Banco central | Alvo sugere conexao central em `core/database.py` e queries nos repositories. | `database.py` concentra criacao de schema, compatibilidade, seeds e muitas queries; `db/*.py` reexporta/proxy. | Confirmada pelo codigo |
| Dependencias compartilhadas | Alvo sugere `shared/dependencies.py`. | Dependencias e permissao compartilhada estao em `routers/common.py`, que e importado por modulos. | Confirmada pelo codigo |
| Contratos de dados | Alvo sugere `schemas.py` por modulo. | Existem schemas modulares, mas `models.py` global ainda concentra schemas de varios dominios. | Confirmada pelo codigo |
| Nomenclatura | Alvo prefere nomes em ingles. | Ha mistura de ingles e portugues: `printing`, `scheduling`, `preconselho`, `ocorrencias`, `usuarios`, `agendamento`. | Confirmada pelo codigo |
| Tamanho de arquivos | Alvo recomenda revisar arquivos acima de 300 linhas. | Ha varios arquivos muito grandes em routers, services e banco. | Confirmada pelo codigo |
| `admin` como interface sobre dominios | Alvo orienta evitar duplicar regra em admin. | `routers/admin_router.py` e grande e concentra varias operacoes administrativas. | Confirmada pelo codigo |
| JavaScript sem regra critica | Alvo exige validacao final no backend. | Nao foi feita auditoria completa de todos os JS nesta etapa. | Pendente de validacao |

## Contradicoes ou tensoes atuais

| Ponto | Tensao observada | Classificacao |
| --- | --- | --- |
| `database.py` versus repositories | A arquitetura alvo quer repositories por modulo, mas o codigo real ainda depende de um arquivo central de banco. | Confirmada pelo codigo |
| `routers.common` versus `shared` | A arquitetura alvo separa dependencias compartilhadas em `shared/`, mas modulos modernos importam dependencias de `routers.common`. | Confirmada pelo codigo |
| Reexports em `main.py` versus modularidade | A arquitetura alvo favorece isolamento por modulo, mas `main.py` reexporta funcoes de varios dominios. | Confirmada pelo codigo |
| Refatorar printing por ultimo versus printing ja modularizado | `AGENTS.md` recomenda deixar `printing` para depois por ser critico, mas o modulo `modules/printing` ja existe e parece bem avancado. | Confirmada pelo codigo |
| Evitar duplicacao versus arquivos de transicao | O modulo de impressao tem arquivos publicos e arquivos com prefixo `_` com nomes semelhantes, sugerindo compatibilidade/transicao. | Inferida |
| `db/` como schema/migrations versus `db/` como proxy | `ARCHITECTURE.md` descreve `db/` como estrutura de banco/migrations, mas hoje `db/` tambem e fachada de persistencia por dominio. | Confirmada pelo codigo |
| Modulo `preconselho` e service legado | Existe `modules/preconselho`, mas tambem `services/preconselho_service.py` e possivelmente router legado relacionado. | Confirmada pelo codigo |

## Pontos que precisam de decisao

| Decisao pendente | Por que importa | Classificacao |
| --- | --- | --- |
| Manter ou nao a pasta `app/` como objetivo real | O alvo documentado mostra `app/`, mas o repositorio atual opera na raiz. Mover tudo seria mudanca estrutural grande. | Pendente de validacao |
| Criar `core/` e `shared/` ou adaptar o alvo ao layout atual | Hoje existem `db/core.py`, `routers/common.py` e `routers/config.py`; e preciso decidir se isso sera migrado ou documentado como padrao intermediario. | Pendente de validacao |
| Definir estrategia para `database.py` | E preciso decidir se ele continuara como compatibilidade central ou se sera drenado gradualmente para repositories. | Pendente de validacao |
| Definir papel definitivo de `db/*.py` | Hoje os arquivos atuam como proxies/fachadas. O alvo sugere repositories nos modulos. | Pendente de validacao |
| Definir quando remover reexports de `main.py` | Reexports ajudam compatibilidade, mas mantem acoplamento. Precisa saber quem ainda depende deles. | Pendente de validacao |
| Definir tratamento de `models.py` global | Pode permanecer como contrato legado ou ser dividido aos poucos por dominio. | Pendente de validacao |
| Definir padrao de permissao compartilhada | Hoje `routers.common` e usado por routers e modulos. O alvo sugere dependencia compartilhada fora da camada de router. | Pendente de validacao |
| Definir destino dos routers legados | `auth.py`, `ocorrencias_router.py`, `pcpi_router.py` e routers em `routers/` ainda sustentam comportamento real. | Pendente de validacao |
| Definir se arquivos de compatibilidade do `modules/printing` ainda sao necessarios | Arquivos como `_job_creation.py`, `_job_access.py` e `_policies.py` precisam de validacao antes de qualquer remocao. | Pendente de validacao |
| Definir padrao de nomenclatura gradual | Ha mistura de portugues e ingles; mudar nomes pode afetar imports, testes e entendimento da equipe. | Pendente de validacao |
| Definir operacao oficial do worker | O sistema suporta worker embutido e externo; a arquitetura alvo precisa refletir o modo adotado em producao. | Pendente de validacao |

## Leitura por modulo em relacao ao alvo

| Modulo/area | Aderencia atual ao alvo | Classificacao |
| --- | --- | --- |
| Impressao | Alta em estrutura modular, mas ainda com compatibilidade em router legado, services globais e worker. | Parcialmente implementado |
| Agendamento | Boa estrutura modular, com router/service/repository/schemas/models, mas ainda com proxies de banco e dependencias externas. | Parcialmente implementado |
| Auditoria | Estrutura modular clara, menor que os dominios principais. | Parcialmente implementado |
| Ocorrencias | Estrutura modular existe, mas integra com services, db e regras externas. | Parcialmente implementado |
| Pre-conselho | Modulo existe, mas convive com services e estruturas legadas. | Parcialmente implementado |
| APC/revisao APC | Parte esta em modulo `apc_review`, mas o fluxo APC ainda usa router/service globais. | Parcialmente implementado |
| Autenticacao | Ainda nao esta em `modules/auth`; permanece em arquivo de raiz e service global. | Nao implementado no alvo modular |
| Usuarios | Ainda nao esta em `modules/users`; aparece distribuido entre admin, professores, db e database. | Nao implementado no alvo modular |
| Recursos | Ainda nao ha `modules/resources` dedicado. | Nao implementado no alvo modular |
| Relatorios | Ainda nao ha `modules/reports` dedicado. | Nao implementado no alvo modular |

## Diretriz de continuidade

A diretriz ja escrita em `AGENTS.md` continua coerente com o estado real: evoluir por etapas pequenas, por modulo, preservando rotas publicas, banco, templates e JavaScript. O codigo atual mostra que a migracao ja comecou; a proxima decisao importante nao e reescrever, mas escolher quais mecanismos de compatibilidade continuam oficiais durante a transicao.

Classificacao: **Inferida** a partir da comparacao entre alvo e codigo real.
