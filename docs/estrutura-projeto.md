# Estrutura do Projeto

## Objetivo

Este documento descreve como o projeto esta organizado depois dos sete sprints de refatoracao, quais camadas existem hoje e quais foram as melhorias estruturais mais relevantes.

## Panorama atual

Os principais blocos de codigo estao distribuidos assim:

- Python da aplicacao principal: `19.217` linhas
- Frontend JavaScript: `12.028` linhas
- CSS: `4.347` linhas
- Templates HTML: `2.238` linhas
- Migrations versionadas: `1.170` linhas
- Testes automatizados: `3.196` linhas

Pontos de concentracao ainda importantes:

- [database.py](/Users/lucassbaraini/sistema-impress/database.py:1): `8.184` linhas
- [ocorrencias_router.py](/Users/lucassbaraini/sistema-impress/ocorrencias_router.py:1): `1.416` linhas
- [preconselho_router.py](/Users/lucassbaraini/sistema-impress/preconselho_router.py:1): `877` linhas
- [models.py](/Users/lucassbaraini/sistema-impress/models.py:1): `770` linhas
- [main.py](/Users/lucassbaraini/sistema-impress/main.py:1): `166` linhas

O ganho principal da refatoracao foi deslocar a complexidade para camadas especializadas, deixando os arquivos de entrada e os pontos de costura menores e mais previsiveis.

## Mapa de diretorios

Estrutura funcional atual:

```text
.
├── app_logging.py
├── auth.py
├── main.py
├── worker_main.py
├── database.py
├── models.py
├── db/
├── routers/
├── services/
├── migrations/
├── templates/
├── static/
│   ├── css/
│   └── js/
├── tests/
├── deploy/
├── docs/
└── .github/workflows/
```

Responsabilidade de cada area:

- `main.py`: bootstrap da API, `lifespan`, `include_router` e inicializacao controlada.
- `worker_main.py`: entrypoint do worker externo.
- `auth.py`: autenticacao HTTP e dependencia de usuario logado.
- `database.py`: implementacao legada/compativel do acesso a dados e bootstrap base do schema.
- `models.py`: modelos Pydantic de entrada e saida.
- `db/`: fronteira publica do acesso a dados por dominio.
- `routers/`: routers modulares da aplicacao web e helpers compartilhados.
- `services/`: regras de negocio, integracoes e logica de processamento.
- `migrations/`: evolucao versionada de schema.
- `templates/`: HTML renderizado pelo backend.
- `static/js/`: scripts por pagina e modulos compartilhados do frontend.
- `static/css/`: bundle CSS e folhas separadas por contexto visual.
- `tests/`: suite `unittest`.
- `deploy/`: artefatos de `systemd` e Nginx.
- `.github/workflows/`: CI e deploy.
- `docs/`: guias, relatorios e historico de refatoracao.

## Backend

### Entradas da aplicacao

- [main.py](/Users/lucassbaraini/sistema-impress/main.py:107) controla startup, cria tabelas, aplica seeds basicos e sobe o worker embutido quando configurado.
- [worker_main.py](/Users/lucassbaraini/sistema-impress/worker_main.py:10) inicializa o bootstrap do banco e entra no loop de impressao.
- [app_logging.py](/Users/lucassbaraini/sistema-impress/app_logging.py:1) centraliza o logging para API e worker.

### HTTP e roteamento

O projeto passou a ter uma camada de routers bem mais clara:

- [routers/system_router.py](/Users/lucassbaraini/sistema-impress/routers/system_router.py:1): raiz, `/health`, `/me` e endpoint interno do RADIUS.
- [routers/pages_router.py](/Users/lucassbaraini/sistema-impress/routers/pages_router.py:1): paginas HTML.
- [routers/impressao_router.py](/Users/lucassbaraini/sistema-impress/routers/impressao_router.py:1): impressao, fila e preview.
- [routers/agendamento_router.py](/Users/lucassbaraini/sistema-impress/routers/agendamento_router.py:1): recursos e reservas.
- [routers/professores_router.py](/Users/lucassbaraini/sistema-impress/routers/professores_router.py:1): cadastro publico e recuperacao de senha.
- [routers/admin_router.py](/Users/lucassbaraini/sistema-impress/routers/admin_router.py:1): operacao administrativa.
- [ocorrencias_router.py](/Users/lucassbaraini/sistema-impress/ocorrencias_router.py:1), [pcpi_router.py](/Users/lucassbaraini/sistema-impress/pcpi_router.py:1) e [preconselho_router.py](/Users/lucassbaraini/sistema-impress/preconselho_router.py:1): modulos de dominio ainda fora de `routers/`, mas ja desacoplados de `main.py`.

Helpers compartilhados de autorizacao e validacao:

- [routers/common.py](/Users/lucassbaraini/sistema-impress/routers/common.py:1)
- [routers/professores_common.py](/Users/lucassbaraini/sistema-impress/routers/professores_common.py:1)
- [routers/config.py](/Users/lucassbaraini/sistema-impress/routers/config.py:1)

### Regra de negocio

Os services concentram comportamento reutilizavel e integracoes:

- autenticacao: [services/auth_service.py](/Users/lucassbaraini/sistema-impress/services/auth_service.py:1)
- cotas: [services/cota_service.py](/Users/lucassbaraini/sistema-impress/services/cota_service.py:1)
- impressao e spool: [services/file_service.py](/Users/lucassbaraini/sistema-impress/services/file_service.py:1), [services/pdf_service.py](/Users/lucassbaraini/sistema-impress/services/pdf_service.py:1), [services/printer.py](/Users/lucassbaraini/sistema-impress/services/printer.py:1), [services/worker.py](/Users/lucassbaraini/sistema-impress/services/worker.py:1)
- importacoes: [services/csv_import_service.py](/Users/lucassbaraini/sistema-impress/services/csv_import_service.py:1), [services/atribuicoes_docentes_import_service.py](/Users/lucassbaraini/sistema-impress/services/atribuicoes_docentes_import_service.py:1)
- dominios educacionais: [services/preconselho_service.py](/Users/lucassbaraini/sistema-impress/services/preconselho_service.py:1), [services/pcpi_service.py](/Users/lucassbaraini/sistema-impress/services/pcpi_service.py:1), [services/ocorrencia_disciplina_service.py](/Users/lucassbaraini/sistema-impress/services/ocorrencia_disciplina_service.py:1), [services/ocorrencia_pdf_service.py](/Users/lucassbaraini/sistema-impress/services/ocorrencia_pdf_service.py:1)
- integracao RADIUS: [services/radius_service.py](/Users/lucassbaraini/sistema-impress/services/radius_service.py:1)

### Acesso a dados

O projeto nao usa mais imports diretos de `database.py` dentro de routers e services. A fronteira oficial agora esta em [db/](/Users/lucassbaraini/sistema-impress/db):

- [db/bootstrap.py](/Users/lucassbaraini/sistema-impress/db/bootstrap.py:1)
- [db/usuarios.py](/Users/lucassbaraini/sistema-impress/db/usuarios.py:1)
- [db/catalogos.py](/Users/lucassbaraini/sistema-impress/db/catalogos.py:1)
- [db/impressao.py](/Users/lucassbaraini/sistema-impress/db/impressao.py:1)
- [db/agendamento.py](/Users/lucassbaraini/sistema-impress/db/agendamento.py:1)
- [db/docencia.py](/Users/lucassbaraini/sistema-impress/db/docencia.py:1)
- [db/ocorrencias.py](/Users/lucassbaraini/sistema-impress/db/ocorrencias.py:1)
- [db/preconselho.py](/Users/lucassbaraini/sistema-impress/db/preconselho.py:1)
- [db/pcpi.py](/Users/lucassbaraini/sistema-impress/db/pcpi.py:1)
- [db/core.py](/Users/lucassbaraini/sistema-impress/db/core.py:1)

Hoje esses modulos ainda atuam como fachada/proxy sobre [database.py](/Users/lucassbaraini/sistema-impress/database.py:1), mas esse foi um passo importante para isolar dependencias e preparar extracoes futuras sem mexer nos consumidores.

### Banco e migrations

O fluxo de schema ficou mais previsivel:

- [database.py](/Users/lucassbaraini/sistema-impress/database.py:268) faz o bootstrap base do schema.
- [db/schema_migrations.py](/Users/lucassbaraini/sistema-impress/db/schema_migrations.py:1) registra e aplica migrations versionadas.
- [migrations/](/Users/lucassbaraini/sistema-impress/migrations) concentra a evolucao do banco.

Estado atual:

- instalacoes novas sobem com schema atual sem replay manual de todo o historico
- instalacoes existentes passam a registrar historico em `schema_migrations`
- os helpers `_garantir_colunas_*` ainda existem como camada de compatibilidade temporaria

## Frontend

### Templates

Os templates HTML estao em [templates/](/Users/lucassbaraini/sistema-impress/templates):

- autenticacao: `login.html`, `cadastro_professor.html`
- hub: `servicos.html`
- modulos: `printing/index.html`, `scheduling/index.html`, `scheduling/my_bookings.html`, `scheduling/calendar.html`, `preconselho/index.html`, `admin.html`, `coordenacao.html`, `pcpi.html`
- compartilhado: [templates/includes/style_bundle.html](/Users/lucassbaraini/sistema-impress/templates/includes/style_bundle.html:1)

O carregamento do CSS foi centralizado no include compartilhado, reduzindo repeticao nos `head` das paginas.

### JavaScript

O frontend ganhou um nucleo compartilhado em [static/js/core/](/Users/lucassbaraini/sistema-impress/static/js/core):

- [api.js](/Users/lucassbaraini/sistema-impress/static/js/core/api.js:1)
- [auth.js](/Users/lucassbaraini/sistema-impress/static/js/core/auth.js:1)
- [dom.js](/Users/lucassbaraini/sistema-impress/static/js/core/dom.js:1)
- [formatters.js](/Users/lucassbaraini/sistema-impress/static/js/core/formatters.js:1)

Os antigos monolitos de admin e coordenacao viraram entrypoints minimos:

- [static/js/admin.js](/Users/lucassbaraini/sistema-impress/static/js/admin.js:1)
- [static/js/coordenacao.js](/Users/lucassbaraini/sistema-impress/static/js/coordenacao.js:1)

E a logica foi distribuida em modulos por contexto:

- [static/js/admin/](/Users/lucassbaraini/sistema-impress/static/js/admin)
- [static/js/coordenacao/](/Users/lucassbaraini/sistema-impress/static/js/coordenacao)

### CSS

O CSS foi dividido em:

- [static/css/base.css](/Users/lucassbaraini/sistema-impress/static/css/base.css:1)
- [static/css/design-system.css](/Users/lucassbaraini/sistema-impress/static/css/design-system.css:1): classes canônicas de página e componentes
- [docs/09-frontend/design-system-classes.md](/Users/lucassbaraini/sistema-impress/docs/09-frontend/design-system-classes.md:1): referência de uso das classes compartilhadas
- [static/css/pages/auth.css](/Users/lucassbaraini/sistema-impress/static/css/pages/auth.css:1)
- [static/css/pages/professor.css](/Users/lucassbaraini/sistema-impress/static/css/pages/professor.css:1)
- [static/css/pages/services-scheduler.css](/Users/lucassbaraini/sistema-impress/static/css/pages/services-scheduler.css:1)
- [static/css/pages/pcpi-preconselho.css](/Users/lucassbaraini/sistema-impress/static/css/pages/pcpi-preconselho.css:1)
- [static/css/pages/admin.css](/Users/lucassbaraini/sistema-impress/static/css/pages/admin.css:1)
- [static/css/pages/coordenacao.css](/Users/lucassbaraini/sistema-impress/static/css/pages/coordenacao.css:1)

O entrypoint [static/css/style.css](/Users/lucassbaraini/sistema-impress/static/css/style.css:1) foi preservado como agregador para nao quebrar o carregamento existente.

## Qualidade, testes e operacao

### Qualidade

- [pyproject.toml](/Users/lucassbaraini/sistema-impress/pyproject.toml:1): configuracao do `ruff`
- [Makefile](/Users/lucassbaraini/sistema-impress/Makefile:1): comandos padrao
- [CONTRIBUTING.md](/Users/lucassbaraini/sistema-impress/CONTRIBUTING.md:1): fluxo de contribuicao

Comandos oficiais:

- `make lint`
- `make test`
- `make check`
- `make migrate`
- `make migrations-status`

### Testes

A suite continua em `unittest`, em [tests/](/Users/lucassbaraini/sistema-impress/tests), cobrindo:

- autenticacao
- NT hash / RADIUS
- importacoes
- atribuicoes docentes
- PCPI
- pre-conselho
- ocorrencias
- healthcheck operacional

### Deploy e runtime

- CI: [.github/workflows/ci.yml](/Users/lucassbaraini/sistema-impress/.github/workflows/ci.yml:1)
- deploy: [.github/workflows/deploy.yml](/Users/lucassbaraini/sistema-impress/.github/workflows/deploy.yml:1)
- `systemd`: [deploy/systemd/](/Users/lucassbaraini/sistema-impress/deploy/systemd)
- Nginx: [deploy/nginx/sistema-impress.conf](/Users/lucassbaraini/sistema-impress/deploy/nginx/sistema-impress.conf:1)
- guia local: [DEPLOY_LOCAL.md](/Users/lucassbaraini/sistema-impress/DEPLOY_LOCAL.md:1)

O endpoint [routers/system_router.py](/Users/lucassbaraini/sistema-impress/routers/system_router.py:30) agora verifica:

- estado do bootstrap
- acesso ao banco
- migrations pendentes
- uptime da aplicacao
- modo do worker

## Principais melhorias realizadas

### 1. Reducao de acoplamento

- `main.py` deixou de concentrar praticamente toda a API.
- routers e services nao dependem mais diretamente de `database.py`.
- frontend parou de repetir helpers de sessao, API e DOM em cada pagina.

### 2. Melhor separacao por dominio

- backend com fronteiras por `routers/`, `services/` e `db/`
- frontend dividido por `core`, modulos administrativos e modulos de coordenacao
- CSS separado por contexto visual

### 3. Melhora de previsibilidade operacional

- CI obrigatoria antes do deploy
- deploy com etapa de migrations e healthcheck
- logging padronizado em API e worker
- healthcheck com verificacao real

### 4. Melhora de manutenibilidade

- comandos padronizados de validacao
- historico de refatoracao documentado em [docs/refatoracao/](/Users/lucassbaraini/sistema-impress/docs/refatoracao)
- bundle visual mais facil de evoluir
- ponto oficial para criar/registrar migrations

## Dividas tecnicas remanescentes

O projeto melhorou muito, mas ainda ha pontos que merecem proximos ciclos:

- [database.py](/Users/lucassbaraini/sistema-impress/database.py:1) ainda e grande e acumula legado + bootstrap + compatibilidade.
- [models.py](/Users/lucassbaraini/sistema-impress/models.py:1) ainda esta centralizado demais.
- [ocorrencias_router.py](/Users/lucassbaraini/sistema-impress/ocorrencias_router.py:1), [pcpi_router.py](/Users/lucassbaraini/sistema-impress/pcpi_router.py:1) e [preconselho_router.py](/Users/lucassbaraini/sistema-impress/preconselho_router.py:1) ainda podem migrar para o pacote `routers/`.
- Parte do schema ainda depende do backstop de compatibilidade em `_garantir_colunas_*`.

## Resumo executivo

Depois dos sete sprints, o projeto saiu de uma estrutura muito concentrada em poucos arquivos para uma organizacao por camadas e dominios, com melhor isolamento entre API, regra de negocio, dados, frontend e operacao. O comportamento foi preservado, mas o custo de manutencao caiu porque hoje existe um lugar claro para cada tipo de mudanca.
