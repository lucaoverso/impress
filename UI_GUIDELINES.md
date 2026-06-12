# UI_GUIDELINES.md - Padrao de UI da Suite Escolar

## 1. Referencia e objetivo

O novo padrao de UI da Suite Escolar e definido por `templates/agendamento.html`
e por sua implementacao em `static/css/base.css`, `static/css/components.css`,
`static/css/pages/scheduling-flow.css` e `static/js/agendamento.js`.

Ele deve ser adotado gradualmente, um modulo por vez, sem alterar regras de
negocio, rotas, permissoes ou contratos existentes.

> Uma superficie de trabalho continua conduz o usuario ate concluir uma tarefa.

A interface deve ser calma, confiavel e familiar. Nao deve parecer dashboard
generico, painel tecnico ou pagina promocional.

## 2. Principios obrigatorios

### Uma tarefa principal

Cada tela deve deixar claro:

1. onde o usuario esta;
2. o que precisa fazer agora;
3. o que ja selecionou;
4. qual e a proxima acao.

Existe uma acao primaria por etapa. Historicos, consultas e configuracoes
secundarias nao competem com ela.

### Superficie continua

Fluxos usam um workspace principal, como `.scheduler-workspace`. Dentro dele,
prefira espacamento, alinhamento, titulos, divisores e fundos tonais.

Cards ficam reservados para objetos independentes ou selecionaveis, como um
recurso, arquivo, reserva ou dialogo. Card dentro de card nao e estrutura padrao.

### Complexidade progressiva

- Mostre apenas o necessario para a decisao atual.
- Revele campos depois da escolha que os torna relevantes.
- Use disclosure para opcoes realmente opcionais.
- Valide antes de avancar.
- Mostre resumo antes de confirmar uma acao importante.

### Contexto persistente

Fluxos longos devem manter compreensivel o que ja foi escolhido: recurso, data,
aula, turma, pessoa, quantidade, filtros ou estado relevante.

No mobile, condense ou incorpore esse contexto ao conteudo atual quando ele
repetir informacao ja evidente.

### Linguagem escolar

Titulos nomeiam a tarefa; descricoes explicam o proximo passo.

| Evitar | Preferir |
|---|---|
| Job | Pedido de impressao |
| Submeter | Enviar |
| Resource booking | Reserva de recurso |
| Dashboard | Painel |
| Input invalido | Verifique este campo |
| Operacao realizada | Acao concluida |

## 3. Anatomia da tela

```text
Navbar global
  Workspace
    Cabecalho da tarefa
    Progresso ou ferramentas locais
    Contexto persistente
    Conteudo da etapa
    Acoes da etapa
    Feedback
  Drawer ou dialogo secundario
```

### Navbar

Informa produto, area atual e navegacao geral. Nao concentra a acao principal
da pagina. Acoes adicionais devem ser poucas, contextuais e acessiveis.

### Cabecalho

Use titulo curto, descricao de uma linha e acao secundaria opcional.

```text
Agendar equipamento
Escolha as aulas em que o equipamento sera utilizado.
[Agenda geral]
```

Evite banners decorativos, metricas heroicas e sombras amplas.

### Stepper

Use apenas quando houver ordem real, decisoes distintas e resumo final.

Estados: atual, concluida ou pronta, futura ou bloqueada. Combine numero, texto,
forma e `aria-current`; nunca dependa apenas de cor. No mobile, rotulos podem
ser visualmente condensados, mas continuam acessiveis.

### Etapa

Cada etapa possui titulo orientado a acao, instrucao breve, controles
relacionados, feedback proximo da origem e acoes no final.

Nao repita "Etapa X de Y" quando o stepper ja comunica isso.

### Acoes

No desktop, voltar fica a esquerda e continuar ou confirmar a direita. No
mobile, ficam empilhadas e ocupam a largura disponivel.

O texto indica destino ou consequencia: `Continuar para detalhes`, `Continuar
para resumo`, `Confirmar reserva`, `Salvar alteracoes`.

## 4. Sistema visual

Os tokens canonicos vivem em `static/css/base.css`:

```css
:root {
  --font-sans: "Nunito", "Avenir Next", "Segoe UI", sans-serif;
  --surface-0: #ffffff;
  --surface-1: #f8fbff;
  --surface-2: #eef3f8;
  --text-main: #1f2a37;
  --text-muted: #4b5563;
  --line: #d8dee8;
  --line-soft: #d8e1ec;
  --line-strong: #c9d2de;
  --brand: #0f766e;
  --brand-strong: #0b5b55;
  --brand-soft: #d6f2ef;
  --error: #dc2626;
  --success: #16845b;
  --warning: #b66a12;
  --info: #326fa8;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --shadow-low: 0 2px 6px rgba(15, 23, 42, 0.06);
  --focus-ring: 0 0 0 3px rgba(15, 118, 110, 0.24);
  --motion-fast: 180ms cubic-bezier(0.22, 1, 0.36, 1);
}
```

### Cor

A cor primaria indica acao, selecao, foco, etapa atual e link importante. Nao e
decoracao. Status combinam cor com texto. Use tokens semanticos em vez de novas
cores literais.

### Tipografia

- titulo de pagina: `26px`, peso 700;
- titulo de etapa: `20px`, peso 700;
- titulo de secao: `15px` a `18px`, peso 700;
- corpo: `14px` a `16px`;
- metadado: `11px` a `13px`.

Use uma familia, textos explicativos de ate `65ch` e caixa alta apenas em
metadados pequenos. Nao use fonte display em labels, botoes ou dados.

### Forma e espacamento

- controles compactos: raio de `6px` a `8px`;
- inputs e objetos selecionaveis: `8px` a `12px`;
- workspace: ate `16px`;
- dialogos: ate `20px`;
- pills: apenas chips, badges e filtros curtos;
- largura de fluxo: aproximadamente `1080px`;
- padding desktop: `28px` a `32px`;
- padding mobile: `16px`;
- distancia entre grupos: `16px` a `24px`;
- altura minima de controle: `44px`.

Use borda como estrutura. Sombras ficam para navbar, drawer, dialogo ou outra
camada fisicamente sobreposta. Nao combine borda decorativa com sombra ampla.

## 5. Componentes e estados

### Botoes

Todo botao possui default, hover, focus-visible, active, disabled e loading
quando houver requisicao.

- primario: concluir ou avancar;
- secundario: voltar, editar ou consultar;
- discreto: acao leve;
- perigoso: cancelar, excluir ou remover.

### Selecao de objetos

Recursos, arquivos e entidades selecionaveis usam controle nativo, nome,
metadado e estado perceptivel sem depender apenas de cor. Use `aria-pressed` ou
controle de formulario equivalente.

Rolagem horizontal deve ser intencional, visivel ao toque e, quando util, usar
`scroll-snap`.

### Listas e formularios

Para comparacao, prefira linhas estruturadas a grades de cards identicos.
Desktop pode usar colunas; mobile reorganiza a mesma informacao por prioridade.

Todo campo tem label. Ajuda aparece antes do erro. Erro explica o problema e
como corrigi-lo. Placeholder nao substitui label. Validacao final fica no
backend.

### Feedback

Prever loading, vazio, sucesso, erro, indisponivel, sem permissao e resultado
parcial. Estado vazio orienta o proximo passo. Use `aria-live` para mensagens
dinamicas importantes, sem anuncios excessivos.

### Drawers e dialogos

Drawer preserva o fluxo enquanto mostra agenda, historico, detalhes ou painel
pessoal. Dialogo fica reservado a uma decisao curta e bloqueante.

Requisitos:

- `role="dialog"`, `aria-modal="true"` e titulo associado;
- foco movido para a camada e contido enquanto aberta;
- `Escape` fecha quando seguro;
- foco retorna ao disparador;
- scroll de fundo bloqueado;
- conteudo inativo usa `inert`.

## 6. Responsividade, acessibilidade e movimento

Responsividade muda a estrutura, nao apenas o tamanho da fonte.

Desktop usa workspace centralizado, stepper completo, listas em colunas, acoes
divididas e contexto visivel.

Mobile usa padding de `12px` a `16px`, controles de pelo menos `44px`, acoes em
largura total, stepper condensado e listas reorganizadas. Nao pode haver scroll
horizontal acidental. `760px` e referencia atual, nao regra absoluta.

Meta de acessibilidade: WCAG 2.2 AA.

- contraste de texto normal de pelo menos `4.5:1`;
- foco visivel e ordem de teclado coerente;
- HTML semantico, labels e nomes acessiveis;
- alvos de toque de `44x44px` nos fluxos principais;
- status que nao dependem apenas de cor;
- erros associados ao contexto;
- teclado funcional em drawers, dialogos e seletores;
- icones decorativos com `aria-hidden="true"`;
- `prefers-reduced-motion` respeitado.

Movimento comunica estado, dura normalmente `150ms` a `250ms` e prioriza
`opacity`, `transform`, cor e borda. Sem bounce, coreografia decorativa ou
conteudo que dependa da animacao para aparecer.

## 7. Padroes proibidos

- cards aninhados como organizacao padrao;
- grades interminaveis de cards identicos;
- faixa colorida lateral como acento;
- texto em gradiente ou glassmorphism decorativo;
- sombra ampla junto de borda em componentes comuns;
- raio acima de `20px` em superficies comuns;
- pill aplicado indiscriminadamente;
- eyebrow em caixa alta antes de toda secao;
- modal como primeira solucao;
- cores literais duplicando tokens;
- JavaScript como unica validacao critica;
- animacao que esconda conteudo ate ser executada.

## 8. O que copiar do agendamento

Padroes reutilizaveis:

- workspace unico com cabecalho, progresso e conteudo;
- contexto persistente;
- uma decisao principal por etapa;
- consulta secundaria em drawer;
- confirmacao perigosa em dialogo;
- lista densa no desktop e reorganizada no mobile;
- selecao semantica com feedback imediato;
- resumo antes da confirmacao;
- foco, `inert`, `aria-live` e reducao de movimento.

Nao copiar automaticamente elementos do dominio, como semana, calendario,
capacidade, aula, turno, turma e disponibilidade.

> Copie a logica de composicao, nao a aparencia literal de cada controle.

## 9. Adocao e checklist

Refatorar um modulo por vez:

1. identificar tarefa, estados e acoes secundarias;
2. definir a anatomia do workspace;
3. reutilizar tokens e componentes existentes;
4. posicionar consultas em regiao, drawer ou pagina adequada;
5. adaptar desktop e mobile;
6. validar acessibilidade e estados;
7. preservar backend, templates e JavaScript.

Um padrao usado em mais de uma tela deve migrar para
`static/css/components.css` ou componente compartilhado apropriado.

Checklist de revisao:

- [ ] Existe uma acao primaria clara e um inicio evidente?
- [ ] Complexidade e contexto sao apresentados progressivamente?
- [ ] Existe resumo antes de acao importante?
- [ ] A tela usa uma superficie principal sem cards desnecessarios?
- [ ] Cores, raios, sombras e tipografia seguem os tokens?
- [ ] Loading, vazio, erro, sucesso e indisponibilidade foram previstos?
- [ ] Disabled e erros explicam o requisito ou a correcao?
- [ ] Funciona em desktop, tablet, celular e teclado?
- [ ] Nao existe scroll horizontal acidental?
- [ ] Controles principais possuem pelo menos `44px`?
- [ ] Contraste, foco, labels e estados atendem WCAG AA?
- [ ] Drawers e dialogos gerenciam foco, `Escape` e retorno?
- [ ] Movimento respeita `prefers-reduced-motion`?
- [ ] Rotas, contratos e regras de backend foram preservados?
- [ ] O novo padrao compartilhado foi documentado?

## 10. Definicao de pronto

Uma refatoracao de UI esta pronta quando preserva comportamento, usa esta
hierarquia, possui estados completos, funciona em mobile e teclado, atende
WCAG 2.2 AA nos fluxos principais, reutiliza componentes e foi revisada
visualmente em desktop e celular.

> O usuario deve perceber a tarefa, o contexto e a proxima acao antes de
> perceber os componentes da interface.
