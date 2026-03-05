# Troubleshooting FreeRADIUS + NT-Hash

## Executar em modo debug
```bash
sudo systemctl stop freeradius
sudo freeradius -X
```

## Capturar tráfego RADIUS
```bash
sudo tcpdump -i any port 1812
```

## Porta 1812 já em uso
Se aparecer erro de bind na 1812, existe outra instância rodando.

Verifique:
```bash
sudo ss -lpun | grep 1812
sudo lsof -i :1812
```

## Erro "No known good password"
Normalmente significa que o FreeRADIUS não encontrou credencial válida no SQL:
- `nt_hash` ausente no usuário
- usuário não retornado pela VIEW `radcheck`
- query SQL/configuração incorreta

## Conferir VIEW `radcheck`
No banco da aplicação, valide:

```sql
SELECT username, attribute, op, value
FROM radcheck
WHERE username = '<login-do-professor>';
```

Se não retornar linha, o usuário ainda não possui `nt_hash` preenchido ou login não corresponde ao identificador usado (neste projeto: `email`).
