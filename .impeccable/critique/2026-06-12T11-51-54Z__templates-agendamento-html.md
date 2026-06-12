---
target: critique templates/agendamento.html adequado ao DESIGN.md
total_score: 24
p0_count: 0
p1_count: 3
timestamp: 2026-06-12T11-51-54Z
slug: templates-agendamento-html
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Ha feedback e botoes desabilitados, mas falta progresso persistente das cinco etapas. |
| 2 | Match System / Real World | 3 | A linguagem e escolar, mas "Ver agenda", "Turma base" e "1o -> ultimo" exigem interpretacao. |
| 3 | User Control and Freedom | 3 | Existem Voltar, Fechar e Escape, mas drawers e dialogos nao gerenciam foco. |
| 4 | Consistency and Standards | 2 | O fluxo mistura componentes de impressao, cards de calendario, pills e alturas de controle diferentes. |
| 5 | Error Prevention | 3 | Ha confirmacao, restricoes e estados disabled; os erros continuam distantes do campo de origem. |
| 6 | Recognition Rather Than Recall | 2 | O usuario nao ve o mapa completo do fluxo e precisa reencontrar contexto apos a mudanca de layout. |
| 7 | Flexibility and Efficiency | 2 | Ha selecao multipla e repeticao de aulas, mas faltam atalhos e os controles de ordenacao sao pesados. |
| 8 | Aesthetic and Minimalist Design | 2 | A hierarquia existe, mas cards dentro de cards fragmentam a tarefa e competem visualmente. |
| 9 | Error Recovery | 2 | Mensagens sao claras, mas globais; falhas parciais ficam condensadas em uma linha. |
| 10 | Help and Documentation | 2 | Ha instrucoes por etapa, mas pouca ajuda contextual para disponibilidade, agenda geral e repeticao. |
| **Total** | | **24/40** | **Aceitavel: base solida, melhorias significativas necessarias.** |

## Anti-Patterns Verdict

**LLM assessment:** a tela nao parece imediatamente gerada por IA. Ela possui
regras de negocio reais, linguagem contextual e estados ricos. Ainda assim, a
combinacao recorrente de card com gradiente, borda, raio grande e sombra cria uma
sensacao de interface montada por blocos. Isso conflita com "Escola em Ordem",
principalmente quando uma superficie elevada contem outra superficie elevada.

**Deterministic scan:** o detector retornou zero ocorrencias para
`templates/agendamento.html`. O resultado e util como confirmacao de que nao ha
anti-padroes sintaticos obvios no template, mas nao invalida os problemas
estruturais encontrados em CSS e JavaScript.

**Visual overlays:** nao foi possivel executar inspecao visual ou sobreposicao no
navegador porque esta sessao nao oferece automacao de browser. A avaliacao usou
template, estilos responsivos e comportamento do JavaScript como evidencias.

## Overall Impression

O fluxo tem boa intencao: seleciona recursos, localiza uma aula, permite repetir,
coleta detalhes e confirma. O maior ganho viria de apresentar tudo como uma unica
jornada continua. Hoje a interface muda de topologia no meio do processo e
empilha superficies demais, justamente onde o usuario precisa sentir seguranca.

## What's Working

- O fluxo usa divulgacao progressiva: etapas posteriores ficam ocultas ate haver
  recursos e uma aula validos.
- Acoes importantes possuem textos objetivos, como "Confirmar reserva", e o
  cancelamento exige confirmacao.
- A implementacao contempla selecao de varios recursos, repeticao em outras aulas,
  resumo final, estados de disponibilidade e mensagens em `aria-live`.

## Priority Issues

### [P1] O progresso das cinco etapas nao e visivel como sistema

**Why it matters:** cada card mostra apenas "Etapa N". O usuario nao sabe quantas
etapas faltam, quais foram concluidas ou por que a composicao muda depois da
selecao da aula. O JavaScript possui logica para um stepper, mas os elementos
referenciados nao existem no template.

**Fix:** adicionar um indicador compacto e persistente com as cinco etapas,
marcando atual, concluidas e futuras. Manter o mesmo cabecalho e a mesma largura
de superficie durante todo o fluxo.

**Suggested command:** `$impeccable shape`

### [P1] Cards aninhados quebram a Regra da Superficie Continua

**Why it matters:** etapas 3 a 5 usam `print-step-card`, dentro dele
`print-config-section`, depois `scheduler-selected-lesson-card`,
`scheduler-lesson-detail-card` ou itens individuais do resumo. Drawers repetem o
mesmo padrao. A tarefa parece mais complexa do que realmente e.

**Fix:** usar uma superficie principal por etapa. Transformar secoes internas em
blocos sem sombra, separados por espaco, titulo e divisor. No resumo, usar uma
lista de definicoes continua em vez de uma caixa para cada valor.

**Suggested command:** `$impeccable distill`

### [P1] Drawers, dialogo e transicoes de etapa nao administram foco

**Why it matters:** abrir um drawer apenas muda `aria-hidden`; nao ha foco inicial,
armadilha de foco nem retorno ao acionador. O dialogo de cancelamento tambem nao
recebe foco. Usuarios de teclado podem continuar navegando no conteudo oculto ou
perder a posicao.

**Fix:** registrar o acionador, mover foco para o titulo ou primeiro controle,
conter Tab dentro da sobreposicao, restaurar foco ao fechar e marcar o painel
como dialogo acessivel. Ao mudar de etapa, focar o novo `h2`.

**Suggested command:** `$impeccable harden`

### [P2] Existem caminhos e controles concorrentes demais

**Why it matters:** "Ver agenda" e "Continuar" revelam a mesma area em modos
diferentes, sem explicar claramente a diferenca. Nos drawers, cinco ou seis
botoes de ordenacao aparecem juntos; alguns possuem apenas 32px de altura e o
texto "1o -> ultimo" e pouco natural.

**Fix:** renomear "Ver agenda" para "Consultar agenda sem selecionar recursos" ou
mover a consulta para uma acao secundaria discreta. Substituir os botoes de
ordenacao por dois controles: "Ordenar por" e "Ordem", mantendo agrupamento como
toggle separado. Garantir alvos de 44px.

**Suggested command:** `$impeccable clarify`

### [P2] Erros e falhas parciais aparecem longe do ponto de decisao

**Why it matters:** toda validacao termina em `msgAgendamento`, abaixo da coluna
principal. Em etapas 4 e 5, o usuario pode nao ver a mensagem. Falhas parciais em
varias reservas sao comprimidas em uma unica linha e apenas duas sao detalhadas.

**Fix:** adicionar erro inline no campo ou aula correspondente, resumo de erros no
topo da etapa ativa e uma lista expansivel para falhas parciais. Preservar os
dados preenchidos e oferecer "Tentar novamente apenas as falhas".

**Suggested command:** `$impeccable harden`

## Persona Red Flags

**Jordan, primeira utilizacao:** entende a etapa 1, mas nao sabe a diferenca entre
"Ver agenda" e "Continuar". Depois de selecionar uma aula, a interface muda para
duas colunas sem mostrar um mapa do processo. Pode acreditar que voltou ou abriu
outro painel.

**Sam, usuario de teclado ou leitor de tela:** consegue usar os botoes de recurso,
mas ao abrir calendario, detalhes ou confirmacao o foco nao acompanha a
sobreposicao. O `aria-hidden` sozinho nao impede navegacao pelo conteudo de fundo.
O salto de `h2` para `h4` em "Agenda do dia" enfraquece a estrutura de titulos.

**Casey, celular e com interrupcoes:** encontra alvos de 36px na navegacao semanal
e controles de 32px na ordenacao. Carrosseis horizontais de recursos e dias
dependem de descoberta por gesto. Sem progresso persistente, retomar o fluxo apos
uma interrupcao exige reconstruir mentalmente o estado.

**Professor entre aulas:** precisa concluir a reserva rapidamente. A selecao de
recursos e aula e eficiente, mas as etapas opcionais, a mudanca de layout e o
excesso de caixas aumentam o tempo de verificacao antes de confirmar.

## Minor Observations

- Trocar o `h4` de "Agenda do dia" por `h3` para manter a hierarquia.
- Corrigir acentuacao e texto: "horario", "Calendario", "Voce" e "1o -> ultimo".
- O cabecalho da pagina usa raio de 24px e sombra ampla, acima do limite definido
  no DESIGN.md para superficies comuns.
- Cards de recurso usam raio de 22px, gradiente e sombra, tambem acima do sistema
  atual.
- `setMensagem` aplica cores literais no JavaScript; deve usar variantes CSS
  semanticas para facilitar a futura migracao ao azul-marinho.
- O resumo final deveria mostrar data e disciplina explicitamente, nao apenas
  "Turma base", professor e quantidade.

## Questions to Consider

- E realmente necessario manter o contexto completo da agenda ao lado das etapas
  3 a 5, ou um resumo compacto seria mais confiavel?
- "Repetir em outras aulas" merece uma etapa obrigatoria ou deveria ser uma opcao
  dentro da selecao de aula?
- O que um professor precisa confirmar em cinco segundos antes de clicar em
  "Confirmar reserva"?
- A consulta de agenda geral pertence ao fluxo de criar reserva ou a uma tela de
  consulta separada?
