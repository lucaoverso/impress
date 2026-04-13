# Sprint 6

## Objetivo

Organizar a camada visual sem alterar a stack atual, reduzindo o acoplamento do CSS e removendo repeticao no carregamento dos templates.

## Escopo

- [x] Dividir o antigo `static/css/style.css` em arquivos menores por dominio visual
- [x] Manter `style.css` como entrypoint unico do bundle para preservar compatibilidade
- [x] Centralizar o carregamento do CSS em um include compartilhado de template
- [x] Validar o carregamento das paginas principais sem alterar a estrutura funcional

## Estrutura

- `static/css/base.css`
- `static/css/pages/auth.css`
- `static/css/pages/professor.css`
- `static/css/pages/services-scheduler.css`
- `static/css/pages/pcpi-preconselho.css`
- `static/css/pages/admin.css`
- `static/css/pages/coordenacao.css`
- `templates/includes/style_bundle.html`

## Observacoes

- O bundle continua entrando por `static/css/style.css`, agora apenas como ponto de agregacao.
- As regras foram agrupadas por contexto visual para facilitar manutencao incremental.
- Os templates principais deixaram de repetir a tag de stylesheet e passaram a reutilizar o include compartilhado.
