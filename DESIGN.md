---
name: "Suite Escolar"
description: "Sistema escolar claro e confiavel, organizado para concluir tarefas sem treinamento."
colors:
  primary: "#0f766e"
  primary-strong: "#0b5b55"
  primary-soft: "#d6f2ef"
  background: "#ffffff"
  background-accent: "#d7e9ff"
  surface: "#ffffff"
  surface-subtle: "#f8fbff"
  surface-muted: "#eef3f8"
  text: "#1f2a37"
  text-muted: "#4b5563"
  border: "#d8dee8"
  border-soft: "#d8e1ec"
  border-strong: "#c9d2de"
  danger: "#dc2626"
  success: "#16a34a"
  warning: "#f59e0b"
  info: "#3b82f6"
typography:
  display:
    fontFamily: "Nunito, Avenir Next, Segoe UI, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Nunito, Avenir Next, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Nunito, Avenir Next, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Nunito, Avenir Next, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Nunito, Avenir Next, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.3
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  modal: "20px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.primary-strong}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "48px"
  chip-selected:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "44px"
  surface-primary:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text}"
    rounded: "0"
    padding: "24px"
---

# Sistema de Design: Suite Escolar

## Overview

**Norte Criativo: "Escola em Ordem"**

A interface deve transmitir a sensacao de uma rotina escolar organizada: cada
tela deixa claro o que esta acontecendo, qual e a proxima acao e o que exige
atencao. A aparencia e acolhedora e objetiva, com controles familiares,
linguagem direta e densidade suficiente para o trabalho diario.

O sistema usa uma superficie principal continua por fluxo. Agrupamentos internos
devem ser definidos primeiro por espacamento, alinhamento, titulos e divisores.
Cards sao reservados para unidades independentes, selecionaveis ou transportaveis,
como um recurso, uma solicitacao ou um dialogo. Card dentro de card e proibido
como estrutura habitual.

O verde-petroleo atual e a cor primaria provisoria. Uma migracao futura para o
azul-marinho da identidade escolar deve substituir os tokens sem alterar a
hierarquia semantica dos componentes.

**Caracteristicas principais:**

- Uma acao primaria evidente por tela ou etapa.
- Superficies continuas, com poucos contornos e pouca fragmentacao.
- Controles de produto conhecidos, legiveis e consistentes.
- Hierarquia por espacamento e tipografia antes de bordas e sombras.
- Responsividade estrutural, com alvos de toque adequados no celular.

**A Regra da Superficie Continua.** Um fluxo usa uma superficie principal. Antes
de criar outro card, tente espacamento, divisor, subtitulo ou fundo tonal sem
elevacao.

**A Regra da Troca de Marca.** Cores de acao devem usar tokens semanticos. Nunca
espalhe novos azuis ou verdes literais para preparar a futura identidade.

## Colors

A paleta combina verde-petroleo controlado com superficies claras e neutros
azulados. A cor primaria indica acao, selecao e foco; nao e decoracao.

### Primary

- **Verde Institucional:** cor primaria para botoes principais, selecao atual,
  links importantes e foco.
- **Verde Profundo:** estado de hover e enfase de texto sobre fundos suaves.
- **Verde de Apoio:** fundo de selecoes, badges e informacoes leves.

### Secondary

- **Azul de Contexto:** usado com moderacao em informacoes neutras e superficies
  auxiliares. Nao compete com a acao primaria.

### Neutral

- **Branco de Trabalho:** fundo continuo do corpo, formularios e conteudo.
- **Nevoa Azulada:** fundo da barra lateral e de regioes auxiliares funcionais.
- **Tinta Escolar:** texto principal de alto contraste.
- **Texto de Apoio:** descricoes, metadados e instrucoes.
- **Linhas Estruturais:** bordas e divisores discretos.

### Semantic

- **Sucesso:** confirmacao e estados concluidos.
- **Alerta:** pendencias e situacoes que exigem atencao.
- **Perigo:** falhas, exclusoes e cancelamentos.
- **Informacao:** orientacoes neutras e disponibilidade.

**A Regra do Verde Funcional.** Verde-petroleo aparece em acao primaria, foco,
selecao e estado atual. Nunca use grandes manchas verdes apenas para decorar.

**A Regra do Status Legivel.** Nenhum status depende somente de cor; sempre
combine cor com texto e, quando util, icone ou forma.

## Typography

**Fonte de Display:** Nunito, com Avenir Next, Segoe UI e sans-serif como fallback.

**Fonte de Corpo:** a mesma familia, para preservar familiaridade e consistencia
em uma interface operacional.

**Carater:** amigavel sem ser infantil, legivel em uso rapido e suficientemente
neutro para telas administrativas densas.

### Hierarchy

- **Display** (700, 34px, 1.1): titulo principal de paginas amplas; no celular
  reduz para aproximadamente 24px.
- **Headline** (700, 24px, 1.15): cabecalhos de etapas, paineis e dialogos.
- **Title** (700, 18px, 1.2): titulos de secoes e unidades independentes.
- **Body** (400, 16px, 1.5): conteudo e instrucoes; textos explicativos devem
  permanecer abaixo de 70 caracteres por linha quando possivel.
- **Label** (700, 14px, 1.3): rotulos de campos, botoes e estados.

Textos em caixa alta e tracking ampliado ficam restritos a pequenos status,
etapas ou metadados. Eles nao devem anteceder todas as secoes.

**A Regra da Leitura Rapida.** Titulos dizem a tarefa, descricoes explicam o
proximo passo e rotulos usam termos familiares da escola.

## Elevation

O sistema usa elevacao leve e funcional. A maior parte da hierarquia deve vir de
espacamento, contraste tonal e divisores. Sombras aparecem apenas quando uma
superficie precisa se separar fisicamente do fundo, como navegacao, dialogo,
drawer ou unidade interativa independente.

### Shadow Vocabulary

- **Elevacao baixa** (`0 2px 6px rgba(15, 23, 42, 0.06)`): controles ou
  superficies interativas pequenas.
- **Elevacao media** (`0 8px 24px rgba(15, 23, 42, 0.10)`): superficie principal
  que precisa se destacar do fundo.
- **Elevacao alta** (`0 16px 40px rgba(15, 23, 42, 0.14)`): apenas dialogos,
  drawers e sobreposicoes.

**A Regra do Nivel Unico.** Um bloco com sombra nao deve conter outro bloco com
sombra. Dentro dele, use fundo tonal, divisor ou espaco.

**A Regra da Borda ou Sombra.** Em componentes comuns, escolha a borda como
estrutura principal. Nao combine borda decorativa com sombra ampla.

## Components

### Buttons

- **Forma:** cantos moderados (12px); pill somente em filtros, chips e controles
  compactos.
- **Primario:** verde institucional, texto branco, altura minima de 44px e peso
  700. Existe apenas uma acao primaria dominante por contexto.
- **Hover / Focus:** hover usa o verde profundo; foco usa anel visivel de 3px.
- **Secundario:** fundo branco, borda estrutural e texto escuro.
- **Perigoso:** vermelho e reservado para excluir, cancelar ou remover.
- **Mobile:** acoes finais podem ocupar toda a largura quando isso melhora o
  toque e a leitura.

### Chips

- **Estilo:** formato pill, altura minima de 44px quando selecionavel e texto
  curto.
- **Estado:** neutro em repouso; fundo verde suave e texto verde ao selecionar.
- **Uso:** opcoes mutuamente exclusivas, filtros e status compactos. Nao usar
  chips como substitutos de secoes ou botoes longos.

### Secoes / Containers

- **Superficie principal:** branca e continua com o corpo, sem raio ou elevacao.
- **Unidade independente:** borda discreta, raio entre 12px e 16px e sombra baixa
  somente quando a separacao fisica for importante.
- **Secao interna:** sem sombra. Use espacamento de 16px a 24px, divisor de 1px
  ou fundo tonal sutil.
- **Cards aninhados:** proibidos como padrao. Um card interno so e aceitavel
  quando representa um objeto independente e acionavel.

### Inputs / Fields

- **Estilo:** fundo branco, borda de 1px, raio de 12px, altura de 48px e texto de
  16px.
- **Focus:** borda primaria e anel visivel de 3px.
- **Erro:** mensagem especifica proxima ao campo; cor nunca e o unico sinal.
- **Disabled:** reducao de contraste acompanhada de explicacao quando bloquear o
  progresso.

### Navigation

A barra superior mantem logo, contexto atual e acesso ao menu. O drawer agrupa
modulos por permissao e acoes de conta. Navegacao nao deve disputar atencao com a
acao primaria da pagina. No celular, a logo reduz e o menu permanece acessivel
por alvo de toque de pelo menos 40px.

### Fluxos Guiados

Tarefas complexas usam etapas claras, validacao antes de avancar e resumo antes
da confirmacao. A etapa ativa usa a cor primaria; etapas concluidas usam estado
de sucesso. Conteudo nao deve ficar invisivel dependendo de animacao. Transicoes
duram entre 150ms e 280ms e respeitam `prefers-reduced-motion`.

### Modals and Drawers

Dialogos sao reservados para confirmacao, recuperacao e bloqueios que exigem
decisao imediata. Informacao complementar extensa deve preferir drawer ou pagina
dedicada. Sobreposicoes usam elevacao alta e bloqueiam o scroll de fundo.

## Do's and Don'ts

### Do:

- **Do** use uma unica superficie principal para conduzir cada fluxo.
- **Do** use espacamento de 16px a 24px e divisores antes de criar outro card.
- **Do** mantenha controles com altura minima de 44px e foco visivel.
- **Do** use verde-petroleo para acao, foco, selecao e estado atual.
- **Do** preserve nomes semanticos de tokens para permitir a futura troca pelo
  azul-marinho da escola.
- **Do** mostre resumo antes de imprimir, reservar, cancelar ou excluir.
- **Do** mantenha estados de carregamento, vazio, erro, sucesso e bloqueio claros.
- **Do** transforme tabelas largas em estruturas legiveis no celular.

### Don't:

- **Don't** use card dentro de card para separar cada pequeno grupo de campos.
- **Don't** transforme todas as secoes em caixas com borda, raio e sombra.
- **Don't** faca o produto parecer um painel tecnico de servidor, um dashboard
  empresarial generico ou uma landing page promocional.
- **Don't** apresente telas densas com varias acoes competindo pela prioridade.
- **Don't** use terminologia tecnica sem explicacao ou exija que o usuario
  entenda como o sistema foi implementado.
- **Don't** trate novidade visual como substituto de usabilidade; controles
  familiares e consistentes vencem interacoes incomuns.
- **Don't** use efeitos decorativos, gradientes de texto, glassmorphism ou
  animacao sem funcao de estado.
- **Don't** use faixas coloridas laterais como acento em cards ou alertas.
- **Don't** use raio acima de 20px em cards comuns; 20px fica reservado para
  dialogos e superficies excepcionais.
- **Don't** misture verde-petroleo e azul-marinho como duas cores primarias
  concorrentes durante a futura migracao de marca.
