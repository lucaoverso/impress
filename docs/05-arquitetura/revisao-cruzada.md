# Revisao cruzada da documentacao

Este documento revisa a documentacao produzida contra os proprios documentos e contra o mapa de codigo levantado ate aqui. O objetivo e identificar lacunas e inconsistencias antes que a documentacao passe a orientar decisoes de refatoracao.

## Criterios

| Severidade | Criterio |
| --- | --- |
| Critica | Pode induzir decisao tecnica errada, esconder risco de seguranca ou afetar planejamento de refatoracao. |
| Alta | Lacuna importante para modulo relevante ou comportamento sensivel. |
| Media | Inconsistencia ou ausencia que dificulta consulta, mas nao bloqueia decisao imediata. |
| Baixa | Ajuste editorial/organizacional. |

## Resumo executivo

| Tema | Situacao |
| --- | --- |
| Funcionalidades sem documentacao | Existem modulos reconhecidos em `docs/01-visao-geral/modulos.md`, mas ainda com documentos proprios vazios ou pendentes em `docs/03-modulos/` e `docs/06-fluxos/`. |
| Regras contraditorias | A principal contradicao funcional identificada envolve permissao de coordenador no agendamento: pode listar professores, mas a criacao em nome de outro professor aparenta exigir admin. |
| Regras duplicadas | Permissoes, modulos por cargo, operacao do worker e riscos de spool aparecem em varios documentos. Isso e util, mas ainda nao ha fonte primaria declarada. |
| Entidades ausentes | Jobs de download/video, tickets de download, Radius/radcheck, arquivos fisicos de spool/APC e configuracoes operacionais ainda nao estao plenamente modelados como entidades/documentos de dominio. |
| Modulos legados nao mapeados | APC, PCPI, Download, Recursos e Administracao estao mapeados no inventario geral, mas nao possuem documentos dedicados completos. |
| Afirmacoes sem evidencia | Alguns documentos usam "parece", "inferida" ou "pendente" corretamente, mas outros placeholders ainda nao indicam evidencia real. |
| Documentos inconsistentes | Ha divergencia entre documentos consolidados e placeholders ainda marcados como pendentes. |
| Fluxos incompletos | Fluxos consolidados existem em `demais-fluxos-identificados.md`, mas arquivos especificos de impressao, autenticacao e administracao continuam vazios. |
| Permissoes nao documentadas | O mapa geral e bom, mas alguns escopos permanecem pendentes: download para todos autenticados, listagem ampla de reservas, permissao de coordenador em agendamento e cobertura completa de pre-conselho. |

## Achados priorizados

| ID | Categoria | Severidade | Achado | Evidencia | Impacto | Encaminhamento documental |
| --- | --- | --- | --- | --- | --- | --- |
| RC-001 | Funcionalidade sem documentacao | Alta | Documentos dedicados de varios modulos ainda estao como placeholders. | `docs/03-modulos/impressao.md`, `autenticacao.md`, `usuarios.md`, `relatorios.md`, `pre-conselho.md`, `ocorrencias.md`, `auditoria.md`, `horario-escolar.md`, `demais-modulos-identificados.md`. | O inventario geral existe, mas a consulta por modulo fica incompleta. | Promover conteudo de `docs/01-visao-geral/modulos.md` para documentos especificos por modulo. |
| RC-002 | Fluxo incompleto | Alta | Arquivos especificos de fluxo ainda estao pendentes, apesar de haver consolidado em `demais-fluxos-identificados.md`. | `docs/06-fluxos/impressao.md`, `autenticacao.md`, `administracao.md` versus `docs/06-fluxos/demais-fluxos-identificados.md`. | Leitores podem abrir o fluxo especifico e concluir que nao ha mapeamento. | Dividir o consolidado nos arquivos especificos ou marcar explicitamente onde esta a fonte atual. |
| RC-003 | Regra contraditoria | Alta | Agendamento permite gestor/coordenador listar professores, mas a criacao com `professor_id` aparenta depender do resolver compartilhado que exige admin em alguns cenarios. | `docs/03-modulos/agendamento.md`: duvida pendente; `docs/04-dominio/permissoes.md`: agendamento; `modules/scheduling/router.py`: `professores_agendamento`; `routers/common.py`: `resolver_usuario_professor_selecionado`. | Pode orientar regra de produto errada para coordenadores. | Manter como decisao pendente destacada em requisitos, permissoes e modulo de agendamento. |
| RC-004 | Modulo legado nao mapeado | Alta | APC/anexos aparece no inventario e requisitos, mas nao possui `docs/03-modulos/apc.md`; fica dentro de `demais-modulos-identificados.md` pendente. | `docs/01-visao-geral/modulos.md`; `docs/02-requisitos/requisitos-funcionais.md`; `docs/02-requisitos/regras-de-negocio.md`; `docs/03-modulos/demais-modulos-identificados.md`. | APC e um fluxo relevante com upload, review, preview e impressao, mas nao tem documento de modulo dedicado. | Criar documento especifico para APC/anexos ou expandir `demais-modulos-identificados.md` com secao completa. |
| RC-005 | Modulo legado nao mapeado | Alta | PCPI esta reconhecido, mas sem documento proprio completo. | `docs/01-visao-geral/modulos.md`: PCPI; `pcpi_router.py`; `services/pcpi_service.py`; placeholder em `demais-modulos-identificados.md`. | Regras e fluxos PCPI podem ficar fora do plano de refatoracao. | Criar `docs/03-modulos/pcpi.md` ou documentar PCPI de forma completa em demais modulos. |
| RC-006 | Modulo legado nao mapeado | Alta | Download de videos aparece como modulo, mas nao possui documento proprio nem requisito funcional catalogado. | `docs/01-visao-geral/modulos.md`: Download De Videos; `routers/download_router.py`; `services/youtube_download_service.py`; RF lista apenas impressao/agendamento/anexos. | Permissoes, persistencia em memoria e consumo de recursos podem ser subestimados. | Incluir RF/RN de download e documento de modulo/fluxo. |
| RC-007 | Entidade ausente | Media | Jobs/tickets de download nao aparecem como entidade de dominio persistente; a documentacao menciona ausencia de tabela, mas nao modela o conceito. | `docs/01-visao-geral/modulos.md`: Download; `docs/07-dados/tabelas.md`: pendencia sobre armazenamento persistente. | Dificulta decidir se download e recurso operacional temporario ou modulo com historico. | Registrar "DownloadJob/Ticket" como entidade transiente ou pendente em `docs/04-dominio/entidades.md`. |
| RC-008 | Entidade ausente | Media | Arquivos fisicos de spool/APC/download sao centrais, mas aparecem mais em operacao do que no dominio. | `docs/08-operacao/worker.md`; `docs/08-operacao/backup.md`; `docs/04-dominio/entidades.md`. | Pode faltar rastreabilidade entre tabelas `jobs`/`apc_envios` e arquivos fisicos. | Incluir entidade operacional "Arquivo armazenado/spool" ou secao transversal em dominio/dados. |
| RC-009 | Entidade ausente | Media | Radius/radcheck aparece como integracao, mas a entidade/view ainda esta pendente de detalhe. | `docs/01-visao-geral/modulos.md`: `radcheck`/view pendente; `docs/04-dominio/permissoes.md`: Radius interno; `routers/system_router.py`. | Integracao sensivel pode ficar pouco rastreavel em seguranca e dados. | Documentar view/tabela Radius em dominio/dados quando validada. |
| RC-010 | Regra duplicada | Media | Permissoes por cargo aparecem em `usuarios-e-perfis.md`, `permissoes.md`, `modulos.md`, `requisitos-nao-funcionais.md` e `dividas-tecnicas.md`. | Arquivos citados. | Risco de divergencia se um documento for atualizado e outro nao. | Declarar `docs/04-dominio/permissoes.md` como fonte primaria e referenciar nos demais. |
| RC-011 | Regra duplicada | Media | Riscos de spool/retencao aparecem em operacao, dividas tecnicas, arquitetura e fluxos. | `docs/08-operacao/worker.md`, `backup.md`, `configuracao.md`; `docs/05-arquitetura/dividas-tecnicas.md`; `docs/06-fluxos/demais-fluxos-identificados.md`. | Repeticao util, mas pode gerar inconsistencia de politica. | Manter politica operacional em `docs/08-operacao/worker.md` e referenciar nos demais. |
| RC-012 | Documento inconsistente | Media | `docs/01-visao-geral/modulos.md` esta detalhado, mas `docs/03-modulos/demais-modulos-identificados.md` ainda diz "modulos iniciais". | Comparacao direta entre os dois documentos. | Leitor pode achar que APC/PCPI/Download/Recursos ainda nao foram mapeados. | Atualizar `demais-modulos-identificados.md` ou substituir por indice de modulos sem documento proprio. |
| RC-013 | Documento inconsistente | Media | `docs/02-requisitos/requisitos-nao-funcionais.md` ainda diz que backup/restore nao foi localizado, enquanto `docs/08-operacao/backup.md` agora documenta a ausencia de rotina e dados a proteger. | `docs/02-requisitos/requisitos-nao-funcionais.md`: RNF-BKP-001/RNF-OPS-004; `docs/08-operacao/backup.md`. | Nao e contradicao de codigo, mas a evidencia documental mudou. | Ajustar RNF para referenciar `docs/08-operacao/backup.md` como evidencia de pendencia operacional. |
| RC-014 | Afirmacao sem evidencia suficiente | Media | "Backend valida acoes criticas" aparece como conclusao ampla, mas a auditoria completa de todos os endpoints/JS ainda esta pendente. | `docs/01-visao-geral/modulos.md`: Demais Pontos Transversais; `docs/05-arquitetura/arquitetura-alvo.md`: JavaScript sem regra critica pendente; `docs/05-arquitetura/dividas-tecnicas.md`. | Pode passar seguranca maior do que a validada. | Reclassificar como "majoritariamente observado nos fluxos analisados" e manter auditoria de permissao pendente. |
| RC-015 | Permissao nao documentada | Alta | Download de videos permite usuario autenticado comum, mas a decisao de produto/perfil esta pendente. | `docs/04-dominio/permissoes.md`: risco; `routers/download_router.py`: endpoints autenticados. | Consumo de recursos e risco operacional podem ser ignorados. | Criar decisao pendente explicita em requisitos/permissoes/download. |
| RC-016 | Permissao nao documentada | Media | Listagem de reservas de agendamento e recursos nao limita por professor; pode ser visao compartilhada, mas precisa decisao. | `docs/04-dominio/permissoes.md`: risco; `modules/scheduling/router.py`: `listar_reservas_agendamento`. | Pode expor informacao de agenda para todos autenticados se nao for intencional. | Manter como pendencia funcional em agendamento e permissoes. |
| RC-017 | Permissao nao documentada | Media | Pre-conselho tem mapa geral, mas o proprio documento de permissoes marca revisao completa dos endpoints como pendente. | `docs/04-dominio/permissoes.md`: frontend/preconselho; `docs/01-visao-geral/modulos.md`: Pre-Conselho. | Pode faltar distincao final entre professor, gestor e admin por acao. | Detalhar permissoes no documento de modulo pre-conselho. |
| RC-018 | Regras ausentes | Alta | Regras de negocio catalogadas cobrem autenticacao, impressao, agendamento e anexos, mas nao cobrem usuarios, ocorrencias, pre-conselho, PCPI, auditoria, relatorios, horario escolar e download. | `docs/02-requisitos/regras-de-negocio.md`: "Proximos Modulos A Extrair"; `docs/01-visao-geral/modulos.md`. | Decisoes futuras podem se basear em regras incompletas. | Priorizar RN dos modulos legados antes de refatorar cada um. |
| RC-019 | Requisitos ausentes | Alta | Requisitos funcionais cobrem impressao, agendamento e anexos, mas deixam varios modulos em "Proximos Modulos A Catalogar". | `docs/02-requisitos/requisitos-funcionais.md`. | Backlog funcional fica incompleto para planejamento. | Completar RF por modulo em ordem de risco/refatoracao. |
| RC-020 | Fluxo incompleto | Media | Fluxos principais cobrem oito fluxos, mas nao cobrem APC envio/revisao, ocorrencias, pre-conselho, PCPI, horario escolar, relatorios e download. | `docs/06-fluxos/demais-fluxos-identificados.md`; `docs/01-visao-geral/modulos.md`. | Refatoracoes desses modulos podem iniciar sem mapa de fluxo. | Criar fluxos por modulo antes de refatorar o modulo correspondente. |
| RC-021 | Documento pendente estrutural | Media | `docs/05-arquitetura/dependencias.md` e `riscos.md` ainda estao como placeholders, embora informacoes existam em outros documentos. | Arquivos citados; `docs/05-arquitetura/dividas-tecnicas.md`. | Riscos e dependencias ficam espalhados. | Consolidar depois desta revisao cruzada. |
| RC-022 | Entidade/relacao pendente | Media | Vinculos academicos `professores_turmas_disciplinas` versus `turmas_disciplinas` aparecem como atuais/legados sem decisao. | `docs/04-dominio/relacionamentos.md`; `docs/07-dados/relacionamentos.md`; `docs/01-visao-geral/modulos.md`. | Pode afetar refatoracao de usuarios, horario, APC e pre-conselho. | Manter decisao pendente de dominio/dados antes de alterar vinculos academicos. |
| RC-023 | Estado contraditorio/incompleto | Media | Status de impressao `CONCLUIDO` e `FINALIZADO` aparecem como reutilizaveis, mas o lifecycle final ainda esta pendente. | `docs/02-requisitos/regras-de-negocio.md`: RN-IMP-006; `docs/01-visao-geral/modulos.md`: duvida impressao. | Pode gerar decisao errada em historico/reimpressao/worker. | Formalizar estados de job antes de mexer em impressao. |
| RC-024 | Afirmacao sem evidencia suficiente | Baixa | Alguns documentos de visao geral usam "parece estar em producao" ou inferencias de uso real sem confirmacao operacional. | `docs/01-visao-geral/produto.md`; `AGENTS.md` fala em uso real. | Baixo para codigo, mas pode afetar priorizacao de produto. | Separar "em uso real informado" de "confirmado por deploy/log/operacao". |

## Funcionalidades sem documentacao dedicada

| Funcionalidade/modulo | Onde aparece hoje | Documento dedicado esperado/ausente | Prioridade sugerida |
| --- | --- | --- | --- |
| APC/anexos | Inventario, RF/RN, permissoes, fluxos parciais | `docs/03-modulos/apc.md` ou secao completa em `demais-modulos-identificados.md`; fluxo APC | Alta |
| PCPI | Inventario geral | Documento de modulo e regras/fluxos | Alta |
| Download de videos | Inventario geral, permissoes, operacao | Documento de modulo, RF/RN, fluxo e entidade transiente | Alta |
| Recursos | Inventario geral, agendamento/admin | Documento de modulo ou decisao de subdominio | Media |
| Administracao | Fluxo consolidado, admin_router | `docs/06-fluxos/administracao.md` completo e modulo/admin como interface | Media |
| Ocorrencias | Inventario geral e entidades | Documento de modulo dedicado completo, RN e fluxos | Alta |
| Pre-conselho | Inventario geral e entidades | Documento de modulo dedicado completo, RN e fluxos | Alta |
| Horario escolar | Inventario geral e entidades | Documento de modulo dedicado completo e fluxos | Media |
| Relatorios | Inventario geral | Documento de modulo, RF/RN e indicadores oficiais | Media |
| Auditoria | Inventario geral, fluxo de registro | Documento de modulo completo e matriz de eventos | Media |

## Regras contraditorias ou a decidir

| Tema | Contradicao/tensao | Documentos envolvidos | Status |
| --- | --- | --- | --- |
| Coordenador em agendamento | Pode listar professores, mas criar reserva para professor selecionado pode exigir admin. | `docs/03-modulos/agendamento.md`; `docs/04-dominio/permissoes.md`; `docs/06-fluxos/agendamento.md`. | Pendente de validacao |
| Download por perfil | Modulo visivel/permitido para autenticados, mas consumo de recursos pode exigir restricao. | `docs/04-dominio/permissoes.md`; `docs/01-visao-geral/modulos.md`. | Pendente de validacao |
| Paginas sem auth backend | Templates abrem sem token, APIs protegem dados. Esta regra esta documentada como risco, mas precisa decisao se e aceitavel. | `docs/04-dominio/permissoes.md`; `docs/01-visao-geral/modulos.md`; `docs/05-arquitetura/dividas-tecnicas.md`. | Pendente de validacao |
| Worker embutido versus externo | Operacao documenta ambos; deploy recomenda externo. | `docs/08-operacao/worker.md`; `docs/05-arquitetura/arquitetura-alvo.md`; `.env.example`. | Pendente de decisao operacional |
| `app/core/shared` versus raiz atual | Arquitetura alvo e estado atual divergem. | `AGENTS.md`; `ARCHITECTURE.md`; `docs/05-arquitetura/arquitetura-alvo.md`. | Pendente de decisao arquitetural |

## Regras duplicadas

| Regra/tema | Locais onde aparece | Risco | Fonte primaria sugerida |
| --- | --- | --- | --- |
| Permissoes por cargo/modulo | `usuarios-e-perfis.md`, `permissoes.md`, `modulos.md`, `requisitos-nao-funcionais.md`. | Divergencia futura. | `docs/04-dominio/permissoes.md`. |
| Worker/spool/retencao | `worker.md`, `backup.md`, `configuracao.md`, `dividas-tecnicas.md`, fluxos. | Politica operacional divergente. | `docs/08-operacao/worker.md`. |
| Arquitetura hibrida/legada | `estado-atual.md`, `arquitetura-alvo.md`, `dividas-tecnicas.md`, `modulos.md`. | Repeticao pode ficar desalinhada. | `docs/05-arquitetura/estado-atual.md`. |
| Pendencias de validacao | Diversos documentos e `pendencias-de-validacao.md` ainda placeholder. | Pendencias espalhadas. | `docs/02-requisitos/pendencias-de-validacao.md`. |

## Afirmacoes que precisam de mais evidencia

| Afirmacao | Onde aparece | Problema | Acao documental |
| --- | --- | --- | --- |
| "Backend valida acoes criticas" | `docs/01-visao-geral/modulos.md`, pontos transversais. | A auditoria completa de todos os endpoints/JS ainda nao foi feita. | Reclassificar para "confirmado nos fluxos analisados" e manter auditoria pendente. |
| "Funcionalidades parecem estar em producao" | `docs/01-visao-geral/produto.md`. | Uso em producao foi inferido/informado, nao verificado por deploy/log. | Separar evidencia por codigo, por deploy e por confirmacao humana. |
| `radcheck`/Radius | `docs/01-visao-geral/modulos.md`, permissoes. | Falta detalhe de view/tabela e operacao real. | Mapear integracao Radius em dados/operacao. |
| Limites de upload | `requisitos-nao-funcionais.md`, operacao. | Nginx tem `50m`, mas limite por rota/modulo nao esta totalmente confirmado. | Documentar limites por camada: Nginx, FastAPI/rota, service. |

## Pendencias a centralizar

`docs/02-requisitos/pendencias-de-validacao.md` ainda esta como placeholder. Ele deve receber, no minimo:

- permissao de coordenador em agendamento;
- download liberado para todos autenticados;
- listagem ampla de reservas;
- politica de backup/restore;
- politica de retencao do spool;
- troca/desativacao de credenciais iniciais;
- lifecycle final de status de jobs;
- vinculos academicos atuais versus legados;
- consumo real de `configuracao_turnos_segmentos`;
- cobertura obrigatoria de auditoria por modulo;
- estrategia para `database.py` e `db/*.py`;
- decisao sobre `app/`, `core/` e `shared`.

## Ordem sugerida para corrigir a documentacao

1. Atualizar `docs/02-requisitos/pendencias-de-validacao.md` como indice central de decisoes pendentes.
2. Completar `docs/06-fluxos/impressao.md`, `autenticacao.md` e `administracao.md` usando o consolidado de fluxos.
3. Completar documentos dedicados em `docs/03-modulos/` para impressao, autenticacao, usuarios e os placeholders atuais.
4. Criar ou expandir documentacao de APC, PCPI, Download, Recursos e Administracao.
5. Completar RF/RN dos modulos ainda nao catalogados.
6. Consolidar `docs/05-arquitetura/dependencias.md` e `riscos.md`.
7. Revisar duplicacoes, declarando a fonte primaria de cada tema e deixando os demais documentos como referencias.

## Conclusao

A documentacao ja tem uma base forte para arquitetura, dados, operacao, agendamento, permissoes e fluxos principais. O maior risco agora nao e falta total de informacao, e sim informacao consolidada convivendo com placeholders e pendencias espalhadas. Antes de usar a documentacao como guia de refatoracao, vale fechar os documentos fonte de verdade por tema e centralizar as decisoes pendentes.
