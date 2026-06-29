# Usuarios E Perfis

Status: mapa inicial extraido do codigo.

## Convencoes

- **Confirmada pelo codigo**: evidenciada por funcao, router, service, schema, template ou teste.
- **Inferida**: deduzida pelo uso combinado de campos/perfis.
- **Pendente de validacao**: precisa de confirmacao de produto/operacao.

## Tipos De Usuario

| Tipo | Finalidade aparente | Identificacao no sistema | Evidencia | Classificacao |
| --- | --- | --- | --- | --- |
| Professor | Usuario docente que usa impressao, agendamento, download, APC e pre-conselho; pode criar pre-registros de ocorrencia. | `cargo = PROFESSOR` ou perfil legado diferente de admin/coordenador. | `routers/common.py`: `CARGO_PROFESSOR`, `usuario_eh_professor`, `MODULOS_POR_CARGO`; `modules/occurrences/service.py`: `create_pre_registration`. | Confirmada pelo codigo |
| Coordenador | Usuario gestor pedagógico, com acesso a relatorios, coordenacao, APC, PCPI, horario, pre-conselho e impressao. | `cargo = COORDENADOR` ou `perfil = coordenador`. | `routers/common.py`: `CARGO_COORDENADOR`, `usuario_eh_gestor`, `MODULOS_POR_CARGO`. | Confirmada pelo codigo |
| Administrador | Usuario com acesso administrativo ampliado: usuarios, cotas, atribuicoes, auditoria e configuracoes sensiveis. | `cargo = ADMIN` ou `perfil = admin`. | `routers/common.py`: `CARGO_ADMIN`, `usuario_eh_admin`, `exigir_admin`; `routers/admin_router.py`; `modules/audit/router.py`. | Confirmada pelo codigo |
| Professor com acesso de coordenacao | Professor que preserva visao docente, mas ganha permissões de coordenacao/gestao em alguns fluxos. | `cargo = PROFESSOR` e `acesso_coordenacao = 1`. | `routers/common.py`: `usuario_tem_acesso_coordenacao`, `modulos_por_usuario`, `usuario_pode_gerir_impressoes`; `tests/test_apc_router.py`: professor com coordenacao alterna visoes. | Confirmada pelo codigo |
| Servico interno Radius | Ator tecnico sem login de usuario comum para endpoint interno de hash NT. | Header `X-RADIUS-SECRET`. | `routers/system_router.py`: `internal_radius_ensure_nt_hash`; `.env.example`: `RADIUS_INTERNAL_SECRET`. | Confirmada pelo codigo |

## Perfis, Cargos E Normalizacao

| Campo | Uso | Regra | Evidencia | Classificacao |
| --- | --- | --- | --- | --- |
| `cargo` | Fonte principal de permissao. | Valores reconhecidos: `ADMIN`, `COORDENADOR`, `PROFESSOR`. | `routers/common.py`: constantes `CARGO_*`, `normalizar_cargo_usuario`. | Confirmada pelo codigo |
| `perfil` | Compatibilidade/legado. | Se `cargo` nao for reconhecido, `perfil=admin` vira `ADMIN`, `perfil=coordenador` vira `COORDENADOR`; demais caem em `PROFESSOR`. | `routers/common.py`: `normalizar_cargo_usuario`; `auth.py`: `normalizar_cargo`. | Confirmada pelo codigo |
| `acesso_coordenacao` | Flag especial para professor com acesso ampliado. | Professor com flag ativa recebe modulos de coordenador e pode gerir impressões. | `routers/common.py`: `usuario_tem_acesso_coordenacao`, `modulos_por_usuario`, `usuario_pode_gerir_impressoes`. | Confirmada pelo codigo |
| `ativo` | Exclusao logica de usuario. | Usuario pode ser mantido no banco como inativo. | `database.py`: tabela `usuarios` e `_clausula_usuario_ativo`; `tests/test_professor_exclusao.py`. | Confirmada pelo codigo |

## Diferencas Entre Professor, Coordenador E Administrador

| Capacidade | Professor | Coordenador | Administrador | Evidencia |
| --- | --- | --- | --- | --- |
| Ver servicos basicos | Sim: impressao, agendamento, download, coordenacao, horario, APC, pre-conselho. | Sim, exceto agendamento na matriz central atual. | Sim, todos os modulos centrais. | `routers/common.py`: `MODULOS_POR_CARGO`. |
| Cota de impressao | Tem cota normal. | Cota ilimitada. | Cota ilimitada. | `routers/common.py`: `usuario_tem_cota_ilimitada`; `services/cota_service.py`. |
| Gerir fila/prioridade de impressao | Nao, salvo professor com `acesso_coordenacao`. | Sim. | Sim. | `routers/common.py`: `usuario_pode_gerir_impressoes`; `modules/printing/router.py`: `fila`, `prioridade`. |
| Selecionar outro professor em impressao/agendamento | Nao, salvo professor com `acesso_coordenacao` nos fluxos que permitem. | Parcial: depende de resolver comum e contexto. | Sim. | `routers/common.py`: `resolver_usuario_professor_selecionado`; `modules/printing/router.py`; `modules/scheduling/router.py`. |
| Administrar usuarios/atribuicoes/cotas | Nao. | Nao para rotas marcadas como admin. | Sim. | `routers/admin_router.py`: endpoints com `exigir_admin`. |
| Gerir recursos/turmas/disciplinas basicas | Nao. | Sim em parte. | Sim. | `routers/admin_router.py`: endpoints com `exigir_gestor`. |
| Auditoria administrativa | Nao. | Nao. | Sim. | `modules/audit/router.py`: `exigir_admin`. |
| Relatorios | Apenas se tiver `acesso_coordenacao`. | Sim. | Sim. | `routers/relatorios_router.py`: `_exigir_acesso_relatorios`. |
| APC gestao | Apenas se tiver `acesso_coordenacao`. | Sim. | Sim. | `routers/apc_router.py`: `_pode_gerir_apc`, `_exigir_gestao_apc`. |
| Pre-conselho docente | Sim, restrito a escopo do professor. | Visao de gestao. | Visao admin/gestao. | `modules/preconselho/service.py`: `resolve_teacher`, `validate_teacher_scope`, `has_manager_access`. |

## Observacoes

- A matriz de `routers/common.py` concede `coordenacao` para professores em geral, mas os endpoints de coordenacao/ocorrencias ainda aplicam regras de service/gestor/professor conforme o caso. **Confirmada pelo codigo**.
- A pagina HTML de cada modulo pode ser aberta sem autenticacao no backend, mas as chamadas de API usam token e as telas usam JS para redirecionar/ocultar. **Confirmada pelo codigo**: `routers/pages_router.py`; `static/js/core/auth.js`.
- Existe diferenca entre a matriz de modulos do backend e a fallback matrix em `static/js/core/auth.js`: o fallback frontend nao inclui `download` para alguns perfis onde `routers/common.py` inclui. **Pendente de validacao**.
