# Resumo

Descreva em poucas linhas o objetivo deste PR.

## Tipo de mudanca

- [ ] refatoracao estrutural
- [ ] ajuste de regra de negocio
- [ ] correcao de bug
- [ ] testes
- [ ] documentacao
- [ ] infraestrutura ou deploy

## Dominio afetado

Marque o principal contexto impactado:

- [ ] autenticacao
- [ ] impressao
- [ ] agendamento
- [ ] admin
- [ ] coordenacao
- [ ] ocorrencias
- [ ] preconselho
- [ ] pcpi
- [ ] horario escolar
- [ ] worker
- [ ] frontend web
- [ ] outro

## O que mudou

- 

## O que nao mudou

Registre explicitamente o que este PR nao pretende alterar.

- comportamento funcional
- contratos externos
- schema do banco

Se algum item acima nao se aplicar, explique:

- 

## Arquitetura

Explique como a mudanca se encaixa na arquitetura alvo.

- `router.py`: 
- `service.py`: 
- `repository.py`: 
- `schemas.py`: 
- legado envolvido (`database.py`, router antigo, models centralizados, etc.):

## Relacao com o legado

- [ ] nao toca legado
- [ ] encapsula acesso legado sem alterar comportamento
- [ ] reduz dependencia direta de `database.py`
- [ ] prepara extracao futura
- [ ] remove trecho legado ja sem consumidores

Detalhe aqui o ponto principal:

- 

## Estrategia de seguranca

- [ ] mudanca pequena e focal
- [ ] sem renomeacao desnecessaria de funcao publica
- [ ] sem mover arquivos em massa
- [ ] sem mistura de refatoracao estrutural com nova funcionalidade
- [ ] comportamento preservado por testes existentes ou novos

## Testes e validacao

Marque o que foi executado:

- [ ] `make test`
- [ ] `make lint`
- [ ] `make check`
- [ ] `make migrate`
- [ ] `make migrations-status`
- [ ] testes manuais
- [ ] nao aplicavel

Descreva os testes relevantes:

- 

## Riscos e atencoes

- risco principal:
- area sensivel:
- rollback simples:

## Checklist de refatoracao

- [ ] o PR tem um objetivo unico e claro
- [ ] o diff esta pequeno o suficiente para revisao segura
- [ ] o router nao ganhou regra de negocio nova
- [ ] o service nao ganhou acesso HTTP desnecessario
- [ ] o repository nao ganhou regra de negocio de alto nivel
- [ ] `database.py` nao cresceu sem justificativa forte
- [ ] a documentacao foi atualizada quando necessario

## Observacoes para revisao

Pontos em que vale revisar com mais cuidado:

- 
