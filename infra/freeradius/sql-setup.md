# FreeRADIUS SQL Setup (PEAP/MSCHAPv2 + NT-Password)

## Premissas
- Login do Wi-Fi usa `email` do usuário do sistema.
- A VIEW `radcheck` já existe no banco da aplicação.
- FreeRADIUS vai ler somente credenciais (`username`, `NT-Password`).
- Neste repositório atual, a aplicação usa SQLite (`DB_PATH`); para produção com FreeRADIUS, o caminho recomendado é PostgreSQL ou MySQL/MariaDB.

## 1) Instalar módulos SQL

PostgreSQL:
```bash
sudo apt update
sudo apt install -y freeradius freeradius-postgresql
```

MySQL/MariaDB:
```bash
sudo apt update
sudo apt install -y freeradius freeradius-mysql
```

## 2) Habilitar módulo SQL

```bash
sudo ln -sf /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/sql
```

## 3) Configurar `/etc/freeradius/3.0/mods-enabled/sql`

- Defina `driver` e `dialect` corretos (`rlm_sql_postgresql` ou `rlm_sql_mysql`).
- Configure servidor, banco, usuário e senha do usuário somente leitura (`radius_ro`).
- Garanta que a query de `radcheck` leia da view `radcheck`.

## 4) Ajustar `inner-tunnel`

Use o snippet de [inner-tunnel.snippet](/Users/lucassbaraini/sistema-impress/infra/freeradius/inner-tunnel.snippet):
- adicionar `sql` em `authorize { ... }`
- manter `mschap` em `authenticate { ... }`

## 5) Reiniciar e testar

```bash
sudo systemctl restart freeradius
sudo freeradius -X
```

No modo debug, confirme que o usuário foi encontrado em `radcheck` e que existe `NT-Password`.
