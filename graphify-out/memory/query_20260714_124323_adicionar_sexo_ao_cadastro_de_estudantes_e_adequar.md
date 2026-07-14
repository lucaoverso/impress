---
type: "query"
date: "2026-07-14T12:43:23.586269+00:00"
question: "Adicionar sexo ao cadastro de estudantes e adequar o artigo no texto consolidado do pré-conselho"
contributor: "graphify"
outcome: "useful"
source_nodes: ["criar_estudante", "gerar_texto_consolidado_pre_conselho", "schema_migrations.py", "cadastros.js"]
---

# Q: Adicionar sexo ao cadastro de estudantes e adequar o artigo no texto consolidado do pré-conselho

## Answer

Expansão usada: estudante, estudantes, cadastro, consolidado, preconselho, migration, migrations, schema. Foi adicionada migration opcional M/F, persistência e edição no painel, propagação do sexo aos registros do pré-conselho e concordância feminina nos textos individual e consolidado. Ausência de sexo preserva o texto masculino legado. Trinta e cinco testes passaram.

## Outcome

- Signal: useful

## Source Nodes

- criar_estudante
- gerar_texto_consolidado_pre_conselho
- schema_migrations.py
- cadastros.js