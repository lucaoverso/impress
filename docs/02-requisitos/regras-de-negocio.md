# Regras De Negocio

Status: catalogo inicial extraido do comportamento atual.

## Convencoes

- `RN-AUT-*`: autenticacao e identidade.
- `RN-IMP-*`: impressao.
- `RN-AGE-*`: agendamento.
- `RN-ANE-*`: anexos/APC.

Classificacao da evidencia:

- `Confirmada pelo codigo`: regra implementada diretamente.
- `Confirmada por teste`: regra implementada e coberta por teste automatizado.
- `Pendente de validacao`: regra precisa de confirmacao ou leitura complementar.

## Autenticacao

| ID | Descricao | Condicao | Resultado esperado | Excecoes | Arquivo e funcao | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RN-AUT-001 | Login so deve ser concedido para email/senha validos. | Usuario envia credenciais em `/login`. | Sistema retorna token, perfil, cargo e expiracao. | Credenciais invalidas geram `401`. | `auth.py`: `login`; `services/auth_service.py`: `autenticar_usuario` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AUT-002 | Tentativas de login devem ser auditadas. | Login falha ou tem sucesso. | Sistema registra evento `login.attempt` ou `login.success`. | Falha de auditoria nao foi analisada. | `auth.py`: `login` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AUT-003 | Rotas protegidas exigem token Bearer valido. | Endpoint usa `Depends(get_usuario_logado)`. | Usuario autenticado e retornado para a rota. | Header ausente/invalido ou token invalido geram `401`. | `auth.py`: `get_usuario_logado`; `services/auth_service.py`: `validar_token` | `tests/test_scheduling_router.py`: usa header `Authorization: Bearer` | Confirmada pelo codigo |

## Impressao

| ID | Descricao | Condicao | Resultado esperado | Excecoes | Arquivo e funcao | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RN-IMP-001 | Impressao deve ser bloqueada quando o status operacional indicar falta de papel/indisponibilidade. | Usuario tenta imprimir ou reimprimir. | Sistema impede criacao de job com `409` e mensagem operacional. | Nenhuma excecao de negocio identificada. | `modules/printing/policies.py`: `ensure_print_is_available`; `modules/printing/router.py`: `imprimir`, `reimprimir_job_historico` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-IMP-002 | Toda impressao deve ter ao menos uma tag de identificacao. | Job novo ou reimpressao e criado. | Sistema aceita apenas tags do catalogo e exige lista nao vazia. | Tags invalidas geram `400`; lista vazia gera `400`. | `modules/printing/policies.py`: `normalize_print_tags`, `validate_required_tags`; `modules/printing/job_creation.py`: `create_job_from_ready_pdf` | `tests/test_impressao_reuso_historico.py`: verifica preservacao de tags no historico | Confirmada pelo codigo |
| RN-IMP-003 | Usuarios sem cota ilimitada so podem imprimir se houver cota suficiente. | Criacao de job calcula paginas consumidas. | Sistema consome cota e cria job. | Cota insuficiente gera `403`; falha de cota gera erro controlado. | `modules/printing/job_creation.py`: `create_job_from_ready_pdf`; `services/cota_service.py`: `validar_e_consumir_cota` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-IMP-004 | Gestores/professores com permissao podem imprimir em nome de professor selecionado. | `professor_id` e informado em impressao/reimpressao/cota/historico. | Sistema resolve professor responsavel/consulta conforme permissao. | Usuario sem permissao recebe erro de autorizacao. | `modules/printing/router.py`: `imprimir`, `reimprimir_job_historico`, `meus_jobs`, `minha_cota`; `modules/printing/dependencies.py`: `resolve_print_teacher` | `tests/test_impressao_reuso_historico.py`: `test_professor_com_acesso_coordenacao_pode_consultar_job_de_outro_professor` | Confirmada por teste |
| RN-IMP-005 | Usuario so pode acessar job proprio, salvo gestor autorizado. | Preview, reimpressao ou cancelamento recebe `job_id`. | Dono ou gestor acessa o job. | Terceiro sem permissao recebe `403`; job inexistente recebe `404`. | `modules/printing/job_access.py`: `get_job_with_access` | `tests/test_impressao_reuso_historico.py`: `test_professor_com_acesso_coordenacao_pode_consultar_job_de_outro_professor` | Confirmada por teste |
| RN-IMP-006 | Apenas jobs concluidos/finalizados podem ser reutilizados. | Usuario tenta preview/reimpressao de historico. | Sistema permite reutilizacao se status for `CONCLUIDO` ou `FINALIZADO`. | Outros status geram `409` ou motivo de indisponibilidade. | `modules/printing/policies.py`: `print_job_can_be_reused`, `serialize_print_job`; `modules/printing/job_creation.py`: `reprint_job_from_history`; `modules/printing/job_access.py`: `read_reusable_job_pdf_content` | `tests/test_impressao_reuso_historico.py`: `test_reimprimir_job_historico_cria_novo_job_com_copia_no_spool`, `test_meus_jobs_informa_quando_arquivo_do_historico_foi_removido` | Confirmada por teste |
| RN-IMP-007 | Cancelamento de job deve respeitar estado atual da fila. | Usuario solicita cancelamento. | Sistema cancela e informa paginas estornadas/restantes quando aplicavel. | Job ja em impressao/finalizado nao pode ser cancelado e gera `409`. | `modules/printing/job_access.py`: `cancel_print_job`; `modules/printing/repository.py`: `cancel_job` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-IMP-008 | Gestores podem ver fila e alterar prioridade; usuarios comuns nao. | Usuario consulta `/fila` ou altera prioridade. | Gestor recebe dados/atualizacao. | Usuario sem permissao recebe erro de acesso. | `modules/printing/router.py`: `fila`, `prioridade`; `modules/printing/dependencies.py`: `require_print_manager` | Pendente de mapeamento | Confirmada pelo codigo |

## Agendamento

| ID | Descricao | Condicao | Resultado esperado | Excecoes | Arquivo e funcao | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RN-AGE-001 | So recursos ativos podem ser reservados. | Usuario cria reserva com `recurso_id`. | Sistema aceita recurso ativo. | Recurso inexistente/inativo gera `404`. | `modules/scheduling/service.py`: `ensure_resource_is_active`, `create_scheduling_reservation` | `tests/test_scheduling_service.py`: `test_ensure_resource_is_active_rejects_inactive_resource` | Confirmada por teste |
| RN-AGE-002 | Turma da reserva precisa estar ativa e possuir turno configurado. | Usuario cria reserva com `turma`. | Sistema identifica turma e turno. | Turma invalida gera `400`; turno nao configurado gera `400`. | `modules/scheduling/policies.py`: `validar_turma`; `modules/scheduling/service.py`: `ensure_class_shift_is_configured` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AGE-003 | Tema da aula e obrigatorio para criar reserva. | Usuario cria reserva. | Sistema grava reserva com tema informado. | Tema vazio gera `400`. | `modules/scheduling/policies.py`: `validar_tema_aula`; `modules/scheduling/service.py`: `build_reservation_creation_payload` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AGE-004 | Aula deve pertencer a janela permitida da turma. | Usuario cria reserva com aula/turma. | Sistema aceita somente aulas configuradas para a turma. | Turma sem janela ou aula fora da janela gera `400`; ausencia de grade global gera `409`. | `modules/scheduling/policies.py`: `validar_aula`; `modules/scheduling/service.py`: `ensure_class_lesson_window_is_configured`; `modules/scheduling/lesson_config.py`: `list_lessons_for_class` | `tests/test_scheduling_service.py`: `test_integral_skips_global_slot_six_and_starts_afternoon_at_seven` | Confirmada por teste |
| RN-AGE-005 | Capacidade do recurso limita reservas simultaneas na mesma data/faixa global. | Ja existem reservas ativas para recurso/data/faixa. | Sistema cria reserva se ainda houver capacidade. | Capacidade atingida gera `409`. | `modules/scheduling/service.py`: `ensure_slot_has_capacity`, `create_scheduling_reservation`; `modules/scheduling/repository.py`: `count_active_reservations_in_slot` | `tests/test_scheduling_service.py`: `test_ensure_slot_has_capacity_rejects_full_slot` | Confirmada por teste |
| RN-AGE-006 | Reserva pode ser criada em nome do usuario logado ou professor selecionado conforme permissao. | `professor_id` pode ser informado. | Sistema define `usuario_id` da reserva. | Selecionar professor sem permissao gera erro; professor inexistente/invalido gera erro. | `modules/scheduling/service.py`: `build_reservation_creation_payload`; `modules/scheduling/dependencies.py`: `resolve_scheduling_teacher`; `routers/common.py`: `resolver_usuario_professor_selecionado` | `tests/test_scheduling_service.py`: `test_create_scheduling_reservation_calls_repository_functions` | Confirmada por teste |
| RN-AGE-007 | Criacao de reserva deve ser auditada. | Criacao tem sucesso ou falha com `HTTPException`. | Sistema registra `reservation.create` com sucesso ou falha. | Falhas nao HTTP nao foram mapeadas. | `modules/scheduling/router.py`: `criar_reserva_agendamento` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AGE-008 | Cancelamento so e permitido para reserva ativa. | Usuario solicita cancelamento. | Reserva ativa segue para validacao de data/permissao. | Reserva cancelada gera `400`; inexistente gera `404`. | `modules/scheduling/service.py`: `ensure_reservation_can_be_cancelled` | `tests/test_scheduling_router.py`: `test_agendamento_create_and_cancel_reservation` | Confirmada por teste |
| RN-AGE-009 | Nao e permitido cancelar agendamento de data passada. | Reserva ativa tem data anterior ao dia atual. | Sistema bloqueia cancelamento. | Data invalida gera `400`; data passada gera `409`. | `modules/scheduling/service.py`: `ensure_reservation_can_be_cancelled` | Pendente de mapeamento | Confirmada pelo codigo |
| RN-AGE-010 | Apenas dono da reserva ou admin pode cancelar. | Usuario tenta cancelar reserva. | Dono ou admin cancela. | Nao dono sem admin recebe `403`. | `modules/scheduling/service.py`: `ensure_reservation_can_be_cancelled`; `modules/scheduling/router.py`: `cancelar_reserva_agendamento` | `tests/test_scheduling_service.py`: `test_cancel_scheduling_reservation_rejects_non_owner` | Confirmada por teste |

## Anexos / APC

| ID | Descricao | Condicao | Resultado esperado | Excecoes | Arquivo e funcao | Teste relacionado | Classificacao |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RN-ANE-001 | Apenas professores podem enviar anexo APC. | Usuario envia arquivo para periodo APC. | Professor segue para validacoes do periodo/entrega. | Usuario nao professor recebe `403`. | `routers/apc_router.py`: `enviar_arquivo_apc_api`; `routers/common.py`: `usuario_eh_professor` | `tests/test_apc_router.py` | Confirmada por teste |
| RN-ANE-002 | Anexo APC so pode ser enviado enquanto o prazo estiver aberto. | Professor tenta enviar arquivo para periodo. | Sistema aceita envio dentro do prazo. | Prazo encerrado gera `409`. | `routers/apc_router.py`: `enviar_arquivo_apc_api`; `services/apc_service.py`: `periodo_apc_aberto` | `tests/test_apc_router.py` | Confirmada por teste |
| RN-ANE-003 | Professor so pode enviar quando ha entrega prevista para ele e para a disciplina/turma selecionada. | Professor envia arquivo APC. | Sistema registra envio para item elegivel. | Sem entrega prevista gera `403`. | `routers/apc_router.py`: `enviar_arquivo_apc_api`, `_selecionar_item_professor_periodo`, `_obter_elegiveis_periodo` | `tests/test_apc_router.py` | Confirmada por teste |
| RN-ANE-004 | Reenvio substitui envio existente e remove arquivo anterior quando aplicavel. | Professor envia novo arquivo para item ja enviado. | Sistema atualiza envio e remove arquivo antigo. | Conflito de banco remove novo arquivo e gera `409`. | `routers/apc_router.py`: `enviar_arquivo_apc_api` | `tests/test_apc_router.py`: `test_professor_remove_envio_e_reenvia_arquivo_dentro_do_prazo` | Confirmada por teste |
| RN-ANE-005 | Apenas professor responsavel pode remover anexo enquanto prazo estiver aberto. | Usuario solicita exclusao de envio. | Professor dono remove envio e arquivo. | Nao dono/nao professor gera `403`; prazo encerrado gera `409`. | `routers/apc_router.py`: `excluir_envio_apc_api` | `tests/test_apc_router.py` | Confirmada por teste |
| RN-ANE-006 | Acesso a baixar/visualizar anexo e restrito a gestao APC ou professor dono. | Usuario solicita arquivo/preview. | Usuario autorizado recebe arquivo ou PDF. | Usuario sem acesso recebe `403`; envio inexistente `404`. | `routers/apc_router.py`: `baixar_arquivo_apc_api`, `visualizar_arquivo_apc_api`, `_pode_gerir_apc` | `tests/test_apc_router.py` | Confirmada por teste |
| RN-ANE-007 | Impressao de anexo APC e restrita a gestao APC. | Usuario solicita impressao de envio. | Gestao prepara PDF e usa fluxo de impressao. | Usuario sem gestao recebe `403`. | `routers/apc_router.py`: `imprimir_arquivo_apc_api`, `_exigir_gestao_apc`; `modules/printing/attachment_printing.py`: `imprimir_anexo_pdf` | `tests/test_apc_router.py`: `test_coordenador_imprime_anexo_usando_fluxo_de_impressao`, `test_professor_nao_pode_imprimir_anexo_pela_gestao` | Confirmada por teste |

## Proximos Modulos A Extrair

- `usuarios`
- `ocorrencias`
- `preconselho`
- `auditoria`
- `relatorios`
- `horario-escolar`
- `download`

