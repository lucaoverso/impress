# Frontend v2

Base inicial para a reestruturacao do frontend da Suite Escolar.

Esta pasta ainda nao substitui o frontend atual. A ideia e construir uma fundacao reutilizavel, alinhada ao `docs/DESIGN.md`, para migrar telas e componentes gradualmente.

## Estrutura

```text
src/
  components/
    ui/
      button.css
      input.css
      badge.css
      icon.css
    layout/
      app-shell.css
      side-nav.css
      side-nav.html
      side-nav.config.js
      side-nav.examples.html
      top-nav.css
      top-nav.html
      top-nav.config.js
      top-nav.examples.html
      stepper.css
    features/
      README.md
  styles/
    index.css        # entrada unica de estilos globais
    variables.css    # tokens do Design System
    foundations.css  # reset, base HTML, foco, tipografia e formularios
    utilities.css    # utilitarios pequenos e acessiveis
templates/
  coordenacao/
    index.html
    style.css
    script.js
```

## Principios

- `styles/variables.css` e a fonte de verdade visual para o v2.
- Componentes devem usar `var(--token-name)` em vez de valores soltos.
- A interface e de produto: familiar, calma, legivel e previsivel.
- A cor primaria deve ficar para acao principal, selecao e estado ativo.
- Movimento deve comunicar estado e respeitar `prefers-reduced-motion`.
- Novos componentes devem prever estados: default, hover, focus, active, disabled, loading e erro.
- A `side-navbar` recebe links do modulo atual; a unica acao global fixa nela e logout.
- O arquivo `components/layout/side-nav.config.js` centraliza os contextos de modulo para evitar duplicar navegacao por tela.
- A `top-navbar` prepara pesquisa, notificacoes, calendario e perfil para serem conectados ao backend depois.
- O frontend legado continua em `static/`; o v2 deve evoluir dentro de `frontend-v2` ate termos uma estrategia de build/serving definida.

## Uso inicial

Importe `src/styles/index.css` no ponto de entrada do futuro frontend v2.

```css
@import "./styles/index.css";
```
