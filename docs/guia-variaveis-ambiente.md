# Guia de variaveis de ambiente

Este documento mapeia as variaveis de ambiente usadas hoje pelo projeto e explica como tratar o `.env` no ambiente local e no servidor.

## Resumo rapido

- O codigo le configuracao com `os.getenv(...)`.
- A aplicacao nao usa `python-dotenv` nem carrega `.env` automaticamente.
- No ambiente local, os scripts [`run_local_api.ps1`](../run_local_api.ps1) e [`run_local_worker.ps1`](../run_local_worker.ps1) criam alguns defaults em memoria, mas nao leem um arquivo `.env`.
- No servidor, os servicos `systemd` em [`deploy/systemd/sistema-impress-api.service`](../deploy/systemd/sistema-impress-api.service) e [`deploy/systemd/sistema-impress-worker.service`](../deploy/systemd/sistema-impress-worker.service) carregam `/opt/sistema-impress/.env` com `EnvironmentFile=`.

## Como o `.env` funciona hoje

### Ambiente local

Se voce apenas criar um arquivo `.env` na raiz, ele nao sera carregado sozinho pela API nem pelo worker.

Hoje o comportamento local padrao e:

- `run_local_api.ps1` define `DB_PATH=../sistema-impress-data/impressao.db` se a variavel nao existir.
- `run_local_api.ps1` define `SPOOL_DIR=spool` se a variavel nao existir.
- `run_local_api.ps1` define `ENABLE_EMBEDDED_WORKER=0` se a variavel nao existir, ou `1` quando chamado com `-EmbeddedWorker`.
- `run_local_worker.ps1` define `DB_PATH=../sistema-impress-data/impressao.db` se a variavel nao existir.
- `run_local_worker.ps1` define `SPOOL_DIR=spool` se a variavel nao existir.

Se quiser sobrescrever algo localmente, exporte as variaveis antes de subir a aplicacao:

```powershell
$env:DB_PATH = (Join-Path (Split-Path -Parent $PWD) "sistema-impress-data\\impressao.db")
$env:SPOOL_DIR = "$PWD\\spool"
$env:ENABLE_EMBEDDED_WORKER = "0"
.\run_local_api.ps1
```

### Servidor

No servidor, o fluxo ja esta preparado para um arquivo `.env` real:

- `systemd` carrega `/opt/sistema-impress/.env` ao subir a API e o worker.
- a workflow de deploy e o procedimento manual de migracao tambem fazem `set -a; . ./.env; set +a` antes de executar `db.schema_migrations`.

Por isso, no servidor, vale a pena manter um arquivo `/opt/sistema-impress/.env` com valores absolutos e estaveis.

## Mapa das variaveis suportadas

| Variavel | Onde e usada | Default no codigo | Observacoes praticas |
| --- | --- | --- | --- |
| `DB_PATH` | `database.py`, `db.schema_migrations`, `migrations/*` | `../sistema-impress-data/impressao.db` | Caminho do SQLite. Se relativo, o codigo resolve em relacao a raiz do repositorio. No servidor prefira caminho absoluto. |
| `SPOOL_DIR` | `routers/config.py`, `routers/impressao_router.py` | `./spool` | Diretorio onde uploads e PDFs temporarios ficam aguardando processamento. No servidor prefira `/var/spool/sistema-impress`. |
| `CUPS_PRINTER` | `routers/config.py`, `services/printer.py` | vazio | Fila padrao do CUPS. Use o nome exato retornado por `lpstat -p`. |
| `ENABLE_EMBEDDED_WORKER` | `routers/config.py`, `main.py` | `false` | Aceita `1`, `true` ou `yes` para ativar. Em producao, o recomendado e `false` quando houver servico worker dedicado. |
| `KEEP_SPOOL_FILES` | `services/worker.py` | `true` | Mantem os arquivos do spool apos impressao concluida. Isso permite preview e reimpressao do historico. Desative apenas se quiser abrir mao dessa feature. |
| `SPOOL_RETENTION_DAYS` | `services/worker.py` | `0` | Quando maior que zero, o worker remove arquivos do `SPOOL_DIR` mais antigos que esse numero de dias. Jobs `PENDENTE` e `IMPRIMINDO` sao preservados. |
| `LOG_LEVEL` | `app_logging.py` | `INFO` | Aceita niveis do `logging`, como `DEBUG`, `INFO`, `WARNING` e `ERROR`. |
| `TOKEN_TTL_DIAS` | `database.py`, `services/auth_service.py` | `7` | So aceita `7` ou `15`. Qualquer outro valor volta para `7`. |
| `PRINT_CANCEL_WINDOW_SECONDS` | `routers/config.py`, `services/worker.py` | `15` | Janela de cancelamento antes do worker despachar o job. Valores invalidos voltam para `15`. |
| `STATIC_ASSET_VERSION` | `routers/config.py`, `routers/pages_router.py` | timestamp do boot | Opcional. Se vazio, muda a cada restart. Se definido como `dynamic`, gera uma versao nova a cada resposta e evita precisar reiniciar a API para enxergar mudancas de CSS e JS no desenvolvimento local. No deploy automatizado, a workflow atualiza esse valor com o SHA do commit para invalidar cache de CSS e JS a cada publicacao. |
| `RADIUS_INTERNAL_SECRET` | `routers/config.py`, `routers/system_router.py` | vazio | Protege o endpoint interno `/internal/radius/ensure-nt-hash`. Se vazio, a integracao fica efetivamente desativada. |
| `CUPS_LP_COMMAND` | `services/printer.py` | `lp` | Nome do comando ou caminho absoluto. Em servidor Linux, usar `/usr/bin/lp` pode deixar o ambiente mais previsivel. |
| `CUPS_LP_TIMEOUT_SECONDS` | `services/printer.py` | `30` | Deve ser inteiro valido. Diferente de outras variaveis numericas, aqui um valor invalido pode quebrar a inicializacao do processo. |
| `LIBREOFFICE_COMMAND` | `services/file_service.py` | autodeteccao | Usada para conversao de `DOC` e `DOCX` em PDF. Se `soffice` nao estiver no `PATH`, informe o caminho absoluto. |

## Sugestao de `.env` para o servidor

Exemplo base para `/opt/sistema-impress/.env`:

```dotenv
DB_PATH=/opt/sistema-impress-data/impressao.db
SPOOL_DIR=/var/spool/sistema-impress
CUPS_PRINTER=HP_LaserJet
ENABLE_EMBEDDED_WORKER=false
KEEP_SPOOL_FILES=true
SPOOL_RETENTION_DAYS=7
LOG_LEVEL=INFO
TOKEN_TTL_DIAS=7
PRINT_CANCEL_WINDOW_SECONDS=15
RADIUS_INTERNAL_SECRET=
CUPS_LP_COMMAND=/usr/bin/lp
CUPS_LP_TIMEOUT_SECONDS=30
LIBREOFFICE_COMMAND=/usr/bin/soffice
# STATIC_ASSET_VERSION=release-2026-04-13
```

## O que eu recomendo no servidor

- Use caminhos absolutos em todas as variaveis de caminho.
- Mantenha `ENABLE_EMBEDDED_WORKER=false` e rode o worker em servico separado.
- Deixe `KEEP_SPOOL_FILES=true` para preservar preview e reimpressao do historico.
- Configure `SPOOL_RETENTION_DAYS` com um prazo curto, como `7`, para evitar crescimento indefinido do spool.
- Preencha `RADIUS_INTERNAL_SECRET` apenas se a integracao com FreeRADIUS estiver ativa.
- Se a impressao de `DOC` e `DOCX` for necessaria, instale o LibreOffice e configure `LIBREOFFICE_COMMAND` de forma explicita.
- No deploy automatizado, a workflow sobrescreve `STATIC_ASSET_VERSION` com o SHA do commit publicado.
- No desenvolvimento local, use `STATIC_ASSET_VERSION=dynamic` para forcar recarga imediata dos assets ao atualizar a pagina.
- Use `TOKEN_TTL_DIAS=7` como padrao mais conservador.

## Operacao segura do arquivo `.env`

- Mantenha o arquivo fora do Git. A raiz do projeto ja ignora `.env` em [`.gitignore`](../.gitignore).
- Em Linux, prefira permissao restrita, por exemplo:

```bash
sudo chown root:sistema-impress /opt/sistema-impress/.env
sudo chmod 640 /opt/sistema-impress/.env
```

- Depois de alterar o `.env`, reinicie os servicos:

```bash
sudo systemctl restart sistema-impress-api
sudo systemctl restart sistema-impress-worker
```

## Melhoria futura opcional

Se voces quiserem padronizar melhor o desenvolvimento local, um proximo passo interessante e fazer os scripts `run_local_*.ps1` lerem o `.env` quando ele existir. Hoje isso ainda nao acontece.
