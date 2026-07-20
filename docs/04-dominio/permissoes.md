# Permissoes

Status: mapa inicial extraido do backend e frontend.

## Convencoes

- **Confirmada pelo codigo**: permissao verificada por funcao backend, dependency, service, router ou JS lido.
- **Inferida**: deduzida por combinacao de matriz de modulos, rotas e comportamento.
- **Pendente de validacao**: precisa de confirmacao funcional.

## Fonte Central De Permissoes

| Elemento | Papel | Evidencia | Classificacao |
| --- | --- | --- | --- |
| `normalizar_cargo_usuario` | Normaliza `cargo` e fallback por `perfil`. | `routers/common.py`: `normalizar_cargo_usuario`. | Confirmada pelo codigo |
| `MODULOS_POR_CARGO` | Define modulos visiveis por cargo no backend. | `routers/common.py`: `MODULOS_POR_CARGO`. | Confirmada pelo codigo |
| `modulos_por_usuario` | Acrescenta modulos de coordenador para professor com `acesso_coordenacao`. | `routers/common.py`: `modulos_por_usuario`. | Confirmada pelo codigo |
| `/me` | Retorna cargo, modulos e flags calculadas ao frontend. | `routers/system_router.py`: `eu`. | Confirmada pelo codigo |
| `exigir_admin` | Bloqueia acesso que exige admin. | `routers/common.py`: `exigir_admin`. | Confirmada pelo codigo |
| `exigir_gestor` | Bloqueia acesso que exige admin ou coordenador. | `routers/common.py`: `exigir_gestor`. | Confirmada pelo codigo |
| `usuario_tem_acesso_coordenacao` | Autoriza admin, coordenador ou professor com flag. | `routers/common.py`: `usuario_tem_acesso_coordenacao`. | Confirmada pelo codigo |
| `usuario_pode_gerir_impressoes` | Autoriza gestor ou professor com acesso de coordenacao a gerir impressao. | `routers/common.py`: `usuario_pode_gerir_impressoes`. | Confirmada pelo codigo |
| `resolver_usuario_professor_selecionado` | Controla quando um usuario pode operar em nome de outro professor. | `routers/common.py`: `resolver_usuario_professor_selecionado`. | Confirmada pelo codigo |

## Matriz De Modulos Por Cargo

| Cargo | Modulos backend | Evidencia | Classificacao |
| --- | --- | --- | --- |
| `ADMIN` | `impressao`, `agendamento`, `download`, `gestao`, `relatorios`, `coordenacao`, `horario`, `apc`, `pcpi`, `preconselho`. | `routers/common.py`: `MODULOS_POR_CARGO`. | Confirmada pelo codigo |
| `PROFESSOR` | `impressao`, `agendamento`, `download`, `coordenacao`, `horario`, `apc`, `preconselho`. | `routers/common.py`: `MODULOS_POR_CARGO`. | Confirmada pelo codigo |
| `COORDENADOR` | `impressao`, `download`, `relatorios`, `coordenacao`, `horario`, `apc`, `pcpi`, `preconselho`. | `routers/common.py`: `MODULOS_POR_CARGO`. | Confirmada pelo codigo |
| `PROFESSOR + acesso_coordenacao` | Modulos de professor + modulos de coordenador que ainda nao existirem. | `routers/common.py`: `modulos_por_usuario`. | Confirmada pelo codigo |

## Permissoes Verificadas No Backend

| Area | Acesso/acao | Quem pode | Onde e verificado | Classificacao |
| --- | --- | --- | --- | --- |
| Autenticacao | Acessar APIs protegidas | Usuario com token Bearer valido. | `auth.py`: `get_usuario_logado`; uso de `Depends(get_usuario_logado)` nos routers. | Confirmada pelo codigo |
| Relatorios | Consultar dashboard/anexos | Admin, coordenador ou professor com `acesso_coordenacao`. | `routers/relatorios_router.py`: `_exigir_acesso_relatorios`; `routers/common.py`: `usuario_tem_acesso_coordenacao`. | Confirmada pelo codigo |
| Auditoria | Consultar eventos de auditoria | Admin. | `modules/audit/router.py`: `get_audit_events`, `exigir_admin`. | Confirmada pelo codigo |
| Impressao | Imprimir arquivo | Usuario autenticado; se informar `professor_id`, precisa permissao para selecionar professor. | `modules/printing/router.py`: `imprimir`; `routers/common.py`: `resolver_usuario_professor_selecionado`. | Confirmada pelo codigo |
| Impressao | Ver fila e alterar prioridade | Gestor: admin ou coordenador. | `modules/printing/router.py`: `fila`, `prioridade`; `modules/printing/dependencies.py`: `require_print_manager`. | Confirmada pelo codigo |
| Impressao | Acessar preview/reimprimir/cancelar job | Dono do job ou gestor de impressao. | `modules/printing/job_access.py`: `get_job_with_access`, `cancel_print_job`; `modules/printing/router.py`. | Confirmada pelo codigo |
| Impressao | Cota ilimitada | Admin/coordenador. | `routers/common.py`: `usuario_tem_cota_ilimitada`; `modules/printing/job_creation.py`. | Confirmada pelo codigo |
| Agendamento | Listar recursos/opcoes/reservas | Usuario autenticado. | `modules/scheduling/router.py`: endpoints com `Depends(get_usuario_logado)`. | Confirmada pelo codigo |
| Agendamento | Listar professores para selecao | Admin, coordenador ou professor com `acesso_coordenacao`; caso contrario exige admin. | `modules/scheduling/router.py`: `professores_agendamento`; `modules/scheduling/dependencies.py`: `user_can_manage_scheduling`, `require_admin_for_scheduling`. | Confirmada pelo codigo |
| Agendamento | Criar reserva para outro professor | Admin ou professor com acesso de coordenacao quando permitido pelo resolver. | `modules/scheduling/router.py`: `criar_reserva_agendamento`; `routers/common.py`: `resolver_usuario_professor_selecionado`. | Confirmada pelo codigo |
| Agendamento | Cancelar reserva | Dono da reserva ou admin. | `modules/scheduling/service.py`: `ensure_reservation_can_be_cancelled`; `modules/scheduling/router.py`: `cancelar_reserva_agendamento`. | Confirmada pelo codigo |
| Administracao | Ver fila/status/historico/relatorios admin, turmas, disciplinas, configuracao de aulas, recursos | Gestor: admin ou coordenador. | `routers/admin_router.py`: endpoints com `exigir_gestor`. | Confirmada pelo codigo |
| Administracao | Gerir turmas-disciplinas, atribuicoes docentes, professores, coordenadores, cotas, auditoria | Admin. | `routers/admin_router.py`: endpoints com `exigir_admin`; `modules/audit/router.py`. | Confirmada pelo codigo |
| APC | Gestao de periodos, destinatarios, revisao e impressao de anexos | Admin, coordenador ou professor com `acesso_coordenacao`. | `routers/apc_router.py`: `_pode_gerir_apc`, `_exigir_gestao_apc`. | Confirmada pelo codigo |
| APC | Enviar anexo | Professor, dentro das regras de elegibilidade/prazo. | `routers/apc_router.py`: `enviar_arquivo_apc_api`; `usuario_eh_professor`. | Confirmada pelo codigo |
| APC | Baixar/visualizar anexo | Gestao APC ou professor dono do envio. | `routers/apc_router.py`: `baixar_arquivo_apc_api`, `visualizar_arquivo_apc_api`. | Confirmada pelo codigo |
| APC | Excluir envio | Professor dono do envio, dentro do prazo. | `routers/apc_router.py`: `excluir_envio_apc_api`. | Confirmada pelo codigo |
| Horario escolar | Visualizar horario | Gestor ou professor. | `routers/horario_escolar_router.py`: `_exigir_visualizacao_horario`. | Confirmada pelo codigo |
| Horario escolar | Gerir horario | Gestor. | `routers/horario_escolar_router.py`: endpoints com `exigir_gestor`. | Confirmada pelo codigo |
| Ocorrencias/pre-registros | Acessar contexto/listagens | Professor ou gestor. | `modules/occurrences/service.py`: `require_occurrences_access`. | Confirmada pelo codigo |
| Ocorrencias/pre-registros | Criar/editar motivos e concluir pre-registros | Gestor. | `modules/occurrences/service.py`: `require_manager`, `complete_pre_registration`. | Confirmada pelo codigo |
| Ocorrencias/pre-registros | Criar pre-registro | Professor. | `modules/occurrences/service.py`: `create_pre_registration`. | Confirmada pelo codigo |
| Pre-conselho | Acessar modulo | Admin, coordenador ou professor. | `modules/preconselho/service.py`: `require_preconselho_access`. | Confirmada pelo codigo |
| Pre-conselho | Administrar periodos/configuracoes sensiveis | Admin ou acesso de gestao conforme endpoint/service. | `modules/preconselho/service.py`: `require_admin_access`, `has_manager_access`, `resolve_teacher`. | Confirmada pelo codigo |
| Download de videos | Consultar/criar/baixar jobs | Usuario autenticado. | `routers/download_router.py`: endpoints com `Depends(get_usuario_logado)`. | Confirmada pelo codigo |
| Radius interno | Garantir NT hash | Chamador com segredo interno. | `routers/system_router.py`: `internal_radius_ensure_nt_hash`; header `X-RADIUS-SECRET`. | Confirmada pelo codigo |

## Permissoes Presentes No Frontend

| Arquivo | Controle visual/comportamental | Backend correspondente | Risco |
| --- | --- | --- | --- |
| `static/js/servicos.js` | Oculta cards de modulos conforme `/me.modulos` ou fallback por cargo. | APIs dos modulos usam `Depends(get_usuario_logado)` e/ou checks especificos. | Baixo para acesso a dados quando API protege; medio para UX porque fallback pode divergir do backend. |
| `static/js/core/auth.js` | Calcula cargo, acesso de coordenacao, modulos permitidos e permissao de gerir impressoes no cliente. | `/me` retorna flags calculadas no backend; routers revalidam operacoes criticas. | Medio: fallback frontend nao deve ser usado como fonte de verdade. |
| `static/js/professor.js` | Mostra/esconde selecao de professor para impressao e bloqueia etapas quando pendente. | `modules/printing/router.py` revalida `professor_id` via `resolve_print_teacher`. | Baixo. |
| `static/js/relatorios.js` | Decide visualmente se usuario pode acessar relatorios. | `routers/relatorios_router.py` bloqueia com `_exigir_acesso_relatorios`. | Baixo. |
| `static/js/preconselho/*` | Mostra botoes/admin/visoes conforme usuario/contexto. | `modules/preconselho/service.py` valida acesso e escopo. | Baixo, pendente revisar todos os endpoints do modulo. |
| `static/js/horario_escolar.js` | Alterna interface gestor/professor e evita filtros de professor na interface docente. | `routers/horario_escolar_router.py` valida visualizacao/gestao no backend. | Baixo. |
| `routers/pages_router.py` + templates | Páginas HTML sao servidas sem autenticação backend. | JS chama `garantirToken()`/APIs protegidas; dados sensiveis vêm das APIs. | Medio: pagina pode abrir sem token, embora dados/acoes sejam protegidos pelas APIs. |

## Restricoes E Acoes Administrativas

| Acao | Restricao | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Alterar status operacional de impressao | Admin. | `routers/admin_router.py`: `atualizar_status_impressao_admin`, `exigir_admin`. | Confirmada pelo codigo |
| Consultar fila/status/historico admin | Gestor. | `routers/admin_router.py`: `fila_admin`, `obter_status_impressao_admin`, `historico_admin`, `exigir_gestor`. | Confirmada pelo codigo |
| Criar/editar turmas e disciplinas | Gestor. | `routers/admin_router.py`: endpoints `/admin/turmas`, `/admin/disciplinas`, `exigir_gestor`. | Confirmada pelo codigo |
| Gerir atribuicoes docentes/turmas-disciplinas | Admin. | `routers/admin_router.py`: endpoints com `exigir_admin`. | Confirmada pelo codigo |
| Criar/editar/excluir professores e coordenadores | Admin. | `routers/admin_router.py`: endpoints `/admin/professores`, `/admin/coordenadores`, `exigir_admin`. | Confirmada pelo codigo |
| Promover professor a coordenador | Admin. | `routers/admin_router.py`: `/admin/professores/{professor_id}/promover-coordenador`, `exigir_admin`. | Confirmada pelo codigo |
| Alterar regras/recalcular cotas | Admin. | `routers/admin_router.py`: `/admin/cotas/regras`, `/admin/cotas/recalcular`, `exigir_admin`. | Confirmada pelo codigo |
| Gerir recursos | Gestor. | `routers/admin_router.py`: `/admin/recursos`, `exigir_gestor`. | Confirmada pelo codigo |
| Consultar auditoria | Admin. | `modules/audit/router.py`: `exigir_admin`. | Confirmada pelo codigo |

## Riscos Identificados

| Risco | Impacto | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Paginas renderizadas sem autenticação no backend. | Um usuario sem token pode abrir HTML, mas nao deveria obter dados nem executar acoes se as APIs estiverem protegidas. | `routers/pages_router.py` nao usa `Depends(get_usuario_logado)`; JS usa `garantirToken`; APIs usam `Depends`. | Confirmada pelo codigo |
| Divergencia entre matriz frontend e backend. | Cards/modulos podem aparecer/desaparecer de forma inconsistente. | `routers/common.py`: `MODULOS_POR_CARGO` inclui `download`; `static/js/core/auth.js`: fallback nao inclui `download` para alguns cargos. | Pendente de validacao |
| Permissao de modulo no frontend nao e controle de seguranca. | Se algum endpoint novo for criado sem check backend, o frontend nao protege contra chamada direta. | Presenca de `modulosPermitidos` em `static/js/servicos.js` e `static/js/core/auth.js`. | Inferida |
| Listagem de reservas de agendamento e recursos exige autenticacao, mas nao limita por professor. | Todos os usuarios autenticados podem listar reservas no periodo/recurso; pode ser intencional para visao compartilhada da agenda. | `modules/scheduling/router.py`: `listar_reservas_agendamento` usa apenas `Depends(get_usuario_logado)`. | Pendente de validacao |
| Download de videos permite usuario autenticado comum. | Pode ser aceitavel ou precisar de restricao por perfil devido a consumo de recursos. | `routers/download_router.py`: endpoints usam `Depends(get_usuario_logado)` sem cargo. | Pendente de validacao |

## Conclusao

As permissoes criticas analisadas estao majoritariamente verificadas no backend. Os controles de frontend funcionam como UX/visibilidade, nao como barreira de seguranca. O principal cuidado para evolucao e manter qualquer nova acao sensivel protegida por `exigir_admin`, `exigir_gestor`, `usuario_tem_acesso_coordenacao`, `usuario_pode_gerir_impressoes` ou validacao de escopo equivalente no service.
