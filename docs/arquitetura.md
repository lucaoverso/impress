# Arquitetura Alvo da Refatoracao

## Objetivo

Este documento define a arquitetura modular desejada para o projeto durante os proximos ciclos de refatoracao. O foco e reduzir acoplamento, tornar o codigo mais previsivel e facilitar manutencao sem alterar comportamento funcional durante a migracao.

## Principios

- preservar comportamento existente a cada passo
- trabalhar em pequenos commits reversiveis
- evitar refatoracoes largas em multiplos dominios ao mesmo tempo
- separar HTTP, regra de negocio, acesso a dados e contratos de dados
- tratar `database.py` como legado temporario, esvaziando-o aos poucos
- manter a arquitetura nova convivendo com o legado ate a migracao completa

## Estrutura de transicao

Durante a fase inicial da refatoracao, o projeto sera organizado por camadas tecnicas:

```text
core/
db/
repositories/
schemas/
routers/
services/
templates/
static/
```

Essa estrutura de transicao existe para:

- reduzir acoplamento
- esvaziar `database.py` aos poucos
- separar responsabilidades sem reorganizacao fisica ampla
- criar um destino previsivel para cada tipo de mudanca

Papel de cada camada:

- `core/`: configuracao, seguranca, dependencias e regras transversais
- `db/`: bootstrap, sessao, base e compatibilidade com acesso legado
- `repositories/`: fronteira de persistencia por dominio
- `schemas/`: contratos, DTOs e validacao estrutural
- `routers/`: rotas HTTP e traducao de request/response
- `services/`: regra de negocio e orquestracao
- `templates/`: HTML renderizado
- `static/`: recursos de frontend

## Direcao futura

Depois que os dominios estiverem mais estaveis e com fronteiras claras, os modulos maiores poderao migrar para uma estrutura modular por dominio.

Exemplo de direcao futura:

```text
modules/
  ocorrencias/
  preconselho/
  impressao/
  agendamento/
```

Dentro de cada modulo estabilizado, o padrao esperado passa a ser:

```text
modules/<dominio>/
  router.py
  service.py
  repository.py
  schemas.py
```

Arquivos especializados continuam validos quando houver necessidade:

```text
modules/<dominio>/
  pdf_service.py
  quota_service.py
  queue_service.py
  conflict_service.py
```

Nem todo dominio precisara de todos os arquivos auxiliares, mas o padrao principal permanece:

- `router.py`: rotas HTTP e orquestracao da requisicao
- `service.py`: regras de negocio
- `repository.py`: acesso ao banco
- `schemas.py`: validacao, DTOs e contratos de entrada/saida
- arquivos especificos como `pdf_service.py`: detalhes tecnicos especializados

## Responsabilidades de cada camada

### `router.py`

Responsavel por:

- declarar endpoints
- receber parametros HTTP
- validar autenticacao e autorizacao
- chamar services
- montar respostas HTTP

Nao deve:

- implementar regra de negocio complexa
- acessar banco diretamente
- conhecer detalhes internos de SQL ou persistencia

### `service.py`

Responsavel por:

- centralizar regra de negocio
- orquestrar chamadas a repositories
- aplicar validacoes de dominio
- isolar integracoes externas
- preparar dados para exportacao, relatorios ou PDF

Nao deve:

- depender de objetos HTTP do framework quando isso puder ser evitado
- concentrar acesso SQL bruto
- virar deposito generico de funcoes sem coesao

### `repository.py`

Responsavel por:

- encapsular acesso ao banco
- expor operacoes de leitura e escrita por dominio
- isolar queries, transacoes e detalhes de persistencia
- servir como fronteira entre regra de negocio e legado de dados

Nao deve:

- conter regras de negocio de alto nivel
- montar resposta HTTP
- misturar operacoes de dominios nao relacionados

### `schemas.py`

Responsavel por:

- definir contratos de request e response
- validar formato e tipos
- documentar estruturas trocadas entre camadas
- reduzir dependencia de estruturas soltas como `dict` anonimos

Pode conter:

- DTOs de entrada
- DTOs de saida
- validacoes estruturais
- aliases e tipos auxiliares do dominio

### Arquivos especializados

Arquivos como `pdf_service.py`, `import_service.py`, `worker.py` ou `auth_service.py` continuam validos quando houver motivo tecnico claro. A regra e simples: especializacao e aceitavel quando ela evita inflar um `service.py` generico.

## Fluxo esperado entre camadas

Fluxo preferencial:

```text
HTTP -> router -> service -> repository -> database legado / banco
```

Fluxo com contratos explicitos:

```text
HTTP -> router -> schemas -> service -> repository -> banco
service -> schemas/out -> router -> resposta
```

## Papel temporario de `database.py`

`database.py` deve ser tratado como uma camada legada de compatibilidade. Ele nao sera removido de uma vez. A estrategia correta e:

- interromper crescimento do arquivo
- evitar novos imports diretos em routers e services
- extrair funcoes aos poucos para repositories por dominio
- manter wrappers e adaptadores enquanto existirem consumidores antigos
- apagar trechos legados somente quando houver cobertura suficiente e consumidores migrados

Estado desejado no fim da jornada:

- `database.py` deixa de ser ponto de entrada para o codigo novo
- suas responsabilidades remanescentes ficam restritas a compatibilidade temporaria ou bootstrap residual
- a maior parte da logica de persistencia passa a viver em `repository.py`

## Convivencia com a estrutura atual

Hoje o projeto ja possui `routers/`, `services/` e `db/`, alem de arquivos legados grandes na raiz. A arquitetura alvo nao exige uma ruptura abrupta. A migracao deve respeitar duas etapas:

1. consolidar primeiro a estrutura por camadas tecnicas
2. modularizar por dominio apenas depois da estabilizacao

Na pratica, a migracao pode seguir esta ordem:

- manter arquivos atuais funcionando
- criar `core/`, `repositories/` e `schemas/` como destino das extracoes
- mover chamadas aos poucos para a nova camada tecnica
- estabilizar com testes
- remover somente o trecho legado que deixou de ser usado
- avaliar modularizacao fisica por dominio apenas quando o fluxo ja estiver desacoplado

## Regras de transicao

- nao mover arquivos em massa
- nao renomear funcoes existentes sem necessidade forte
- nao misturar extracao estrutural com mudanca funcional
- cada commit deve ter escopo pequeno e validacao objetiva
- sempre que possivel, migrar um fluxo completo por vez

## Padrao sugerido por dominio

Exemplo da fase de transicao para um dominio `ocorrencias`:

```text
routers/ocorrencias_router.py
services/ocorrencias_service.py
services/ocorrencias_pdf_service.py
repositories/ocorrencias_repository.py
schemas/ocorrencias_schemas.py
```

Exemplo da fase futura modularizada:

```text
modules/ocorrencias/
  router.py
  service.py
  repository.py
  schemas.py
  pdf_service.py
```

Distribuicao de responsabilidade:

- `routers/ocorrencias_router.py`: endpoints, permissao e traducao HTTP
- `services/ocorrencias_service.py`: regras de cadastro, consulta e fluxo
- `services/ocorrencias_pdf_service.py`: montagem de PDF e exportacoes
- `repositories/ocorrencias_repository.py`: leitura e escrita no banco
- `schemas/ocorrencias_schemas.py`: payloads de entrada e saida

## Beneficios esperados

- menor tamanho medio dos arquivos
- menor impacto colateral de mudancas
- facilidade maior para testes unitarios
- fronteiras mais claras entre camadas
- onboarding mais rapido para manutencao
- menor dependencia do conhecimento historico de `database.py`

## Criterios de sucesso da arquitetura

Um modulo pode ser considerado alinhado com a arquitetura alvo quando:

- o router nao acessa banco diretamente
- a regra de negocio principal esta em service
- o acesso a dados esta encapsulado em repository
- os contratos principais estao definidos em schemas
- a cobertura de testes protege o fluxo migrado
- `database.py` deixa de crescer por causa daquele dominio

## Resumo executivo

A arquitetura desejada e incremental e pragmatica. Primeiro consolidamos a estrutura por camadas tecnicas `core/`, `db/`, `repositories/`, `schemas/`, `routers/` e `services/`. Depois, quando os dominios estiverem mais estaveis, os modulos maiores podem migrar para pacotes em `modules/<dominio>/`. Em todas as etapas, `database.py` permanece como legado temporario a ser esvaziado com seguranca em pequenos commits.
