---
type: "query"
date: "2026-07-14T12:52:48.282174+00:00"
question: "Criar edição do sexo dos estudantes diretamente na tabela da turma selecionada"
contributor: "graphify"
outcome: "useful"
source_nodes: ["renderTabelaEstudantes", "salvarEstudante", "cadastros.js", "painel.js"]
---

# Q: Criar edição do sexo dos estudantes diretamente na tabela da turma selecionada

## Answer

Expansão usada: cadastro, editar, edicao, estudante, estudantes, painel, salvar, select, tabela, turma, turmas. A coluna Sexo agora usa um select por linha com salvamento automático pela API existente, estado aria-busy, anúncio de sucesso/erro e restauração do valor anterior em falha. O formulário tradicional permanece para nome e turma. Trinta e cinco testes e verificações de sintaxe passaram.

## Outcome

- Signal: useful

## Source Nodes

- renderTabelaEstudantes
- salvarEstudante
- cadastros.js
- painel.js