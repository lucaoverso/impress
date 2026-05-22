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
```

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

## Regra pratica de tamanho de arquivo

Durante a refatoracao, usar esta referencia para decidir quando estudar separacao de arquivos:

- ate `200` linhas: tamanho normalmente saudavel
- entre `200` e `300` linhas: manter apenas se a coesao estiver clara
- acima de `300` linhas: estudar separacao obrigatoriamente
- acima de `500` linhas: quase sempre exige divisao por responsabilidade

A separacao deve acontecer por coesao e responsabilidade, nao apenas por contagem de linhas.
Exemplos de cortes validos:

- `service.py`: validacao, casos de uso, montagem textual, integracoes externas
- `repository.py`: leitura, escrita, consultas especializadas
- `schemas.py`: requests, responses, DTOs internos

O objetivo dessa regra e evitar novos arquivos gigantes e tornar a modularizacao futura mais previsivel.

## Criterios de sucesso da arquitetura

Um dominio pode ser considerado alinhado com a arquitetura alvo quando:

- o router nao acessa banco diretamente
- a regra de negocio principal esta em service
- o acesso a dados esta encapsulado em repository
- os contratos principais estao definidos em schemas
- a cobertura de testes protege o fluxo migrado
- `database.py` deixa de crescer por causa daquele dominio

## Resumo executivo

A arquitetura desejada e incremental e pragmatica. Primeiro consolidamos a estrutura por camadas tecnicas `core/`, `db/`, `repositories/`, `schemas/`, `routers/` e `services/`. Depois, quando os dominios estiverem mais estaveis, os modulos maiores podem migrar para pacotes em `modules/<dominio>/`.
