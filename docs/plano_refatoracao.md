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

Essa e a estrutura oficial de transicao. A migracao para `modules/<dominio>/` fica como direcao futura, nao como obrigacao imediata.

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

Resultado esperado:

- a equipe passa a ter um destino claro para novas extracoes
- o codigo novo deixa de depender diretamente da organizacao antiga

## Fase 1.1. Preparar a direcao modular futura

Objetivo:

- registrar a estrutura alvo de `modules/<dominio>/` sem forcar mudanca fisica imediata

Passos:

1. definir quais dominios tendem a virar modulo
2. alinhar o time sobre os criterios de estabilizacao
3. evitar reorganizacao fisica antes da separacao logica das camadas

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

Criterio de pronto:

- nenhum codigo novo acessa `database.py` diretamente fora da camada de transicao

## Fase 3. Extrair contratos para `schemas.py`

Objetivo:

- reduzir concentracao de contratos em arquivos genericos e preparar validacoes mais locais

Passos:

1. mapear payloads mais usados por dominio
2. criar `schemas/<dominio>_schemas.py`
3. migrar primeiro DTOs mais estaveis e de baixo risco
4. manter compatibilidade com estruturas antigas enquanto houver consumidores mistos

Comecar por:

- ocorrencias
- preconselho
- pcpi
- admin

Criterio de pronto:

- cada dominio priorizado passa a ter seus contratos principais documentados e reutilizaveis

## Fase 4. Enxugar routers grandes

Objetivo:

- deixar routers com foco real em HTTP

Passos:

1. escolher um fluxo pequeno dentro de um router grande
2. extrair a regra de negocio para `service.py`
3. substituir o trecho do router por chamada ao service
4. validar comportamento
5. repetir ate o arquivo perder peso e acoplamento

Sequencia sugerida:

1. `ocorrencias_router.py`
2. `preconselho_router.py`
3. `pcpi_router.py`
4. `routers/admin_router.py`

Observacao:

- nao e necessario mover o router de lugar nesta etapa
- primeiro a responsabilidade muda, depois a localizacao pode ser revista em outra fase

## Fase 5. Modularizar services grandes

Objetivo:

- dividir services extensos sem dispersar a regra de negocio

Passos:

1. separar casos gerais de casos especializados
2. manter `service.py` como coordenador do dominio
3. extrair responsabilidades tecnicas para arquivos especificos quando houver motivo claro

Exemplos:

- `services/ocorrencia_pdf_service.py` continua como especializacao de PDF
- importacoes podem viver em `import_service.py`
- integracoes externas podem viver em services dedicados

Criterio de pronto:

- o service principal fica menor e com responsabilidade mais clara

## Fase 6. Trocar implementacao interna dos repositories

Objetivo:

- reduzir de fato o conteudo de `database.py`

Passos:

1. selecionar um grupo pequeno de funcoes de um dominio
2. copiar a logica para `repository.py` mantendo a mesma semantica
3. apontar o service para o repository novo
4. validar com testes
5. somente depois remover ou aposentar o trecho legado equivalente

Regra de seguranca:

- nunca apagar um bloco legado antes de saber quem ainda o consome

## Fase 7. Revisar `models.py` e contratos remanescentes

Objetivo:

- reduzir concentracao de modelos genericos

Passos:

1. manter compatibilidade com consumidores atuais
2. migrar contratos de dominio para `schemas.py`
3. deixar em `models.py` apenas o que ainda for transversal ou legado temporario

Resultado esperado:

- `models.py` deixa de ser deposito central de contratos desconexos

## Fase 8. Consolidacao gradual

Objetivo:

- remover restos de acoplamento apos as migracoes principais

Passos:

1. localizar imports diretos residuais de `database.py`
2. localizar regras de negocio ainda presas em routers
3. localizar contratos ainda espalhados em `dict` e tuplas anonimas
4. fechar lacunas de teste

## Fase 9. Modularizacao por dominio

Objetivo:

- mover apenas os dominios ja estabilizados para `modules/<dominio>/`

Pre-condicoes:

- router, service, repository e schemas do dominio ja existem
- o dominio depende pouco de imports diretos do legado
- os testes do dominio estao consistentes

Passos:

1. escolher um dominio estabilizado
2. agrupar seus arquivos em um pacote `modules/<dominio>/`
3. ajustar imports com o menor diff possivel
4. validar comportamento
5. repetir apenas para dominios maduros

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
3. escolher um primeiro dominio piloto pequeno
4. extrair um repository de fachada para esse dominio
5. extrair um service simples ou um trecho de router
6. repetir o padrao antes de atacar os modulos mais pesados

## Dominios piloto sugeridos

Boas candidaturas para primeiros passos:

- `pcpi`, por ser menor que `ocorrencias` e `preconselho`
- um trecho especifico de `admin`
- uma leitura simples de catalogo ou consulta auxiliar

Dominios para depois:

- `ocorrencias`, por volume e criticidade
- `preconselho`, por concentracao de fluxo
- partes sensiveis de impressao e worker

## Como tratar `database.py` durante a migracao

`database.py` deve seguir estas regras:

- nenhum recurso novo importante entra direto nele
- ele pode continuar sendo chamado por compatibilidade
- toda extracao deve diminuir ou isolar seu papel
- apagar codigo dele sera a ultima etapa de cada microciclo

Em outras palavras:

- primeiro encapsular
- depois redirecionar
- depois validar
- so entao reduzir o legado

## Riscos e mitigacoes

Risco: quebrar fluxo antigo ao extrair tudo de uma vez.
Mitigacao: migrar um unico caso de uso por commit.

Risco: duplicar regra entre router e service.
Mitigacao: definir dono claro da regra antes de extrair.

Risco: repository virar apenas outro nome para `database.py` sem evolucao.
Mitigacao: usar repository primeiro como fachada e depois como destino da logica extraida.

Risco: refatoracao sem rede de seguranca.
Mitigacao: sempre rodar testes do dominio afetado antes de reduzir legado.

## Resumo executivo

O caminho recomendado e incremental. Primeiro consolidamos a arquitetura por camadas tecnicas, depois paramos de crescer o legado, em seguida extraimos repositories, schemas e services por dominio, e so depois avaliamos a modularizacao fisica em `modules/<dominio>/`. `database.py` deve ser esvaziado com seguranca, sempre em pequenos commits e com comportamento preservado.
