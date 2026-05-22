# Roadmap de PRs da Refatoracao

## Objetivo

Este documento organiza os principais PRs da refatoracao incremental a partir de uma branch limpa baseada em `main`.

O foco desta fase e consolidar a arquitetura de transicao por camadas tecnicas:

- `core/`
- `db/`
- `repositories/`
- `schemas/`
- `routers/`
- `services/`
- `templates/`
- `static/`

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

### PR 2. Introducao das camadas `repositories/` e `schemas/`

Objetivo:

- criar o destino oficial das extracoes iniciais

### PR 3. Consolidar `pcpi` como piloto da transicao

Objetivo:

- usar `pcpi` para validar o padrao sem alto risco

Status:

- concluido como dominio piloto da transicao
- `router` enxuto e focado em HTTP
- `repository` criado como fronteira de persistencia
- `schemas` definidos fora de `models.py`
- `service` dividido por responsabilidade e abaixo da regra de `300` linhas por arquivo

## Sequencia curta recomendada para agora

1. fechar o PR de documentacao e padroes
2. usar `pcpi` como referencia para os proximos dominios
3. criar `repository` de fachada para `preconselho`
4. criar `schemas` iniciais de `preconselho`
5. extrair o primeiro fluxo pequeno de `routers/preconselho_router.py`
6. repetir o mesmo movimento em `ocorrencias`

## Resumo executivo

O melhor caminho e usar uma branch limpa baseada em `main` para manter os PRs pequenos, independentes e revisaveis. Primeiro consolidamos a arquitetura por camadas tecnicas. Depois, so quando os dominios estiverem maduros, validamos a ida para `modules/<dominio>/`.
