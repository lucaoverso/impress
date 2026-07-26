# Notificações internas e Web Push

## Componentes

- A API e a caixa interna funcionam no processo FastAPI.
- `notification_worker_main.py` reconcilia a APC e processa Web Push.
- `sistema-impress-notifications-worker.service` mantém esse worker separado da fila CUPS.
- Desabilitar `WEB_PUSH_ENABLED` interrompe apenas o canal externo.

## Variáveis

```dotenv
WEB_PUSH_ENABLED=false
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=https://sistema.eepjd.com.br
APP_TIMEZONE=America/Campo_Grande
```

A chave privada VAPID deve permanecer somente no `.env` do servidor. O mesmo par de
chaves deve ser preservado entre deploys; trocar o par exige novas assinaturas dos
dispositivos.

## Rollout seguro

1. Fazer backup do SQLite antes da migration.
2. Publicar o código com `WEB_PUSH_ENABLED=false`.
3. Executar o bootstrap/migrations e validar `/notificacoes`.
4. Configurar o par VAPID no `.env`.
5. Instalar e iniciar `sistema-impress-notifications-worker.service`.
6. Ativar `WEB_PUSH_ENABLED=true` e reiniciar somente o worker de notificações.

Exemplo de instalação do serviço:

```bash
sudo cp deploy/systemd/sistema-impress-notifications-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-impress-notifications-worker
sudo journalctl -u sistema-impress-notifications-worker -f
```

## Cloudflare Tunnel e rede

O domínio canônico é `https://sistema.eepjd.com.br`; não há configuração de Certbot
ou terminação TLS no Nginx nesta feature. Depois do deploy, confirme:

```bash
curl -I https://sistema.eepjd.com.br/service-worker.js
```

A resposta deve ter:

- `Content-Type: application/javascript`;
- `Service-Worker-Allowed: /`;
- `Cache-Control: no-cache`.

O Tunnel não deve armazenar `/service-worker.js` em cache. O servidor também precisa
de saída HTTPS para os endpoints de push informados pelos navegadores. Falhas `429`
ou `5xx` entram em retry exponencial; `404` e `410` desativam a assinatura.

## Smoke test

- Criar uma demanda APC futura e confirmar a notificação interna do professor.
- Verificar os marcos de 72h e 24h no banco/worker.
- Ativar um dispositivo por ação explícita na página de notificações.
- Fechar a aba e enviar um lote de teste sem dados sensíveis.
- Clicar no push e confirmar a abertura do destino interno correto.
- Fazer logout e confirmar a desativação do dispositivo.
