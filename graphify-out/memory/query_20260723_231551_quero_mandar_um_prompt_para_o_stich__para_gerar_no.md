---
type: "query"
date: "2026-07-23T23:15:51.035931+00:00"
question: "Quero mandar um prompt para o stich, para gerar nova UI das ocorrências da coordenação. Me indique os requisitos que eu devo mandar para ele"
contributor: "graphify"
outcome: "useful"
source_nodes: ["ocorrencias.js", "ocorrencias_router.py", "coordenacao.html", "painel.js", "OcorrenciaOut"]
---

# Q: Quero mandar um prompt para o stich, para gerar nova UI das ocorrências da coordenação. Me indique os requisitos que eu devo mandar para ele

## Answer

Expanded from original query via vocab: [ocorrencia, ocorrencias, coordenacao, status, filtros, detalhes, editar, regimento, anexo, pdf, gravidade, permissao]. A UI atual exige: visão de acompanhamento com totais por status; filtros por referência, tipo, turma, status e período; tabela com data, tipo, referência, contexto, ação, status e ações; detalhe selecionado; criação e edição em três etapas (contexto, descrição, base legal e fechamento); prévia A4; PDF, edição e exclusão; tipos estudante, professor e geral; estados registrado, em acompanhamento, aguardando responsável e resolvido; acesso restrito à gestão. O redesenho deve preservar o shell, contratos e fluxos, usar o design system Suite Escolar, ser responsivo e WCAG AA, e cobrir loading, vazio, erro, sucesso e confirmação destrutiva.

## Outcome

- Signal: useful

## Source Nodes

- ocorrencias.js
- ocorrencias_router.py
- coordenacao.html
- painel.js
- OcorrenciaOut