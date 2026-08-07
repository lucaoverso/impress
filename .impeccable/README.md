# Integração do Impeccable

O projeto usa FastAPI com templates Jinja em `templates/` e estilos em `static/`.
Os wrappers versionados em `.github/skills/impeccable/scripts/` encaminham os
comandos para uma instalação local ou global da skill sem depender de caminhos
absolutos da máquina.

## Modo live

1. Inicie a aplicação em um terminal:

   `./run_local_api.ps1`

2. Confirme que a aplicação responde em `http://127.0.0.1:8010`.
3. Em outro terminal, inicie o Impeccable:

   `node .github/skills/impeccable/scripts/live.mjs`

O detector de contexto deste repositório reconhece a porta `8010` e as pastas
`templates/` e `static/` como código de interface.

## Dependência

A skill `impeccable` deve estar instalada em uma destas localizações:

- `.codex/skills/impeccable`;
- `.agents/skills/impeccable`;
- `$CODEX_HOME/skills/impeccable`;
- diretório global `.codex/skills/impeccable` do usuário.
