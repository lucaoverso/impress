# Checklist de PR de Refatoracao

## Objetivo

Este checklist padroniza PRs de refatoracao para manter a migracao segura, incremental e facil de revisar.

## Quando usar

Use este padrao sempre que o PR tiver como foco principal:

- extracao de camada
- reducao de acoplamento
- isolamento de legado
- reorganizacao interna sem mudanca de comportamento
- preparacao de terreno para migracoes futuras

## O que um bom PR de refatoracao deve fazer

- ter um objetivo unico e claro
- atacar uma area pequena do sistema
- preservar comportamento
- reduzir acoplamento ou concentracao de responsabilidade
- deixar um caminho mais claro para o proximo passo

## O que um PR de refatoracao deve evitar

- misturar refatoracao estrutural com funcionalidade nova
- alterar varios dominios sem necessidade
- mover arquivos em massa
- renomear funcoes publicas sem ganho claro
- crescer `database.py`
- introduzir duplicacao permanente entre camadas

## Estrutura recomendada da descricao do PR

Todo PR de refatoracao deve responder:

1. qual problema estrutural ele ataca
2. qual trecho foi migrado ou encapsulado
3. o que permaneceu igual
4. como a mudanca se conecta ao plano de refatoracao
5. quais testes protegem o comportamento

## Checklist obrigatorio

- [ ] o PR tem um unico objetivo estrutural
- [ ] a descricao explica o problema de manutencao que esta sendo tratado
- [ ] a descricao informa claramente o que nao mudou
- [ ] o escopo cabe em revisao humana sem leitura exaustiva
- [ ] a mudanca preserva comportamento
- [ ] nao houve mistura indevida com nova regra de negocio
- [ ] o router ficou igual ou mais simples
- [ ] a regra de negocio foi movida para `service.py` quando aplicavel
- [ ] o acesso a dados foi encapsulado em `repository.py` quando aplicavel
- [ ] os contratos foram movidos ou preparados para `schemas.py` quando aplicavel
- [ ] `database.py` foi isolado ou reduzido, nunca expandido sem motivo forte
- [ ] os testes relevantes foram executados

## Checklist opcional por tipo de mudanca

### Se o PR tocar router

- [ ] o router nao concentra regra de negocio nova
- [ ] o router apenas traduz HTTP, permissao e resposta
- [ ] a integracao com service ficou explicita

### Se o PR tocar service

- [ ] o service concentra a regra de negocio do fluxo alterado
- [ ] o service nao depende de detalhes HTTP sem necessidade
- [ ] a responsabilidade do service ficou mais coesa

### Se o PR tocar repository

- [ ] o repository encapsula persistencia do dominio
- [ ] nao houve mistura com regra de negocio de alto nivel
- [ ] a dependencia de `database.py` ficou menor ou mais isolada

### Se o PR tocar schemas

- [ ] os contratos ficaram mais explicitos
- [ ] a validacao estrutural saiu de lugares dispersos
- [ ] nao houve quebra desnecessaria de compatibilidade

## Tamanho recomendado

Preferencia para PRs que tenham:

- um fluxo ou caso de uso por vez
- um dominio por vez
- uma extracao principal por vez

## Relacao com os documentos do projeto

Ao abrir PRs de refatoracao, use junto:

- [docs/arquitetura.md](/C:/Users/lucas/impress/docs/arquitetura.md)
- [docs/plano_refatoracao.md](/C:/Users/lucas/impress/docs/plano_refatoracao.md)
- [docs/guia-commits-e-alteracoes.md](/C:/Users/lucas/impress/docs/guia-commits-e-alteracoes.md)
