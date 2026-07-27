---
type: "query"
date: "2026-07-21T22:53:13.938989+00:00"
question: "O que acontece com a APC hoje se eu trocar a data de uma demanda? Quem enviou é perdido? Se o professor ter aula para o dia que eu trocar mantem o envio dele?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["atualizar_apc_periodo", "_obter_elegiveis_periodo", "montar_painel_periodo_apc", "apc.js"]
---

# Q: O que acontece com a APC hoje se eu trocar a data de uma demanda? Quem enviou é perdido? Se o professor ter aula para o dia que eu trocar mantem o envio dele?

## Answer

Expanded from original query via graph vocab: [apc, demanda, data, date, envio, envios, submission, professor, teacher, aula, schedule, solicitacao]. A edição mantém o mesmo periodo_id e não apaga apc_envios. Para HORARIO_DIA, a elegibilidade é recalculada pelo dia da semana da nova data e pelo tipo da entrega. A interface associa o envio pela chave exata professor_id, turma_id e disciplina_id. Se a mesma chave continuar elegível, o envio permanece visível. Se o professor deixar de ser elegível, ou tiver aula apenas em outra turma ou disciplina, o registro e arquivo continuam no banco, mas ficam fora do painel normal, enquanto a nova chave aparece pendente. O prazo é campo separado e não acompanha automaticamente a troca da data na interface.

## Outcome

- Signal: useful

## Source Nodes

- atualizar_apc_periodo
- _obter_elegiveis_periodo
- montar_painel_periodo_apc
- apc.js