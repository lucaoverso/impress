# Mapa do Repositório

## Visão rápida por domínio

Este é o mapa lógico do sistema. Ele mostra onde cada assunto pertence, mesmo que
os arquivos ainda estejam distribuídos em mais de uma pasta durante a
refatoração gradual.

```text
app/ (visão lógica; ainda não existe como diretório físico)
├── auth/
├── printing/
├── scheduling/
├── coordination/
│   ├── occurrences/
│   ├── apc_review/
│   ├── teacher_followup/
│   ├── school_schedule/
│   └── audit/
├── preconselho/
├── reports/
├── users/
├── video_downloads/
├── library/              [domínio ainda não identificado no código]
├── core/
└── shared/
```

Os nomes em inglês seguem a convenção definida em `ARCHITECTURE.md`. Nomes de
rotas, templates e arquivos legados em português devem ser preservados enquanto
forem contratos públicos ou pontos de compatibilidade.

## Onde cada domínio está hoje

| Domínio lógico | Implementação principal atual | Complementos ainda distribuídos |
| --- | --- | --- |
| `auth` | `auth.py`, `services/auth_service.py` | `db/usuarios.py`, `security/` |
| `printing` | `modules/printing/` | `routers/impressao_router.py`, serviços de impressão e `db/impressao.py` |
| `scheduling` | `modules/scheduling/` | `db/agendamento.py`, template e arquivos estáticos de agendamento |
| `coordination/occurrences` | `modules/occurrences/` | `ocorrencias_router.py`, serviços e `db/ocorrencias.py` |
| `coordination/apc_review` | `modules/apc_review/` | `routers/apc_router.py`, serviços e `db/apc.py` |
| `coordination/teacher_followup` | `modules/teacher_followup/` | JavaScript e template de coordenação |
| `coordination/school_schedule` | `routers/horario_escolar_router.py` | `services/horario_escolar_service.py`, `db/horario_escolar.py` |
| `coordination/audit` | `modules/audit/` | painel de auditoria nos templates e arquivos estáticos administrativos |
| `preconselho` | `modules/preconselho/` | `preconselho_router.py`, serviço legado e `db/preconselho.py` |
| `reports` | `modules/reports/` | `routers/relatorios_router.py`, `db/relatorios.py` |
| `users` | `routers/professores_router.py` | `db/usuarios.py`, `db/docencia.py`, cadastro e administração |
| `video_downloads` | `routers/download_router.py` | serviços `youtube_download_*` e worker associado |
| `library` | ainda não identificado | não há módulo, rota, serviço ou tabela claramente associados |

## Estrutura física atual

```text
.
├── main.py                 # entrada da aplicação FastAPI
├── worker_main.py          # entrada do worker
├── auth.py                 # autenticação e dependências legadas
├── database.py             # banco e compatibilidade legada
├── models.py               # modelos ainda centralizados
├── modules/                # módulos já organizados por domínio
├── routers/                # rotas ainda organizadas por camada
├── services/               # serviços ainda organizados por camada
├── db/                     # acesso a dados por domínio e bootstrap
├── templates/              # páginas Jinja2
├── static/                 # CSS, JavaScript e imagens
├── migrations/             # evolução do banco SQLite
├── tests/                  # testes automatizados
├── deploy/                 # configuração de execução e proxy
├── infra/                  # integrações de infraestrutura
└── docs/                   # documentação técnica e funcional
```

## Direção arquitetural

O destino continua sendo a organização definida em `ARCHITECTURE.md`:

```text
app/
├── core/
├── shared/
├── modules/
│   └── <domain>/
│       ├── router.py
│       ├── service.py
│       ├── repository.py
│       ├── schemas.py
│       └── models.py
├── templates/
├── static/
└── db/
```

Este mapa não autoriza movimentação em massa. Cada domínio deve migrar
separadamente, preservando rotas públicas, banco, templates e JavaScript.
