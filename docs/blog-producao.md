# Publicação do Blog em `blog.eepjd.com.br`

## Visão geral

O Blog usa a mesma aplicação FastAPI, o mesmo banco SQLite e o mesmo Nginx da suíte.
O cabeçalho HTTP `Host` define qual interface deve responder:

- domínio principal: mantém a suíte e a página de login;
- `blog.eepjd.com.br`: publica o Blog em `/`, `/artigos/...` e `/images/...`;
- `/blog/`: permanece disponível no domínio principal apenas para teste, com `noindex`.

Não é necessário iniciar outro processo Uvicorn.

## 1. Ambiente e armazenamento

Configure `/opt/sistema-impress/.env`:

```env
BLOG_IMAGE_DIR=/opt/sistema-impress-data/blog-images
BLOG_PUBLIC_HOST=blog.eepjd.com.br
BLOG_PUBLIC_URL=https://blog.eepjd.com.br
```

Prepare o diretório persistente:

```bash
sudo mkdir -p /opt/sistema-impress-data/blog-images
sudo chown -R sistema-impress:lp /opt/sistema-impress-data/blog-images
```

As imagens não devem ficar dentro da pasta clonada do projeto. Isso evita perda dos
arquivos durante deploys e mantém os backups separados do código.

## 2. Aplicar e validar o deploy

```bash
cd /opt/sistema-impress
set -a
. ./.env
set +a
.venv/bin/python -m db.schema_migrations upgrade
sudo systemctl restart sistema-impress-api.service
sudo systemctl is-active --quiet sistema-impress-api.service
```

Valide localmente antes de publicar o DNS:

```bash
curl -I -H 'Host: blog.eepjd.com.br' http://127.0.0.1/
curl -H 'Host: blog.eepjd.com.br' http://127.0.0.1/robots.txt
curl -H 'Host: blog.eepjd.com.br' http://127.0.0.1/sitemap.xml
```

O primeiro comando deve retornar `200`. O sitemap não deve conter rascunhos nem URLs
com o prefixo `/blog`.

## 3. Publicar pelo Cloudflare Tunnel — recomendado

Esta opção é adequada quando o servidor está na escola: o `cloudflared` abre uma
conexão de saída e não exige publicar portas de entrada no roteador.

No Tunnel que já atende a aplicação, adicione uma rota de aplicação publicada:

```text
Hostname: blog.eepjd.com.br
Service:  http://localhost:80
```

Não configure `httpHostHeader`: o Host original precisa chegar ao Nginx e ao FastAPI.
Ao criar a rota pelo painel, o Cloudflare cria o registro DNS ligado ao Tunnel.

Referências oficiais:

- https://developers.cloudflare.com/tunnel/
- https://developers.cloudflare.com/tunnel/routing/
- https://developers.cloudflare.com/tunnel/setup/

## 4. Alternativa com DNS apontando ao servidor

Se o Nginx já estiver acessível publicamente, crie um registro `A`, `AAAA` ou `CNAME`:

```text
Name:         blog
Target:       mesmo destino público da suíte
Proxy status: Proxied
TTL:          Auto
```

Use esta opção apenas quando firewall, certificado do origin e portas 80/443 já
estiverem corretamente configurados. Para tráfego web, o Cloudflare recomenda manter
o registro como `Proxied`.

Referência: https://developers.cloudflare.com/dns/proxy-status/

## 5. HTTPS e cache

- Ative `Always Use HTTPS` no Cloudflare.
- Se o Cloudflare acessar diretamente um Nginx HTTPS com certificado válido, use
  `Full (strict)`.
- Não crie uma regra `Cache Everything` para todo o hostname.
- As páginas já enviam cache curto de 60 segundos.
- Imagens publicadas usam cache imutável de um ano.

Referências:

- https://developers.cloudflare.com/ssl/edge-certificates/additional-options/always-use-https/
- https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/

## 6. Verificação externa

Depois da propagação:

```bash
curl -I https://blog.eepjd.com.br/
curl -I https://blog.eepjd.com.br/artigos/slug-de-um-artigo
curl https://blog.eepjd.com.br/robots.txt
curl https://blog.eepjd.com.br/sitemap.xml
```

Confira:

- HTTPS sem redirecionamento em ciclo;
- `Content-Security-Policy`, `X-Frame-Options` e `X-Content-Type-Options` presentes;
- `Strict-Transport-Security` presente na resposta HTTPS;
- rascunhos e imagens de rascunhos retornando `404`;
- `https://blog.eepjd.com.br/blog/...` redirecionando para a URL limpa;
- domínio principal continuando a abrir a suíte normalmente.

O sitemap público pode ser cadastrado como:

```text
https://blog.eepjd.com.br/sitemap.xml
```

## 7. Backup e rollback

Inclua nos backups:

```text
/opt/sistema-impress-data/impressao.db
/opt/sistema-impress-data/blog-images/
```

Para interromper apenas a publicação pública, remova/desative a rota do Tunnel ou o
registro DNS `blog`. Não apague a tabela nem o diretório de imagens: os artigos seguem
disponíveis para edição dentro da suíte.
