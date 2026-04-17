# Contribuindo

## Ambiente local

O projeto usa Python `3.13`.

## Rodando o app localmente

### 1. Abra o repositorio na raiz do projeto

Todos os comandos abaixo assumem que o terminal esta em `impress/`.

### 2. Garanta um Python `3.13` executavel

No Windows, evite o Python instalado pela Microsoft Store se a maquina tiver politica de Controle de Aplicativo. Nesse caso, prefira o instalador oficial do Python e use o executavel instalado fora de `WindowsApps`.

Sinal tipico desse problema:

```text
Uma politica de Controle de Aplicativo bloqueou este arquivo
```

### 3. Crie o ambiente virtual

Linux/macOS:

```bash
python3 -m venv .venv
```

Windows (PowerShell), usando um Python instalado fora de `WindowsApps`:

```powershell
C:\Users\<usuario>\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
```

### 4. Instale as dependencias

Linux/macOS:

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

### 5. Opcional: ajuste variaveis de ambiente para desenvolvimento

O projeto nao carrega `.env` automaticamente durante a execucao local. Se precisar sobrescrever algum valor, exporte a variavel no terminal antes de subir a aplicacao.

PowerShell:

```powershell
$env:DB_PATH = (Join-Path (Split-Path -Parent $PWD) "sistema-impress-data\\impressao.db")
$env:SPOOL_DIR = "$PWD\\spool"
$env:ENABLE_EMBEDDED_WORKER = "0"
```

Bash:

```bash
export DB_PATH="$(cd .. && pwd)/sistema-impress-data/impressao.db"
export SPOOL_DIR="$PWD/spool"
export ENABLE_EMBEDDED_WORKER=0
```

Se nada for definido:

- o banco SQLite sera criado automaticamente em `../sistema-impress-data/impressao.db`
- o spool caira em `spool/` na raiz do projeto
- o app esperara um worker externo de impressao

### 6. Aplique bootstrap e migrations

Linux/macOS:

```bash
.venv/bin/python -m db.schema_migrations upgrade
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m db.schema_migrations upgrade
```

### 7. Suba a API

Linux/macOS:

```bash
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```

Use `python -m uvicorn` em vez de `uvicorn ...` para evitar depender diretamente do `uvicorn.exe`.

### 8. Confira se o sistema subiu

Abra no navegador:

- `http://127.0.0.1:8010/health`
- `http://127.0.0.1:8010/login-page`

Se `/health` estiver correto, a resposta esperada e um JSON com `status`, `checks.database` e `checks.migrations`.

### 9. Entre com um usuario de teste

Na primeira subida, a aplicacao garante estes usuarios basicos:

- `admin@escola` / `admin123`
- `professor@escola` / `prof123`

### 10. Opcional: rode o worker de impressao

Por padrao, a API sobe esperando um worker externo. Isso nao impede o desenvolvimento dos modulos web, login, admin, coordenacao, PCPI e pre-conselho.

Se preferir testar API + worker no mesmo processo, defina antes de subir o `uvicorn`:

PowerShell:

```powershell
$env:ENABLE_EMBEDDED_WORKER = "1"
```

Bash:

```bash
export ENABLE_EMBEDDED_WORKER=1
```

Se voce quiser rodar o worker em outro terminal:

Linux/macOS:

```bash
.venv/bin/python worker_main.py
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe worker_main.py
```

Observacao importante:

- o fluxo de impressao real depende de um comando `lp` compativel com CUPS
- em Windows sem CUPS configurado, o worker pode iniciar mas falhara ao enviar jobs reais para a impressora

### 11. Validacoes uteis durante o desenvolvimento

Linux/macOS:

```bash
.venv/bin/python -m db.schema_migrations status
.venv/bin/python -m unittest discover -s tests -q
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m db.schema_migrations status
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

### Problemas comuns

`Uma politica de Controle de Aplicativo bloqueou este arquivo`

- O Python ou o wrapper do ambiente virtual foi bloqueado.
- Reinstale o Python com o instalador oficial e recrie `.venv`.
- Depois rode `python -m uvicorn ...`, nao `uvicorn ...`.

`/health` volta com migrations pendentes

- Rode novamente `python -m db.schema_migrations upgrade`.

`Comando 'lp' nao encontrado`

- Isso e esperado fora de um ambiente com CUPS.
- Para desenvolvimento das telas e regras de negocio, voce pode seguir sem impressao real.

## Comandos padrão

Use sempre os mesmos comandos para validar mudanças antes de enviar:

```bash
make test
make lint
make check
make migrate
make migrations-status
```

Para formatar arquivos com o `ruff`:

```bash
make format
```

No Windows sem `make`, use os equivalentes abaixo com o mesmo interpretador do ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format .
.\.venv\Scripts\python.exe -m db.schema_migrations upgrade
.\.venv\Scripts\python.exe -m db.schema_migrations status
```

## Banco e migrations

O fluxo oficial de schema agora fica assim:

1. `database.criar_tabelas()` garante o bootstrap base do banco.
2. As migrations versionadas em `migrations/` sao registradas em `schema_migrations`.
3. O comando `make migrate` aplica bootstrap + migrations pendentes.
4. O comando `make migrations-status` mostra o que ja foi aplicado e o que ainda falta.

Enquanto houver legado em producao, os helpers `_garantir_colunas_*` continuam como camada de compatibilidade, mas novas evolucoes de schema devem entrar primeiro como migration versionada.

## Fluxo recomendado

1. Faça mudanças pequenas e focadas.
2. Rode `make check` antes de abrir ou atualizar um PR.
3. Evite misturar refatoração estrutural com mudança de regra de negócio na mesma entrega.

## Documentacao de arquitetura

Para entender a organizacao atual do repositorio e o padrao esperado para novas entregas, consulte:

- [docs/estrutura-projeto.md](/Users/lucassbaraini/sistema-impress/docs/estrutura-projeto.md)
- [docs/guia-novos-modulos.md](/Users/lucassbaraini/sistema-impress/docs/guia-novos-modulos.md)

## CI

O repositório agora possui uma workflow de `CI` dedicada. O deploy no servidor deve acontecer apenas depois de uma execução bem-sucedida dessa validação na branch `main`.
