# Guia para Criacao de Novos Modulos

## Objetivo

Este guia define o caminho recomendado para criar novos modulos sem reintroduzir o acoplamento que foi removido durante a refatoracao.

## Principios

- Novos modulos devem ser orientados por dominio, nao por conveniencia de arquivo.
- Routers nao devem falar direto com `database.py`.
- Mudanca de schema deve nascer como migration versionada.
- Regra de negocio reutilizavel deve ficar em `services/`.
- Pagina nova deve entrar com template, JS e CSS organizados por contexto.
- Toda entrega nova deve sair com testes e documentacao minima.

## Regra de decisao rapida

Quando criar algo novo, use esta referencia:

- precisa de endpoint HTTP: `routers/`
- precisa de regra de negocio: `services/`
- precisa de acesso a dados: `db/`
- precisa mudar schema: `migrations/`
- precisa de pagina HTML: `templates/` + `routers/pages_router.py`
- precisa de comportamento no navegador: `static/js/`
- precisa de estilo visual novo: `static/css/pages/`
- precisa de contrato de request/response: `models.py`

## Estrutura alvo para um modulo novo

Exemplo de um modulo ficticio `estoque`:

```text
routers/estoque_router.py
services/estoque_service.py
db/estoque.py
templates/estoque.html
static/js/estoque.js
static/css/pages/estoque.css
tests/test_estoque_router.py
tests/test_estoque_service.py
migrations/20260412_create_estoque.py
```

Se o frontend crescer:

```text
static/js/estoque.js
static/js/estoque/core.js
static/js/estoque/init.js
static/js/estoque/painel.js
```

## Passo a passo recomendado

### 1. Defina o recorte do dominio

Antes de escrever codigo, responda:

- o modulo e administrativo, operacional ou publico?
- ele tem pagina HTML ou e apenas API?
- ele cria regra de negocio nova ou so organiza CRUD?
- ele precisa persistir dados novos?

Se o modulo tocar mais de um dominio, quebre antes.

### 2. Modele o contrato

Se houver payloads e respostas novas:

- adicione modelos em [models.py](/Users/lucassbaraini/sistema-impress/models.py:1)
- use nomes terminando com `In` e `Out` quando fizer sentido
- mantenha validacoes estruturais no modelo e validacoes de regra no router/service

### 3. Planeje o banco primeiro

Se houver alteracao de schema:

1. crie uma migration em [migrations/](/Users/lucassbaraini/sistema-impress/migrations)
2. exponha o acesso a dados via `db/<dominio>.py`
3. use `database.py` apenas como implementacao subjacente, nunca como dependencia direta do router

Regras importantes:

- novos campos e tabelas devem entrar por migration versionada
- nao adicione novo schema apenas em `_garantir_colunas_*`
- se precisar de backstop de compatibilidade, trate isso como excecao e documente

### 4. Crie a fachada de dados

Em `db/<dominio>.py`:

- exponha funcoes do dominio
- mantenha nomes coerentes com o resto do projeto
- se ainda precisar usar `database.py`, faca isso via proxy/fachada

Padrao preferido:

```python
from ._proxy import proxy

listar_itens_estoque = proxy("listar_itens_estoque")
criar_item_estoque = proxy("criar_item_estoque")
```

### 5. Coloque a regra de negocio em `services/`

Use `services/` quando houver:

- validacao reutilizavel
- importacao/exportacao
- integracao externa
- montagem de relatorios
- logica que nao deve ficar espalhada no router

Routers devem orquestrar a requisicao. Services devem concentrar comportamento.

### 6. Crie o router

Preferencia atual:

- novos routers devem nascer dentro de [routers/](/Users/lucassbaraini/sistema-impress/routers)
- siga o padrao `<dominio>_router.py`

No router:

- use `APIRouter()`
- importe apenas `db/`, `services/`, `models.py` e helpers compartilhados
- reaproveite [routers/common.py](/Users/lucassbaraini/sistema-impress/routers/common.py:1) quando houver regra geral de cargo, validacao ou contexto

Se for um modulo novo de API, lembre de incluir em [main.py](/Users/lucassbaraini/sistema-impress/main.py:1).

### 7. Se houver pagina, ligue a camada web

Para pagina nova:

1. crie `templates/<modulo>.html`
2. adicione a rota HTML em [routers/pages_router.py](/Users/lucassbaraini/sistema-impress/routers/pages_router.py:1)
3. carregue o CSS pelo include:

```html
{% include "includes/style_bundle.html" %}
```

4. carregue os scripts compartilhados de `static/js/core/` antes do script da pagina

### 8. Organize o JavaScript

Para pagina simples:

- crie `static/js/<modulo>.js`

Para pagina media/grande:

- mantenha `static/js/<modulo>.js` como entrypoint minimo
- mova a logica para `static/js/<modulo>/`

Sempre prefira reaproveitar:

- [static/js/core/api.js](/Users/lucassbaraini/sistema-impress/static/js/core/api.js:1)
- [static/js/core/auth.js](/Users/lucassbaraini/sistema-impress/static/js/core/auth.js:1)
- [static/js/core/dom.js](/Users/lucassbaraini/sistema-impress/static/js/core/dom.js:1)
- [static/js/core/formatters.js](/Users/lucassbaraini/sistema-impress/static/js/core/formatters.js:1)

Evite:

- duplicar `fetchJson`
- duplicar logout/sessao
- criar novo monolito JS com milhares de linhas

### 9. Organize o CSS

Se o modulo trouxer estilo proprio:

1. crie `static/css/pages/<modulo>.css`
2. adicione o `@import` correspondente em [static/css/style.css](/Users/lucassbaraini/sistema-impress/static/css/style.css:1)
3. reutilize tokens e estilos base de [static/css/base.css](/Users/lucassbaraini/sistema-impress/static/css/base.css:1)

Evite:

- jogar tudo em `base.css`
- misturar regra global com regra de pagina
- criar seletor generico demais que vaze para outras telas

### 10. Escreva testes

Minimo esperado:

- teste de fluxo principal
- teste de erro relevante
- teste da nova migration, se houver schema

Padroes do repositorio:

- `tests/test_<modulo>_router.py`
- `tests/test_<modulo>_service.py`
- usar `tempfile.TemporaryDirectory()` e `DB_PATH` temporario quando o banco entrar no teste

### 11. Atualize operacao e docs quando necessario

Atualize tambem:

- [docs/](/Users/lucassbaraini/sistema-impress/docs) se o modulo introduzir fluxo novo
- [.env.example](/Users/lucassbaraini/sistema-impress/.env.example:1) se houver nova variavel de ambiente
- [DEPLOY_LOCAL.md](/Users/lucassbaraini/sistema-impress/DEPLOY_LOCAL.md:1) se houver impacto operacional
- [Makefile](/Users/lucassbaraini/sistema-impress/Makefile:1) se houver comando recorrente novo

## Checklists

### Checklist de backend

- [ ] existe model `In`/`Out` quando necessario
- [ ] router novo nao importa `database.py` diretamente
- [ ] regra de negocio nova foi para `services/`
- [ ] acesso a dados foi encapsulado em `db/`
- [ ] migration criada quando houve schema novo
- [ ] `main.py` inclui o router, se aplicavel

### Checklist de frontend

- [ ] template usa `includes/style_bundle.html`
- [ ] pagina reutiliza `static/js/core/`
- [ ] CSS novo entrou em `static/css/pages/`
- [ ] entrypoint JS nao virou monolito
- [ ] nomes de classes seguem o contexto do modulo

### Checklist de qualidade

- [ ] `make lint`
- [ ] `make test`
- [ ] `make migrate` se houve migration
- [ ] documentacao minima atualizada

## O que evitar

- importar `database.py` direto em router ou service
- misturar migration nova com regra escondida em `_garantir_colunas_*`
- colocar logica de negocio complexa dentro do template ou do router
- adicionar CSS global para resolver problema local
- criar pagina nova sem teste do fluxo principal
- usar `main.py` como deposito de endpoint

## Convencao recomendada para novos modulos

Para tudo o que for novo daqui para frente, prefira este padrao:

1. `migrations/`
2. `db/`
3. `services/`
4. `routers/`
5. `templates/`
6. `static/js/`
7. `static/css/pages/`
8. `tests/`
9. `docs/`

Esse fluxo ajuda a manter o projeto coerente com a arquitetura que foi consolidada nos sprints 0 a 7.
