# Mapa de Modulos

## Objetivo

Este documento descreve a ponte entre a estrutura atual por camadas tecnicas e a direcao futura de modularizacao por dominio.

## Estrutura de transicao

Nesta fase, o projeto esta convergindo para:

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

Essa estrutura e a base oficial para as proximas extracoes.

## Direcao futura

Depois da estabilizacao das camadas, alguns dominios poderao migrar para:

```text
modules/
  ocorrencias/
  preconselho/
  impressao/
  agendamento/
```

Cada modulo podera conter:

```text
router.py
service.py
repository.py
schemas.py
```

E, quando necessario:

```text
pdf_service.py
quota_service.py
queue_service.py
```

## Criterios para um dominio virar modulo

Um dominio so deve migrar para `modules/<dominio>/` quando:

- sua separacao logica por camadas ja estiver pronta
- o router estiver enxuto
- a regra de negocio estiver centralizada em service
- o acesso a dados estiver encapsulado em repository
- os contratos estiverem mapeados em schemas
- o dominio tiver testes minimamente confiaveis

## Candidatos naturais

Os dominios com maior potencial para modularizacao futura sao:

- `ocorrencias`
- `preconselho`
- `impressao`
- `agendamento`

## Regra pratica

Primeiro separar responsabilidade. Depois modularizar fisicamente.

## Resumo executivo

`modules/` e destino futuro, nao etapa obrigatoria agora. O trabalho imediato continua sendo consolidar `core/`, `repositories/`, `schemas/`, `routers/` e `services/` para reduzir acoplamento e esvaziar `database.py` com seguranca.
