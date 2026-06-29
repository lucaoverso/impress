# Relacionamentos Do Dominio

Status: resumo conceitual inicial.

## Relacoes Centrais

| Dominio | Relacao conceitual | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Identidade | Usuario autentica por tokens e atua como professor, coordenador ou admin. | `database.py`: `usuarios`, `tokens`; `auth.py`; `routers/common.py`. | Confirmada pelo codigo |
| Impressao | Usuario solicita jobs e consome cotas mensais. | `database.py`: `jobs`, `cotas`; `modules/printing/*`. | Inferida: `jobs.usuario_id` e `cotas.usuario_id` nao possuem FK fisica declarada. |
| Agendamento | Usuario reserva recurso em data/aula, com status ativo/cancelado. | `database.py`: `agendamentos`; `modules/scheduling/*`. | Confirmada pelo codigo |
| Academico | Turmas possuem estudantes; disciplinas sao associadas a turmas e professores. | `database.py`: `turmas`, `estudantes`, `disciplinas`, `turmas_disciplinas`, `professores_turmas_disciplinas`. | Confirmada pelo codigo |
| Horario escolar | Turma, disciplina e professor sao alocados por ano/dia/aula. | `migrations/20260511_create_horario_escolar_module.py`. | Confirmada pelo codigo |
| Pre-conselho | Periodo agrupa registros de estudantes por professor/turma/disciplina e motivos. | `database.py`: `pre_conselho_*`. | Confirmada pelo codigo |
| Ocorrencias | Ocorrencia referencia estudante/turma/professor e pode manter itens de regimento. | `database.py`: `ocorrencias`, `ocorrencia_regimento_itens`. | Confirmada pelo codigo |
| APC | Periodo solicita envios por professor/turma/disciplina, com historico, preview e revisao. | `migrations/20260511_create_apc_module.py`; migrations APC posteriores. | Confirmada pelo codigo |
| Auditoria | Eventos registram ator, categoria, acao, resultado e entidade afetada. | `migrations/20260615_create_audit_events.py`; `modules/audit/models.py`. | Confirmada pelo codigo |

## Diagrama

O diagrama ER detalhado esta em `docs/07-dados/relacionamentos.md`.

## Pendencias

- Confirmar quais vinculos academicos sao atuais e quais sao legado (`professores_turmas_disciplinas` versus `turmas_disciplinas`). **Pendente de validacao**.
- Confirmar se relacoes logicas sem FK fisica devem virar restricoes de banco. **Pendente de validacao**.
