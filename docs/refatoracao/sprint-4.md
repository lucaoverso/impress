# Sprint 4

## Objetivo

Comecar a modularizacao do acesso a dados, reduzindo o acoplamento direto dos routers e services ao `database.py`.

## Escopo

- [x] Criar pacote `db/` com modulos por dominio
- [x] Introduzir superfícies de dominio para bootstrap, usuarios, catalogos, impressao, agendamento, docencia, ocorrencias, pre-conselho e PCPI
- [x] Redirecionar todos os consumers para importar via `db/`
- [x] Validar lint e testes apos a reorganizacao

## Estrutura inicial

- `db/bootstrap.py`
- `db/usuarios.py`
- `db/catalogos.py`
- `db/impressao.py`
- `db/agendamento.py`
- `db/docencia.py`
- `db/ocorrencias.py`
- `db/preconselho.py`
- `db/pcpi.py`

## Observacoes

- Nesta etapa, `database.py` continua como implementacao de compatibilidade.
- Os novos modulos em `db/` passam a concentrar a fronteira publica por dominio e preparam a extracao fisica das implementacoes nos proximos ciclos.
- Os wrappers em `db/` resolvem o `database` dinamicamente para continuar compativeis com os testes que recarregam o modulo em memoria.
- Os imports diretos de `database.py` foram eliminados dos routers e services da aplicacao ao final deste sprint.
