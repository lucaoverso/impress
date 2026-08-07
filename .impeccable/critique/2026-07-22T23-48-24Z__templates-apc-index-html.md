---
target: comparação visual da Central de Anexos com o Stitch
total_score: 23
p0_count: 0
p1_count: 3
score: 23
p0: 0
p1: 3
timestamp: 2026-07-22T23-48-24Z
slug: templates-apc-index-html
---
## Design Health Score

| # | Heurística | Nota | Problema principal |
|---|---|---:|---|
| 1 | Visibilidade do estado | 3 | Estados existem, mas competem com títulos e metadados. |
| 2 | Correspondência com o mundo real | 3 | Aulas e anexos estão claros. |
| 3 | Controle e liberdade | 3 | As ações principais estão disponíveis. |
| 4 | Consistência e padrões | 2 | O vocabulário visual diverge da referência. |
| 5 | Prevenção de erros | 2 | O envio não evidencia formato, limite ou arrastar e soltar. |
| 6 | Reconhecimento em vez de memória | 3 | Contexto de demanda, aula e turma está visível. |
| 7 | Flexibilidade e eficiência | 2 | A área de envio parece um formulário nativo, não um fluxo guiado. |
| 8 | Estética e design minimalista | 1 | Contêiner gigante, excesso de respiro e hierarquia pesada. |
| 9 | Recuperação de erros | 2 | A correção existe, mas não está demonstrada no estado pendente. |
| 10 | Ajuda e documentação | 2 | Instruções da coordenação e regras do arquivo não têm presença constante. |
| **Total** | | **23/40** | **Precisa de revisão visual estrutural** |

## Anti-Patterns Verdict

A tela atual parece um dashboard administrativo genérico. Não está visualmente alinhada à referência além do modelo mestre-detalhe. O detector determinístico não encontrou violações sintáticas no template; isso não contradiz a avaliação, porque o problema é de composição e escala, não de padrões mecânicos detectáveis.

## Overall Impression

A implementação está funcional e legível, mas reinterpretou a referência em vez de reproduzi-la. O maior desvio é transformar uma superfície aberta e editorial em um grande cartão administrativo, com tipografia muito maior e formulário compacto.

## What's Working

- A separação entre demandas e detalhe foi preservada.
- Estados pendente e prazo encerrado são reconhecíveis.
- Enviar arquivo e criar atividade permanecem ações explícitas.

## Priority Issues

### [P1] Composição diferente da referência

O Stitch usa uma superfície contínua, divisor vertical simples e conteúdo começando logo após os controles. A implementação envolve tudo em um contêiner alto com borda e grande vazio inferior. Remover o grande cartão e reconstruir a grade aberta nas proporções aproximadas de 35/65.

### [P1] Escala tipográfica e densidade incompatíveis

O H1, o título da demanda e os itens da lista estão muito maiores e pesados. A referência tem hierarquia mais compacta, com títulos serifados e metadados menores. Reduzir escala, peso e espaçamentos; aproximar as alturas de linha e os recuos da referência.

### [P1] Área de envio não reproduz o componente central do Stitch

O Stitch apresenta um dropzone grande, centralizado, com ícone, instrução e ação secundária. A implementação mostra um input nativo dentro de uma caixa curta e dois botões equivalentes. Criar dropzone amplo, deixar a seleção como ação dominante e mover o salvamento para a ação persistente do fluxo.

### [P2] Lista de demandas virou cartões ricos demais

A referência usa linhas compactas; apenas a seleção recebe contorno e fundo. A implementação adiciona mais metadados, badges grandes e altura. Simplificar itens não selecionados e reduzir a altura do selecionado.

### [P2] Cabeçalho e instruções perderam a cadência da referência

Ano e calendário deveriam formar um conjunto compacto, com contagem de pendências à direita. O detalhe deveria seguir título, contexto, instruções e anexo. Atualmente há nome do usuário, grande separação e uma barra de controles dispersa.

## Persona Red Flags

**Professora com pouco tempo:** enxerga uma grande moldura vazia e precisa localizar o formulário pequeno; o Stitch conduz o olhar diretamente ao anexo.

**Professora pouco habituada a sistemas:** o input nativo e os dois botões de mesmo peso não explicam claramente se deve escolher, criar ou enviar primeiro.

**Coordenação:** a lista alta reduz a quantidade de demandas visíveis e dificulta comparação rápida.

## Minor Observations

- O botão de calendário ficou isolado demais.
- A informação do usuário repete contexto já fornecido pela navegação.
- O badge de status ocupa mais atenção que o conteúdo da aula.
- A largura da coluna esquerda está aceitável, mas o padding interno a faz parecer mais estreita.

## Questions to Consider

- A meta é copiar a composição do Stitch ou apenas usar as mesmas cores?
- O envio deve ser a ação dominante da tela, como na referência?
- A tipografia serifada dos títulos deve ser reproduzida apenas nesta área central?
