# Deploy local (servidor da escola)

Este guia prepara:
- API FastAPI (`main.py`)
- Worker de impressão (`worker_main.py`)
- CUPS local no servidor
- Nginx como reverse proxy

## 1) Pré-requisitos no servidor (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip cups cups-client nginx
```

## 2) Criar usuário de serviço

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin sistema-impress || true
sudo usermod -aG lp sistema-impress
```

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
- `{"status":"ok"}` nas duas chamadas
- worker ativo sem erro no `journalctl`
- envio de impressão cria job e envia para CUPS (`lp`)

## Acesso remoto via 5G

Para acesso externo seguro, use VPN (Tailscale/WireGuard) e exponha apenas o Nginx.
Não exponha porta 631 (CUPS) na internet.
