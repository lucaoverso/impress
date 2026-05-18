# Roadmap de PRs da Refatoracao

## Objetivo

Este documento organiza os principais PRs da refatoracao incremental a partir da branch `refactor-transicao-camadas`.

O foco desta fase e consolidar a arquitetura de transicao por camadas tecnicas:

- `core/`
- `db/`
- `repositories/`
- `schemas/`
- `routers/`
- `services/`
- `templates/`
- `static/`

Depois disso, os dominios maiores poderao evoluir para `modules/<dominio>/`.

## Regras do roadmap

- cada PR deve ter um objetivo unico
- cada PR deve preservar comportamento
- cada PR deve reduzir acoplamento ou preparar a proxima extracao
- nao misturar refatoracao estrutural com mudanca funcional
- `database.py` nao deve crescer

## Branch de trabalho

Branch base recomendada:

- `refactor-transicao-camadas`

Convencao sugerida para sub-branches locais ou PRs derivados:

- `refactor/transicao-pcpi`
- `refactor/transicao-schemas`
- `refactor/transicao-repositories`
- `refactor/transicao-ocorrencias`

Se o ambiente Git continuar limitando nomes com `/`, usar:

- `refactor-pcpi`
- `refactor-schemas`
- `refactor-repositories`

## Fase 1. Fundacao da transicao

### PR 1. Documentacao e convencoes da refatoracao

Objetivo:

- formalizar a arquitetura de transicao
- definir o modelo futuro
- padronizar PRs de refatoracao

Escopo:

- `docs/arquitetura.md`
- `docs/plano_refatoracao.md`
- `docs/mapa-modulos.md`
- `docs/checklist_pr_refatoracao.md`
- `docs/roadmap_prs_refatoracao.md`
- `.github/pull_request_template.md`
- `CONTRIBUTING.md`

Status atual:

- pronto para abrir

Criterio de pronto:

- a equipe compartilha a mesma visao de transicao e destino final

### PR 2. Introducao das camadas `repositories/` e `schemas/`

Objetivo:

- criar o destino oficial das extracoes iniciais

Escopo:

- criar pacotes `repositories/` e `schemas/`
- introduzir o primeiro uso real em um dominio pequeno

Status atual:

- iniciado com `pcpi`

Criterio de pronto:

- existe pelo menos um dominio usando `repository` e `schemas` como camada intermediaria

## Fase 2. Dominio piloto

### PR 3. Consolidar `pcpi` como piloto da transicao

Objetivo:

- usar `pcpi` para validar o padrao sem alto risco

Escopo sugerido:

- manter `pcpi_router.py` operando
- expandir `repositories/pcpi_repository.py`
- expandir `schemas/pcpi_schemas.py`
- reduzir dependencia direta de `models.py` e `db/pcpi.py`

Passos recomendados:

1. mover imports do router para `schemas` e `repository`
2. extrair pequenas validacoes repetidas para `service` quando fizer sentido
3. manter todos os nomes publicos e rotas iguais

Criterio de pronto:

- `pcpi` usa a arquitetura de transicao sem regressao funcional

## Fase 3. Contratos e persistencia

### PR 4. Extrair contratos de dominio para `schemas/`

Objetivo:

- reduzir concentracao em `models.py`

Ordem sugerida:

1. `pcpi`
2. `preconselho`
3. `ocorrencias`
4. `admin`

Criterio de pronto:

- os contratos principais dos dominios priorizados deixam de nascer direto em `models.py`

### PR 5. Criar repositories de fachada para dominios prioritarios

Objetivo:

- isolar o acesso legado antes da extracao real de queries

Ordem sugerida:

1. `preconselho`
2. `ocorrencias`
3. `impressao`
4. `agendamento`

Criterio de pronto:

- routers e services novos deixam de importar `database.py` ou `db/*.py` diretamente quando houver repository equivalente

## Fase 4. Enxugar hotspots

### PR 6. Enxugar `preconselho_router.py`

Objetivo:

- mover regra de negocio para services e contratos para schemas

Criterio de pronto:

- o router fica mais focado em HTTP

### PR 7. Enxugar `ocorrencias_router.py`

Objetivo:

- atacar um dos maiores pontos de concentracao do backend

Estrategia:

- quebrar por fluxo pequeno
- priorizar consultas e operacoes mais isoladas
- manter `pdf_service` como especializacao separada

Criterio de pronto:

- o router reduz acoplamento sem mudanca de comportamento

### PR 8. Isolar trechos de `database.py` por dominio

Objetivo:

- trocar gradualmente implementacao legada por repository de verdade

Passos:

1. escolher um grupo pequeno de funcoes
2. copiar para repository
3. redirecionar consumidores
4. validar
5. somente depois aposentar o trecho legado

Criterio de pronto:

- `database.py` perde responsabilidade real em ao menos um dominio

## Fase 5. Core e padroes transversais

### PR 9. Introduzir `core/`

Objetivo:

- criar um destino claro para itens transversais

Conteudo esperado ao longo do tempo:

- configuracao
- seguranca
- dependencias
- permissoes

Observacao:

- essa fase nao exige mover tudo de uma vez
- a criacao de `core/` pode comecar por wrappers e funcoes compartilhadas

Criterio de pronto:

- novas responsabilidades transversais deixam de nascer espalhadas

## Fase 6. Preparacao do modelo final

### PR 10. Definir criterios de modularizacao por dominio

Objetivo:

- decidir quando um dominio pode migrar para `modules/<dominio>/`

Dominios candidatos:

- `ocorrencias`
- `preconselho`
- `impressao`
- `agendamento`

Criterio de pronto:

- existe consenso sobre quando modularizar fisicamente

### PR 11. Primeiro modulo estabilizado em `modules/`

Objetivo:

- validar o modelo final em um dominio maduro

Pre-condicoes:

- router, service, repository e schemas ja estao separados
- testes do dominio estao confiaveis
- a mudanca fisica nao gera diff explosivo

Criterio de pronto:

- um dominio migra para `modules/<dominio>/` com baixo risco

## Sequencia curta recomendada para agora

Se quisermos manter foco e tracao, eu recomendo esta ordem imediata:

1. fechar o PR de documentacao e padroes
2. fechar o PR piloto de `pcpi`
3. criar `repository` de fachada para `preconselho`
4. criar `schemas` iniciais de `preconselho`
5. extrair o primeiro fluxo pequeno de `preconselho_router.py`
6. repetir o mesmo movimento em `ocorrencias`

## Resumo executivo

O melhor caminho e usar a branch `refactor-transicao-camadas` como guarda-chuva da refatoracao incremental, mas manter os PRs pequenos, independentes e revisaveis. Primeiro consolidamos a arquitetura por camadas tecnicas. Depois, so quando os dominios estiverem maduros, validamos a ida para `modules/<dominio>/`.
