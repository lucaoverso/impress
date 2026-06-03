# Modulos do Sistema e Aderencia a Arquitetura

## Objetivo

Este documento registra um apanhado geral dos dominios atuais do sistema em relacao a arquitetura alvo descrita em `AGENTS.md` e `ARCHITECTURE.md`.

Base da leitura:

- `main.py` para identificar modulos ativos
- `modules/`, `routers/`, `services/` e `db/` para localizar as camadas reais
- tamanho e distribuicao dos arquivos como sinal de acoplamento e maturidade

Legenda resumida:

- `Aderente`: ja segue bem o fluxo `router -> service -> repository -> database`
- `Parcial`: existe separacao relevante, mas ainda faltam camadas ou ha concentracao excessiva
- `Misturado`: o dominio ainda esta espalhado fora do padrao modular

## Tabela Geral

| Modulo | Aderencia | Estado | Risco | Prioridade | Evidencias principais |
| --- | --- | --- | --- | --- | --- |
| Auth/Login | Baixa | Misturado | Alto | Nao mexer agora | `auth.py` + `services/auth_service.py` + `db/usuarios.py`, sem pacote `modules/auth` |
| Impressao | Alta | Funciona e esta bem encaminhado | Muito alto | So com testes | `modules/printing/` tem `router.py`, `service.py`, `repository.py`, `schemas.py` e `models.py` |
| Agendamento | Alta | Bom candidato | Medio | Depois de recursos | `modules/scheduling/` ja segue o padrao, com router legado residual em `routers/agendamento_router.py` |
| Recursos | Baixa | Nao existe como modulo isolado | Baixo | Comecar aqui | regras e dados ainda aparecem diluidos entre `db/catalogos.py`, `db/bootstrap.py` e telas de agendamento |
| Relatorios | Media | Parcial | Baixo | Depois | `routers/relatorios_router.py` e `db/relatorios.py` sao pequenos, mas ainda nao ha `modules/reports` |
| Admin | Baixa | Misturado | Medio | Depois | `routers/admin_router.py` tem mais de 1000 linhas e cruza varios dominios |
| Usuarios/Professores | Media | Parcial | Medio | Depois de relatorios | `routers/professores_router.py`, `services/auth_service.py`, `db/usuarios.py` e `db/docencia.py` ainda estao separados por camada, nao por dominio |
| Preconselho | Media | Parcial | Medio | Depois de users | existe `modules/preconselho/`, mas o router ativo ainda esta em `preconselho_router.py` e ha arquivos grandes em `service.py` e `reports.py` |
| PCPI | Baixa | Misturado | Medio-alto | Depois | `pcpi_router.py` e `services/pcpi_service.py` ainda concentram muita regra fora de `modules/` |
| APC | Baixa | Misturado | Medio-alto | Depois | `routers/apc_router.py` e `services/apc_service.py` continuam grandes e sem modulo dedicado |
| Ocorrencias/Coordenacao | Baixa | Baguncado | Alto | Depois | `ocorrencias_router.py` e `services/ocorrencia_pdf_service.py` ainda sao monolitos grandes |
| Horario Escolar | Media | Parcial | Medio | Depois | ha `routers/horario_escolar_router.py`, `services/horario_escolar_service.py` e `db/horario_escolar.py`, mas sem `modules/horario_escolar` |
| Download de Videos | Media | Parcial | Medio | Depois | dominio separado em `routers/download_router.py` e services proprios, mas ainda fora da estrutura modular alvo |

## Leitura Rapida

Os dominios hoje mais proximos da arquitetura alvo sao:

- `printing`
- `scheduling`
- `preconselho` em estado intermediario

Os dominios mais desalinhados hoje sao:

- `auth`
- `admin`
- `apc`
- `pcpi`
- `ocorrencias/coordenacao`

O ponto mais importante para a estrategia de refatoracao continua valido:

- `resources` ainda e o melhor modulo para consolidar primeiro, porque o risco funcional e menor e ele ainda nao existe como pacote de dominio claro
- `scheduling` vem logo depois, porque ja possui boa base em `modules/scheduling/`
- `auth` e `printing` devem continuar no fim da fila por criticidade operacional

## Observacoes

- `admin` nao deve concentrar regra de negocio propria quando a regra pertence a impressao, usuarios, recursos ou outros dominios.
- `resources` hoje aparece mais como capacidade embutida em agendamento e bootstrap do que como modulo de dominio isolado.
- `main.py` ainda mistura rotas em tres formatos: `modules/*`, `routers/*` e routers na raiz do projeto. Isso e um bom indicador de transicao parcial.
- A existencia de `db/*.py` por dominio ja ajuda bastante, mas ainda nao substitui a necessidade de pacotes modulares completos em `modules/`.

## Ordem Recomendada de Trabalho

Se a equipe quiser transformar esta leitura em backlog de refatoracao, a ordem mais segura continua sendo:

1. `resources`
2. `scheduling`
3. `reports`
4. `users`
5. `auth`
6. `printing`

Depois disso, vale abrir uma trilha paralela especifica para dominios educacionais mais pesados:

1. `preconselho`
2. `pcpi`
3. `apc`
4. `ocorrencias/coordenacao`
5. `horario escolar`
