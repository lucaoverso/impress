# Guia de Commits e Alteracoes

## Objetivo

Este guia define um padrao simples para registrar mudancas no projeto de forma legivel, revisavel e segura.

O foco nao e escrever commits "bonitos", e sim produzir historico util para:

- entender rapidamente o que mudou
- revisar com menos risco
- localizar regressao com mais facilidade
- separar mudanca funcional de mudanca estrutural

## Principios

- cada commit deve contar uma historia pequena e completa
- uma alteracao deve ter um objetivo claro
- refatoracao, regra de negocio e ajuste visual nao devem ser misturados sem necessidade
- testes e documentacao devem acompanhar a mudanca quando fizer sentido
- o historico deve explicar a intencao, nao apenas repetir o nome do arquivo

## Tamanho ideal da alteracao

Prefira alteracoes pequenas a medias.

Uma entrega boa para este projeto normalmente:

- resolve um problema especifico
- afeta um modulo ou fluxo principal
- inclui testes quando ha mudanca de comportamento
- atualiza documentacao quando o uso ou a operacao mudam

Evite no mesmo commit:

- refatorar estrutura e mudar regra de negocio ao mesmo tempo
- alterar backend, frontend e banco sem relacao direta
- incluir arquivos temporarios, lixo de debug ou renomeacoes incidentais

## Padrao de mensagem de commit

Use o formato:

```text
tipo(escopo): resumo curto no imperativo
```

Exemplos:

```text
feat(preconselho): adiciona validacao de fechamento por etapa
fix(router): corrige filtro de turmas sem professor vinculado
refactor(preconselho): extrai montagem textual para service dedicado
test(preconselho): cobre consolidacao de observacoes por estudante
docs(contributing): adiciona guia de commits e alteracoes
chore(ci): ajusta comando de validacao no workflow
```

### Tipos recomendados

- `feat`: nova funcionalidade
- `fix`: correcao de bug
- `refactor`: reorganizacao sem mudar comportamento esperado
- `test`: adicao ou ajuste de testes
- `docs`: mudanca de documentacao
- `style`: ajuste de formatacao ou estilo sem impacto funcional
- `chore`: manutencao tecnica, tooling ou rotina operacional

### Escopo recomendado

O escopo deve apontar o contexto principal da mudanca.

Exemplos de escopo neste projeto:

- `preconselho`
- `pcpi`
- `ocorrencias`
- `professores`
- `admin`
- `router`
- `service`
- `db`
- `migrations`
- `docs`

Se a mudanca for muito transversal e nao houver um escopo claro, pode usar:

```text
fix: corrige tratamento de erro na autenticacao
```

## Como escrever um bom resumo

Prefira verbos diretos:

- `adiciona`
- `corrige`
- `extrai`
- `padroniza`
- `remove`
- `documenta`

Evite resumos vagos como:

- `ajustes`
- `melhorias`
- `update`
- `corrigindo coisas`
- `pre conselho mvp 2.0`

Esses textos nao ajudam a entender impacto nem intencao.

## Quando separar em mais de um commit

Separe commits quando houver mudancas de natureza diferente.

Exemplos bons de separacao:

- commit 1: cria migration
- commit 2: adapta camada `db/` e `services/`
- commit 3: cobre fluxo com testes
- commit 4: atualiza tutorial ou guia operacional

Tambem vale separar quando:

- a refatoracao prepara terreno para uma correcao posterior
- a mudanca de layout e independente da mudanca de regra
- ha renomeacao grande de arquivo sem alteracao funcional

## Ordem recomendada para mudancas maiores

Quando a entrega nao couber bem em um unico commit, prefira esta sequencia:

1. preparacao estrutural ou refatoracao segura
2. mudanca funcional principal
3. testes
4. documentacao

Isso deixa a revisao mais simples e reduz ruido.

## Checklist antes de commitar

Antes de criar o commit, confirme:

- a alteracao tem um objetivo claro
- nao existem arquivos temporarios ou acidentais no diff
- o commit nao mistura assuntos sem relacao
- os testes relevantes foram executados
- a mensagem do commit explica a intencao

Se aplicavel, rode:

```text
make test
make lint
make check
make migrate
make migrations-status
```

No Windows sem `make`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m db.schema_migrations upgrade
.\.venv\Scripts\python.exe -m db.schema_migrations status
```

## Regras praticas para este repositorio

### Mudanca de schema

Se alterou banco:

- a mudanca deve nascer em `migrations/`
- o acesso a dados deve ficar em `db/`
- testes relevantes devem cobrir o comportamento novo
- nao esconda schema novo apenas em helpers de compatibilidade

Mensagem sugerida:

```text
feat(migrations): cria tabela de consolidacao do preconselho
```

### Mudanca de regra de negocio

Se alterou comportamento:

- concentre a regra em `services/` quando houver reutilizacao
- deixe o router responsavel por orquestracao
- adicione ou ajuste teste do fluxo principal

Mensagem sugerida:

```text
fix(preconselho): evita duplicidade de observacoes por disciplina
```

### Mudanca visual ou de pagina

Se alterou template, JS ou CSS:

- mantenha o escopo do modulo afetado
- nao misture com refatoracao de backend sem dependencia real
- documente se houver impacto no uso

Mensagem sugerida:

```text
feat(preconselho): destaca estudantes com pendencias na tela
```

## O que evitar

- commit gigante com varios assuntos
- commit com nome generico
- commit quebrando teste conhecido sem registrar contexto
- misturar formatacao em massa com correcao funcional
- incluir arquivos gerados, temporarios ou dados locais
- adiar teste essencial para "depois"

## Padrao para pull requests ou entregas agrupadas

Mesmo quando varios commits fizerem parte da mesma entrega, o conjunto deve responder claramente:

- qual problema estamos resolvendo
- qual foi a estrategia
- como validar
- quais riscos ou impactos existem

Um bom resumo de PR ou entrega pode seguir este modelo:

```text
Contexto
- corrige inconsistencias na consolidacao textual do preconselho

O que mudou
- extrai regra para service
- ajusta endpoint de consolidacao
- adiciona cobertura de testes

Como validar
- executar testes do modulo
- revisar fluxo da tela de preconselho

Riscos
- impacto em textos previamente consolidados
```

## Regra de ouro

Se alguem abrir o historico daqui a tres meses, o commit deve responder sem esforco:

- o que mudou
- por que mudou
- onde a mudanca aconteceu

Se a mensagem nao ajuda nisso, ela ainda pode ser melhor.
