# Deploy local (servidor da escola)

Este guia prepara:
- API FastAPI (`main.py`)
- Worker de impressão (`worker_main.py`)
- CUPS local no servidor
- Nginx como reverse proxy

## 1) Pré-requisitos no servidor (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip cups cups-client nginx libreoffice nodejs
```

## 2) Criar usuário de serviço

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin sistema-impress || true
sudo usermod -aG lp sistema-impress
```

## 2.1) Liberar `sudo` sem senha para o usuário do runner

A workflow de deploy em [`.github/workflows/deploy.yml`](/Users/lucassbaraini/sistema-impress/.github/workflows/deploy.yml:1) usa `sudo -n`, ou seja: ela **não pode** pedir senha interativamente. Se o servidor estiver com um runner `self-hosted`, o usuário que executa o serviço do GitHub Actions precisa ter permissão `NOPASSWD` apenas para os comandos usados no deploy.

Descubra primeiro qual é o usuário do runner:

```bash
ps -ef | grep actions-runner
```

Depois crie um arquivo em `/etc/sudoers.d/` com `visudo` (troque `runneruser` pelo usuário real do runner):

```bash
sudo visudo -f /etc/sudoers.d/sistema-impress-deploy
```

Conteúdo sugerido:

```sudoers
Cmnd_Alias SISTEMA_IMPRESS_GIT = /usr/bin/rm -f /opt/sistema-impress/.git/index.lock, /usr/bin/git -C /opt/sistema-impress *
Cmnd_Alias SISTEMA_IMPRESS_APP = /usr/bin/bash -lc *
Cmnd_Alias SISTEMA_IMPRESS_SYSTEMD = /usr/bin/systemctl restart sistema-impress-api.service, /usr/bin/systemctl restart sistema-impress-worker.service, /usr/bin/systemctl is-active --quiet sistema-impress-api.service, /usr/bin/systemctl is-active --quiet sistema-impress-worker.service

runneruser ALL=(sistema-impress) NOPASSWD: SISTEMA_IMPRESS_GIT, SISTEMA_IMPRESS_APP
runneruser ALL=(root) NOPASSWD: SISTEMA_IMPRESS_SYSTEMD
```

Valide antes de fechar:

```bash
sudo visudo -cf /etc/sudoers.d/sistema-impress-deploy
```

Se preferir simplificar a operacao, uma alternativa e executar o runner como `root`, mas isso aumenta bastante a superficie de risco. A configuracao acima e a opcao recomendada.

## 3) Publicar código em `/opt/sistema-impress`

```bash
sudo mkdir -p /opt/sistema-impress
sudo chown -R $USER:$USER /opt/sistema-impress
cd /opt/sistema-impress
git clone <SEU_REPOSITORIO_GIT> .
```

## 4) Ambiente Python

```bash
cd /opt/sistema-impress
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 5) Variáveis de ambiente

```bash
cd /opt/sistema-impress
cp .env.example .env
```

Ajuste obrigatório em `.env`:
- `CUPS_PRINTER` com o nome exato da fila CUPS (`lpstat -p`)
- `SPOOL_DIR=/var/spool/sistema-impress`
- `ENABLE_EMBEDDED_WORKER=false`

Ajuste recomendado em `.env` para o banco fora da pasta do código:
- `DB_PATH=/opt/sistema-impress-data/impressao.db`
- `LOG_LEVEL=INFO`

Ajuste recomendado para o módulo de downloads do YouTube:
- confirme que `node` está instalado com `node --version`
- deixe `YTDLP_JS_RUNTIMES=node` no `.env` se quiser forçar esse runtime explicitamente

Ajuste opcional para diagnostico controlado no spool:
- `KEEP_SPOOL_FILES=true`
- `SPOOL_RETENTION_DAYS=7`

Ajuste recomendado para integração FreeRADIUS:
- `RADIUS_INTERNAL_SECRET=<segredo-forte-aleatorio>` (usado no endpoint interno de migração silenciosa de `nt_hash`)

## 6) Diretórios e permissões

```bash
sudo mkdir -p /var/spool/sistema-impress
sudo mkdir -p /opt/sistema-impress-data
sudo chown -R sistema-impress:lp /var/spool/sistema-impress
sudo chown -R sistema-impress:lp /opt/sistema-impress
sudo chown -R sistema-impress:lp /opt/sistema-impress-data
```

## 7) Configurar CUPS e impressora

Verifique filas configuradas:

```bash
lpstat -p
lpstat -d
```

Se necessário, defina a padrão:

```bash
sudo lpadmin -d <NOME_DA_IMPRESSORA>
```

## 8) Instalar serviços `systemd`

```bash
sudo cp deploy/systemd/sistema-impress-api.service /etc/systemd/system/
sudo cp deploy/systemd/sistema-impress-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-impress-api
sudo systemctl enable --now sistema-impress-worker
```

Verificação:

```bash
sudo systemctl status sistema-impress-api --no-pager
sudo systemctl status sistema-impress-worker --no-pager
```

Logs:

```bash
journalctl -u sistema-impress-api -f
journalctl -u sistema-impress-worker -f
```

Aplicar migrations manualmente antes de um restart planejado:

```bash
cd /opt/sistema-impress
set -a
. ./.env
set +a
.venv/bin/python -m db.schema_migrations upgrade
```

## 9) Configurar Nginx

```bash
sudo cp deploy/nginx/sistema-impress.conf /etc/nginx/sites-available/sistema-impress
sudo ln -sf /etc/nginx/sites-available/sistema-impress /etc/nginx/sites-enabled/sistema-impress
sudo nginx -t
sudo systemctl reload nginx
```

## 10) Teste final

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1/health
```

Resultado esperado:
- JSON com `"status":"ok"` e `checks.database = "ok"`
- worker ativo sem erro no `journalctl`
- envio de impressão cria job e envia para CUPS (`lp`)

Se o deploy automatizado falhar com mensagem parecida com `sudo: a password is required`, revise primeiro o passo `2.1`: normalmente isso indica que o usuário do runner ainda não recebeu as regras `NOPASSWD` esperadas pela workflow.

## Acesso remoto via 5G

Para acesso externo seguro, use VPN (Tailscale/WireGuard) e exponha apenas o Nginx.
Não exponha porta 631 (CUPS) na internet.

## Integração FreeRADIUS

Os arquivos de apoio ficam em:
- `infra/freeradius/clients.conf.snippet`
- `infra/freeradius/sql-setup.md`
- `infra/freeradius/create-radius-db-user.sql`
- `infra/freeradius/inner-tunnel.snippet`
- `infra/freeradius/troubleshooting.md`
- `infra/freeradius/internal-endpoint.md`
