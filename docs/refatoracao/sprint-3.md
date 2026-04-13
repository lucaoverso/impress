# Sprint 3

## Objetivo

Dividir os arquivos gigantes do frontend por contexto funcional, mantendo o comportamento atual das telas.

## Escopo

- [x] Extrair `admin.js` em módulos menores
- [x] Extrair `coordenacao.js` em módulos menores
- [x] Manter `admin.js` e `coordenacao.js` como entrypoints mínimos
- [x] Atualizar templates para carregar os módulos na ordem correta
- [x] Validar sintaxe, lint e testes após a divisão

## Estrutura

### Admin

- `static/js/admin/core.js`
- `static/js/admin/atribuicoes.js`
- `static/js/admin/estrutura.js`
- `static/js/admin/operacao.js`
- `static/js/admin/init.js`

### Coordenacao

- `static/js/coordenacao/core.js`
- `static/js/coordenacao/ocorrencias.js`
- `static/js/coordenacao/painel.js`
- `static/js/coordenacao/base-legal.js`
- `static/js/coordenacao/cadastros.js`
- `static/js/coordenacao/init.js`

## Observações

- Os entrypoints legados `static/js/admin.js` e `static/js/coordenacao.js` foram reduzidos para apenas iniciar a página depois que os módulos são carregados.
