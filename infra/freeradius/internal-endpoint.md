# Endpoint interno: migração silenciosa de NT-Hash

Endpoint:
- `POST /internal/radius/ensure-nt-hash`

Header obrigatório:
- `X-RADIUS-SECRET: <RADIUS_INTERNAL_SECRET>`

Body:
```json
{
  "username": "professor@escola.local",
  "password": "Senha@123"
}
```

Respostas:
- `200 {"ok": true}` quando usuário/senha são válidos (e `nt_hash` é garantido).
- `401 {"ok": false}` para usuário inexistente ou senha inválida.
- `403 {"ok": false}` para segredo ausente/incorreto.

Teste com `curl`:
```bash
curl -X POST http://127.0.0.1:8000/internal/radius/ensure-nt-hash \
  -H "Content-Type: application/json" \
  -H "X-RADIUS-SECRET: ${RADIUS_INTERNAL_SECRET}" \
  -d '{"username":"professor@escola.local","password":"Senha@123"}'
```
