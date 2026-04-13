# Sprint 2

## Objetivo

Criar um núcleo compartilhado no frontend para reduzir duplicação entre os scripts por página.

## Escopo

- [x] Criar `static/js/core/`
- [x] Centralizar helpers de DOM
- [x] Centralizar helpers de autenticação e sessão
- [x] Centralizar wrappers de API
- [x] Centralizar formatadores simples
- [x] Adaptar templates para carregar o núcleo compartilhado
- [x] Atualizar os scripts das páginas para consumir o núcleo
- [x] Validar lint e testes após a extração

## Observações

- `servicos.js` manteve uma regra local de visibilidade para coordenadores para preservar o comportamento atual da tela inicial.
