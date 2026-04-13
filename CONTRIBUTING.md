# Contribuindo

## Ambiente local

O projeto usa Python `3.13`.

Crie um ambiente virtual e instale as dependências:

```bash
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
make install-dev
```

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
