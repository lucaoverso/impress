# Plano Inicial de Refatoracao

## Objetivo

Este plano organiza a migracao para a arquitetura modular desejada sem alterar comportamento de producao, sem mover arquivos em massa e sem renomear funcoes existentes. A refatoracao deve acontecer em etapas pequenas, com validacao constante e commits curtos.

## Restricoes desta jornada

- nao alterar comportamento funcional como efeito colateral da refatoracao
- nao mover arquivos existentes nesta fase
- nao renomear funcoes publicas ja utilizadas
- nao ampliar `database.py`
- preservar compatibilidade durante toda a transicao

## Estrategia geral

O plano segue a mesma logica para cada dominio:

1. mapear o fluxo atual
2. criar a camada destino
3. redirecionar um trecho pequeno para a nova camada
4. validar com testes
5. somente depois reduzir o legado correspondente

## Estrutura adotada nesta fase

Nesta etapa, a arquitetura sera organizada por camadas tecnicas:

- `core/`
- `db/`
- `repositories/`
- `schemas/`
- `routers/`
- `services/`
- `templates/`
- `static/`

## Ordem de prioridade

Prioridade alta:

- `database.py`
- `ocorrencias_router.py`
- `preconselho_router.py`
- `services/ocorrencia_pdf_service.py`

Prioridade media:

- `models.py`
- `routers/admin_router.py`
- servicos de importacao e relatorios mais extensos

Prioridade baixa:

- consolidacoes cosmeticas
- padronizacao fina de nomes internos
- reorganizacao complementar de frontend

## Fase 0. Preparacao e guardrails

Objetivo:

- congelar o crescimento do legado
- deixar o time alinhado sobre o padrao alvo

Entregas:

- documentacao de arquitetura
- documentacao do plano de migracao
- checklist de PR para refatoracoes pequenas

Regras praticas:

- toda mudanca nova deve preferir `router -> service -> repository -> schemas`
- qualquer acesso novo ao banco deve nascer fora de `database.py` sempre que possivel
- se um fluxo ainda depender do legado, encapsular a dependencia em camada intermediaria

## Fase 1. Preparar a arquitetura de transicao

Objetivo:

- criar os lugares certos para o codigo novo, sem quebrar nada

Passos:

1. criar pastas ou modulos destino para `core/`, `repositories/` e `schemas/`
2. definir convencoes minimas para nomes por dominio
3. estabelecer o padrao de importacao entre camadas
4. manter os arquivos legados operando em paralelo

## Fase 2. Conter `database.py`

Objetivo:

- transformar `database.py` em legado estavel em vez de ponto de expansao

Passos:

1. identificar grupos de funcoes por dominio
2. documentar quais grupos ainda sao consumidos por cada router ou service
3. criar `repository.py` por dominio como fachada
4. redirecionar chamadas novas para os repositories

Regra importante:

- nesta fase, `repository.py` pode continuar delegando para `database.py`
- isso ja vale como ganho arquitetural porque reduz acoplamento dos consumidores

## Fase 3. Extrair contratos para `schemas.py`

Objetivo:

- reduzir concentracao de contratos em arquivos genericos e preparar validacoes mais locais

Comecar por:

- `pcpi`
- `preconselho`
- `ocorrencias`
- `admin`

## Fase 4. Enxugar routers grandes

Objetivo:

- deixar routers com foco real em HTTP

Sequencia sugerida:

1. `ocorrencias_router.py`
2. `preconselho_router.py`
3. `pcpi_router.py`
4. `routers/admin_router.py`

## Fase 5. Modularizar services grandes

Objetivo:

- dividir services extensos sem dispersar a regra de negocio

Validacao inicial:

- `pcpi` passou a ser a referencia do projeto para esse passo
- o dominio foi dividido em services especializados sem mudar comportamento
- os arquivos resultantes ficaram abaixo da regra de `300` linhas

## Fase 6. Trocar implementacao interna dos repositories

Objetivo:

- reduzir de fato o conteudo de `database.py`

## Fase 7. Revisar `models.py` e contratos remanescentes

Objetivo:

- reduzir concentracao de modelos genericos

## Fase 8. Consolidacao gradual

Objetivo:

- remover restos de acoplamento apos as migracoes principais

Primeiro dominio consolidado:

- `pcpi`
- fronteiras validadas entre `router`, `service`, `repository` e `schemas`
- pronto para servir de modelo a `preconselho` e `ocorrencias`

## Fase 9. Modularizacao por dominio

Objetivo:

- mover apenas os dominios ja estabilizados para `modules/<dominio>/`

## Checklist de cada pequeno commit

Antes de concluir cada commit de refatoracao:

- o comportamento funcional continua igual
- a mudanca atinge um fluxo pequeno e claro
- nao houve renomeacao desnecessaria
- nao houve movimentacao estrutural ampla
- existe teste cobrindo o trecho alterado ou o teste existente continua verde
- o router ficou menor ou mais simples
- `database.py` nao cresceu

## Sequencia pratica recomendada para os proximos commits

1. criar `docs/arquitetura.md` e `docs/plano_refatoracao.md`
2. introduzir `repositories/` e `schemas/` como destino oficial
3. consolidar `pcpi` como piloto do padrao
4. repetir o mesmo fluxo em `preconselho`
5. atacar um primeiro corte pequeno em `ocorrencias`
6. revisar contratos remanescentes e reduzir compatibilidades legadas

## Dominios piloto sugeridos

Boas candidaturas para primeiros passos:

- `preconselho`, reaproveitando o padrao validado em `pcpi`
- um trecho especifico de `admin`
- uma leitura simples de catalogo ou consulta auxiliar

## Resumo executivo

O caminho recomendado e incremental. Primeiro consolidamos a arquitetura por camadas tecnicas, depois paramos de crescer o legado, em seguida extraimos repositories, schemas e services por dominio, e so depois avaliamos a modularizacao fisica em `modules/<dominio>/`.
