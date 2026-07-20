# Classes do Design System

## Objetivo

Este documento é a referência operacional das classes compartilhadas da interface da Suíte Escolar. Use-o ao criar ou migrar páginas para evitar novos padrões locais.

O arquivo descreve o contrato público de `static/css/design-system.css`. Classes específicas de módulos continuam permitidas para comportamentos particulares, mas não devem recriar estrutura, botões, campos, feedbacks, listas, métricas ou tabelas já cobertos aqui.

Estado da documentação: versão inicial estável, atualizada em 20 de julho de 2026.

## Fontes de verdade

- `DESIGN.md`: princípios visuais, cores, tipografia, elevação e decisões de produto.
- `static/css/base.css`: tokens e estilos básicos dos elementos HTML.
- `static/css/design-system.css`: classes canônicas documentadas neste guia.
- `static/css/components/continuous-surfaces.css`: remove a aparência de card de superfícies estruturais.
- `static/css/components/app-navbar.css`: barra superior compartilhada.
- `static/css/components/app-sidebar.css`: navegação lateral compartilhada.
- `templates/includes/style_bundle.html`: ordem oficial de carregamento das folhas.

A ordem do bundle é:

1. ícones;
2. base;
3. componentes antigos ainda compartilhados;
4. CSS específico da página;
5. design system;
6. superfícies contínuas;
7. barra lateral.

O design system é carregado depois do CSS da página para estabelecer o padrão. Exceções específicas devem ser justificadas e usar seletor mais específico, não `!important`.

## Estrutura mínima de uma página

```html
<main class="page-shell">
    <header class="page-header">
        <div class="page-header-main">
            <h1 class="page-title">Título da página</h1>
            <p class="page-lead">Explique a tarefa principal em uma frase.</p>
        </div>
        <div class="page-actions">
            <button class="button button--primary" type="button">Ação principal</button>
        </div>
    </header>

    <section class="page-section">
        <header class="section-header">
            <div class="section-header-main">
                <h2 class="section-title">Título da seção</h2>
                <p class="section-copy">Descrição curta da seção.</p>
            </div>
        </header>
    </section>
</main>
```

Não envolva cada seção em um card. O corpo e o conteúdo principal usam a mesma superfície; espaçamento, títulos e divisores fazem a separação.

## Layout de página

| Classe | Uso |
| --- | --- |
| `.page-shell` | Contêiner principal centralizado, com largura e espaçamento responsivos. |
| `.page-shell--wide` | Página ampla, adequada a dashboards e tabelas extensas. |
| `.page-shell--medium` | Largura intermediária de 1180 px, usada em agendamento. |
| `.page-shell--compact` | Fluxos e formulários que exigem menor largura de leitura. |
| `.page-grid` | Grade genérica com alinhamento pelo topo. |
| `.page-grid--two` | Duas colunas de mesma largura; vira uma coluna no celular. |
| `.page-section` | Seção interna transparente e sem aparência de card. |

Use apenas um modificador de largura por página. O atributo `hidden` continua funcionando em `.page-section`.

## Cabeçalhos e títulos

| Classe | Uso |
| --- | --- |
| `.page-header` | Organiza título e ações principais da página. |
| `.page-header--flush` | Remove a margem inferior quando o contêiner pai já possui `gap`. |
| `.page-header-main` | Agrupa título, descrição e contexto textual, limitado a 70 caracteres. |
| `.page-title` | Título principal único da página. |
| `.page-lead` | Explicação da tarefa ou objetivo da página. |
| `.section-header` | Organiza título, descrição e possíveis ações de uma seção. |
| `.section-header-main` | Agrupa o conteúdo textual do cabeçalho de seção. |
| `.section-title` | Título de segundo nível visual. |
| `.section-copy` | Texto explicativo ou auxiliar da seção. |

Uma página deve ter apenas um `.page-title`. Evite criar subtítulos estilizados localmente quando `.section-title` atende ao caso.

## Ações e botões

| Classe | Uso |
| --- | --- |
| `.page-actions` | Ações relacionadas à página inteira. |
| `.action-group` | Agrupa ações locais e permite quebra de linha. |
| `.action-group--compact` | Reduz controles para 36 px em ações secundárias densas. |
| `.button` | Base obrigatória para botão ou link com aparência de botão. |
| `.button--primary` | Ação principal do contexto. |
| `.button--danger` | Ação destrutiva secundária, com contorno de perigo. |
| `.button--danger-solid` | Confirmação destrutiva final. |
| `.is-active` | Estado selecionado de botões e abas; não deve ser aplicado sem estado real. |

Exemplo:

```html
<div class="action-group">
    <button class="button" type="button">Cancelar</button>
    <button class="button button--primary" type="submit">Salvar</button>
</div>
```

Regras:

- mantenha uma ação primária dominante por contexto;
- use `.button` também nos elementos criados por JavaScript;
- preserve `disabled` e `hidden` como atributos nativos;
- não use a variante de perigo para ações reversíveis comuns.

## Abas

| Classe | Uso |
| --- | --- |
| `.tab-list` | Contêiner horizontal rolável das abas. |
| `.tab-button` | Botão de aba com indicador inferior. |
| `.tab-button.is-active` | Aba atual. |

As abas devem continuar usando `aria-selected`, e o painel correspondente deve usar `hidden` quando inativo.

```html
<nav class="tab-list" aria-label="Seções da página">
    <button class="tab-button is-active" aria-selected="true">Resumo</button>
    <button class="tab-button" aria-selected="false">Histórico</button>
</nav>
```

## Formulários

| Classe | Uso |
| --- | --- |
| `.form-grid` | Estrutura vertical ou grade base de formulário. |
| `.form-grid--two` | Formulário com duas colunas em telas amplas. |
| `.field` | Agrupa rótulo, controle, ajuda e erro de um campo. |
| `.field--wide` | Campo que ocupa todas as colunas disponíveis. |
| `.field-label` | Rótulo visual do controle. |
| `.field-hint` | Ajuda curta, condição ou exemplo de preenchimento. |
| `.field--upload` | Região de envio de arquivo com borda tracejada. |

```html
<div class="form-grid form-grid--two">
    <div class="field">
        <label class="field-label" for="nome">Nome</label>
        <input id="nome" name="nome" required>
        <small class="field-hint">Use o nome completo.</small>
    </div>
</div>
```

O elemento `<label>` deve apontar para o controle por `for`. Ajuda e erro podem ser ligados por `aria-describedby`.

## Feedback e estados vazios

| Classe | Uso |
| --- | --- |
| `.feedback` | Mensagens de carregamento, sucesso, informação ou erro. |
| `.empty-state` | Ausência de dados ou conteúdo inicial. |

`.feedback` aceita os contratos existentes `data-variant="success"`, `data-variant="error"`, `data-variant="erro"` e `data-tipo="erro"`. Mensagens vazias não geram superfície visual.

```html
<p class="feedback" role="status" aria-live="polite"></p>
<p class="empty-state">Nenhum registro encontrado.</p>
```

Não use apenas cor para comunicar erro ou sucesso. A mensagem deve explicar o estado e, quando possível, indicar a recuperação.

## Listas

| Classe | Uso |
| --- | --- |
| `.item-list` | Remove marcadores e organiza uma coleção vertical. |
| `.list-item` | Item contínuo separado por divisor, sem card. |
| `.item-meta` | Datas, autoria, turma e demais metadados. |

```html
<ul class="item-list">
    <li class="list-item">
        <strong>Projetor da sala 4</strong>
        <span class="item-meta">20/07/2026 · 3ª aula</span>
    </li>
</ul>
```

Itens inseridos com `createElement()` precisam receber as mesmas classes.

## Métricas

| Classe | Uso |
| --- | --- |
| `.metric-grid` | Grade responsiva de indicadores. |
| `.metric-item` | Indicador sem fundo ou elevação própria. |
| `.metric-label` | Nome curto do indicador. |
| `.metric-value` | Valor principal. |
| `.metric-description` | Contexto ou definição do indicador. |

Métricas usam alinhamento, tipografia e uma linha discreta; não devem virar uma grade de cards coloridos.

## Tabelas

| Classe | Uso |
| --- | --- |
| `.data-table-wrap` | Permite rolagem horizontal sem ampliar a página. |
| `.data-table` | Tabela de dados compartilhada. |

```html
<div class="data-table-wrap">
    <table class="data-table">
        <thead><tr><th>Nome</th><th>Status</th></tr></thead>
        <tbody></tbody>
    </table>
</div>
```

Cabeçalhos devem usar `<th>`. Em tabelas extensas, mantenha o texto essencial nas primeiras colunas e valide a rolagem no celular.

## Tokens principais

Não copie valores literais para folhas de página quando existir token equivalente.

| Grupo | Tokens |
| --- | --- |
| Fonte | `--font-sans` |
| Fundo e superfícies | `--bg-main`, `--surface-0`, `--surface-1`, `--surface-2` |
| Texto | `--text-main`, `--text-muted` |
| Linhas | `--line`, `--line-soft`, `--line-strong` |
| Marca | `--brand`, `--brand-strong`, `--brand-soft`, `--brand-outline` |
| Estados | `--error`, `--success`, `--warning`, `--info`, família `--state-*` |
| Raios | `--radius-sm`, `--radius-md`, `--radius-lg` |
| Espaçamento | `--space-1`, `--space-2`, `--space-3`, `--space-4`, `--space-6`, `--space-8` |
| Larguras | `--page-width`, `--page-width-wide`, `--page-width-compact` |
| Controles | `--control-height`, `--focus-ring`, `--motion-fast` |
| Camadas | família `--z-*` |

## Classes estruturais do shell

Estas classes possuem documentação de implementação nas próprias folhas, mas fazem parte do padrão de página:

- `.app-navbar`: barra superior fixa;
- `.app-sidebar`: navegação lateral do módulo;
- `.app-sidebar-link`: item de navegação;
- `.app-sidebar-link.is-active`: página atual;
- `.app-sidebar-replaced`: navegação antiga mantida no HTML, mas substituída pela lateral.

Novas páginas devem incluir `includes/app_navbar.html`, `includes/app_sidebar_config.html` e `includes/style_bundle.html` em vez de copiar o markup desses componentes.

## Classes específicas e legado

Uma classe específica de módulo é válida quando representa comportamento ou visual exclusivo, por exemplo calendário, gráfico, preview, stepper ou drawer. Ela deve ser combinada com a classe canônica correspondente quando também representar um padrão comum.

```html
<button class="scheduler-header-calendar-btn button">Agenda geral</button>
```

Não remova classes antigas durante uma migração sem verificar CSS, JavaScript e testes. A estratégia atual é aditiva: aplicar a classe compartilhada, preservar o seletor antigo e remover o legado somente em uma etapa posterior dedicada.

Módulos já migrados para esta fundação:

- Recursos administrativos;
- Agendamento;
- Relatórios.

Os demais módulos ainda podem conter classes locais equivalentes. Esta documentação não declara essas classes como parte da API compartilhada.

## Checklist para criar ou migrar uma página

- carregar o CSS por `includes/style_bundle.html`;
- usar `.page-shell` e apenas um modificador de largura;
- usar `.page-header`, `.page-title` e `.page-lead`;
- estruturar conteúdo com `.page-section`, sem cards de layout;
- aplicar `.button` em botões e links de ação;
- agrupar campos com `.field` e ações com `.action-group`;
- usar `.feedback`, `.empty-state`, `.item-list` e `.data-table` quando aplicável;
- aplicar as classes também ao conteúdo criado por JavaScript;
- preservar IDs, `data-*`, atributos ARIA e seletores específicos existentes;
- testar teclado, estados `hidden`/`disabled`, desktop e celular;
- adicionar ou atualizar o teste de contrato do design system.

## Manutenção desta documentação

Toda alteração em `static/css/design-system.css` deve atualizar este arquivo no mesmo commit. Uma classe só é considerada canônica quando:

1. está implementada no design system;
2. está descrita aqui;
3. possui ao menos um consumidor real;
4. está coberta pelo teste de contrato.

Evite adicionar classes para uma necessidade futura. Primeiro confirme o uso em uma página real; depois extraia o padrão compartilhado.
