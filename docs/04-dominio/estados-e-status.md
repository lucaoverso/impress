# Estados E Status

Status: catalogo inicial extraido do codigo.

## Convencoes

- **Confirmada pelo codigo**: valor aparece em constantes, CHECK de tabela, model ou service.
- **Inferida**: valor aparece em consultas/fluxos, mas sem enum formal unico.
- **Pendente de validacao**: exige confirmacao funcional.

## Status E Enums

| Contexto | Valores | Onde aparece | Classificacao |
| --- | --- | --- | --- |
| Impressao/job | `PENDENTE`, `PROCESSANDO`, `IMPRIMINDO`, `CONCLUIDO`, `FINALIZADO`, `CANCELADO`, `ERRO`. | `database.py`: insercao/listagem/cancelamento de jobs; `services/worker.py`: atualizacao para `CONCLUIDO`; `modules/printing/policies.py`: `print_job_can_be_reused`. | Inferida: conjunto consolidado a partir de usos em funcoes diferentes. |
| Agendamento | `ATIVO`, `CANCELADO`. | `database.py`: `STATUS_AGENDAMENTO_ATIVO`, `STATUS_AGENDAMENTO_CANCELADO`, tabela `agendamentos`; `modules/scheduling/service.py`: `ensure_reservation_can_be_cancelled`. | Confirmada pelo codigo. |
| Pre-conselho periodo | `ABERTO`, `FECHADO`. | `services/preconselho_service.py`: `STATUS_PERIODO_PRE_CONSELHO_VALIDOS`; `database.py`: `pre_conselho_periodos`. | Confirmada pelo codigo. |
| Ocorrencia status | `registrado`, `em_acompanhamento`, `aguardando_responsavel`, `resolvido`. | `database.py`: `STATUS_OCORRENCIA_VALIDOS` e CHECK de `ocorrencias.status`. | Confirmada pelo codigo. |
| Ocorrencia tipo de registro | `estudante`, `professor`, `geral`. | `database.py`: `TIPOS_REGISTRO_OCORRENCIA` e CHECK de `ocorrencias.tipo_registro`. | Confirmada pelo codigo. |
| Ocorrencia assinatura | `estudante`, `responsavel`, `ambos`. | `database.py`: `QUEM_ASSINA_OCORRENCIA_VALIDOS`; `services/ocorrencia_pdf_service.py`. | Confirmada pelo codigo. |
| Ocorrencia acao aplicada | `advertencia_verbal`, `retirada_sala_orientacao`, `suspensao_extracurricular`, `suspensao_orientada_2_dias`, `suspensao_aulas_3_dias`, `transferencia_compulsoria`, `orientacao_verbal`, `advertencia`, `chamada_responsavel`, `encaminhamento_direcao`, `registro_informativo`, `orientacao_professor`, `reuniao_alinhamento`, `orientacao_geral_docentes`. | `services/ocorrencia_disciplina_service.py`: `ACAO_OCORRENCIA_VALIDAS`; `database.py`: CHECK de `ocorrencias.acao_aplicada`. | Confirmada pelo codigo. |
| Base legal | `artigo`, `inciso`, `alinea`. | `database.py`: `TIPO_BASE_LEGAL_ARTIGO`, `TIPO_BASE_LEGAL_INCISO`, `TIPO_BASE_LEGAL_ALINEA`. | Confirmada pelo codigo. |
| Grade escolar | `AULA`, `INTERVALO`. | `database.py`: `TIPOS_CONFIGURACAO_GRADE`; `modules/scheduling/lesson_config.py`. | Confirmada pelo codigo. |
| APC tipo de entrega | `GERAL`, `APC`, `PROVA_BIMESTRAL`. | `services/apc_service.py`: `APC_TIPO_ENTREGA_*`. | Confirmada pelo codigo. |
| APC revisao | `PENDENTE`, `APROVADO`, `IMPRESSO`, `AJUSTE_SOLICITADO`. | `modules/apc_review/models.py`: `ApcReviewStatus`; `modules/apc_review/schemas.py`; migration `20260615_add_apc_submission_review.py`. | Confirmada pelo codigo. |
| APC preview job | `PENDENTE`, `CONCLUIDO`, `ERRO`. | `migrations/20260622_create_apc_preview_jobs.py`; `database.py`: funcoes de fila/preview APC. | Inferida: tabela define `PENDENTE`; funcoes atualizam para `CONCLUIDO`/filtram `ERRO`. |
| Pre-registro de ocorrencia | `pending`, `completed`, `cancelled`. | `migrations/20260611_create_occurrence_pre_registrations.py`: CHECK de `status`. | Confirmada pelo codigo. |
| Contato com responsavel em pre-registro | `none`, `communicate`, `summon`. | `migrations/20260611_create_occurrence_pre_registrations.py`: CHECK; `modules/occurrences/schemas.py`: `ResponsibleContact`. | Confirmada pelo codigo. |
| Auditoria categoria | `auth`, `password`, `printing`, `scheduling`, `attachments`. | `modules/audit/models.py`: `AuditCategory`. | Confirmada pelo codigo. |
| Auditoria resultado | `success`, `failure`. | `modules/audit/models.py`: `AuditOutcome`. | Confirmada pelo codigo. |
| Download de videos | `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `ERRO`. | `services/youtube_download_jobs.py`: `STATUS_DOWNLOAD_*`. | Confirmada pelo codigo. |

## Pontos Pendentes

- Confirmar se todos os status de `jobs` devem ser formalizados em enum unico ou se alguns sao apenas legados. **Pendente de validacao**.
- Confirmar se `FINALIZADO` deve continuar como status legado aceito para reuso historico. **Inferida** por `modules/printing/policies.py`: `print_job_can_be_reused`.
- Confirmar transicoes permitidas para APC review alem dos valores existentes. **Pendente de validacao**.
