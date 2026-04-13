# Sprint 0

## Objetivo

Criar uma base segura para a refatoração sem alterar comportamento funcional da aplicação.

## Escopo

- [x] Padronizar comandos de validação local
- [x] Adicionar configuração inicial de lint/format
- [x] Criar documentação mínima para contribuição
- [x] Criar workflow de CI
- [x] Fazer o deploy depender de CI bem-sucedida
- [x] Limpar artefatos indevidos do versionamento

## Entregas

- `pyproject.toml` com configuração do `ruff`
- `requirements-dev.txt` para ferramentas de desenvolvimento
- `Makefile` com comandos padrão
- `CONTRIBUTING.md`
- `.github/workflows/ci.yml`
- ajuste de `.github/workflows/deploy.yml`
- atualização do `.gitignore`

## Critérios de pronto

- Existe um comando único e documentado para teste e lint
- Existe CI automatizada para validação
- O deploy não depende mais apenas do push bruto em `main`
- O repositório deixa de versionar arquivos de sistema como `.DS_Store`
