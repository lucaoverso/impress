# AGENTS.md

## Objetivo deste arquivo

Este arquivo orienta agentes de código, como Codex, ChatGPT ou ferramentas similares, sobre como trabalhar neste projeto sem quebrar funcionalidades existentes e sem criar novos padrões desorganizados.

Antes de qualquer alteração, leia também:

- `ARCHITECTURE.md`

Este projeto está em processo de refatoração gradual. A prioridade é preservar o comportamento atual, reduzir acoplamento e organizar o código em uma arquitetura modular por domínio.

---

## Contexto do projeto

O sistema é uma aplicação web escolar construída com:

- FastAPI no backend;
- SQLite como banco de dados;
- Jinja2/templates para renderização de páginas;
- arquivos estáticos em `static/`;
- módulos como impressão, agendamento, recursos, usuários, autenticação e relatórios.

O sistema já possui funcionalidades em uso real. Portanto, mudanças devem ser pequenas, controladas e revisáveis.

---

## Arquitetura alvo

A arquitetura alvo é modular por domínio.

Estrutura geral esperada:

```text
app/
  core/
  shared/
  modules/
    nome_do_modulo/
      router.py
      service.py
      repository.py
      schemas.py
      models.py
  templates/
  static/
  db/
```

Cada módulo deve representar uma área funcional do sistema, por exemplo:

```text
modules/
  auth/
  users/
  printing/
  scheduling/
  resources/
  reports/
```

---

## Responsabilidade das camadas

### `router.py`

Responsável por:

- declarar rotas HTTP;
- receber requisições;
- validar dependências de autenticação/autorização;
- chamar funções da camada `service`;
- retornar respostas, redirects ou templates.

Não deve conter:

- SQL;
- regras complexas de negócio;
- cálculos de domínio;
- lógica de acesso direto ao banco.

---

### `service.py`

Responsável por:

- concentrar regras de negócio;
- coordenar operações;
- validar regras do domínio;
- chamar repositories;
- decidir fluxos da funcionalidade.

Exemplos:

- verificar se um professor pode agendar um recurso;
- calcular consumo de cota de impressão;
- validar conflito de horários;
- cancelar uma solicitação;
- aplicar permissões de domínio.

Não deve conter:

- SQL direto;
- renderização de templates;
- manipulação de `Request`/`Response` sem necessidade;
- lógica visual ou de frontend.

---

### `repository.py`

Responsável por:

- acessar o banco de dados;
- executar consultas SQL;
- inserir, atualizar, remover e buscar dados;
- encapsular detalhes de persistência.

Não deve conter:

- regra de negócio;
- decisão de permissão;
- renderização;
- dependência de HTTP;
- acesso a templates.

---

### `schemas.py`

Responsável por:

- definir estruturas de entrada e saída;
- validar dados com Pydantic quando aplicável;
- documentar contratos de dados do módulo.

---

### `models.py`

Responsável por:

- representar entidades do domínio;
- documentar estruturas relacionadas a tabelas;
- definir dataclasses, enums ou modelos, quando necessário.

Se o projeto não usar ORM, este arquivo pode ser simples ou até não existir em módulos pequenos.

---

## Fluxo obrigatório

O fluxo padrão deve ser:

```text
router -> service -> repository -> database
```

O caminho inverso não deve acontecer.

Exemplos proibidos:

```text
repository chamando service
service renderizando template
template decidindo regra de negócio
router executando SQL
JavaScript decidindo permissão crítica
```

---

## Regras gerais de refatoração

Ao refatorar, siga estas regras:

1. Refatore apenas um módulo por vez.
2. Não altere comportamento existente sem autorização explícita.
3. Não altere nomes de rotas públicas sem autorização explícita.
4. Não altere o banco de dados sem antes propor plano de migração.
5. Não remova funcionalidades existentes.
6. Não misture refatoração com criação de funcionalidade nova.
7. Não refatore múltiplos módulos em uma única etapa.
8. Não mova arquivos sem atualizar imports.
9. Não crie padrões novos se já houver padrão definido.
10. Preserve compatibilidade com templates e JavaScript existentes.

---

## Limite de tamanho dos arquivos

Use a seguinte régua:

```text
até 150 linhas       saudável
150 a 300 linhas    aceitável
acima de 300 linhas revisar divisão
acima de 500 linhas provável arquivo com responsabilidade demais
```

Regra principal:

> Evite criar ou manter arquivos com mais de 300 linhas sem justificar.

Também observe funções grandes:

```text
até 30 linhas     saudável
30 a 60 linhas    revisar
acima de 60 linhas provável necessidade de extração
```

---

## Antes de alterar arquivos

Antes de qualquer alteração relevante, apresente um plano curto contendo:

1. módulo que será refatorado;
2. arquivos envolvidos;
3. problemas encontrados;
4. alterações propostas;
5. riscos da alteração;
6. testes manuais recomendados.

Não comece refatoração ampla sem esse plano.

---

## Durante a refatoração

Durante a alteração:

- mantenha o escopo pequeno;
- preserve o comportamento atual;
- mova lógica para a camada correta;
- mantenha nomes claros;
- prefira funções pequenas;
- evite duplicação;
- não misture responsabilidades;
- mantenha imports organizados;
- remova código morto apenas quando houver segurança.

---

## Ao finalizar uma alteração

Ao concluir uma etapa, informe:

1. arquivos alterados;
2. resumo do que mudou;
3. comportamento preservado;
4. riscos restantes;
5. testes manuais recomendados;
6. próximos passos sugeridos.

---

## Testes manuais

Quando não houver testes automatizados, sempre sugerir checklist manual.

Exemplo:

```text
- login de professor funciona;
- login de admin funciona;
- tela principal abre sem erro;
- criação do registro funciona;
- listagem aparece corretamente;
- edição funciona;
- cancelamento ou exclusão funciona;
- permissões continuam corretas;
- templates não quebraram;
- JavaScript da tela continua funcionando.
```

---

## Proibições importantes

Não faça:

- refatoração total do projeto;
- reescrita completa sem autorização;
- mudança de framework;
- troca de banco;
- alteração de rotas públicas;
- alteração de autenticação junto com outro módulo;
- alteração no módulo de impressão em produção sem plano e checklist;
- criação de abstrações complexas sem necessidade;
- criação de arquivos genéricos como `utils.py` para esconder regra de negócio;
- duplicação de lógica entre módulos.

---

## Ordem recomendada de refatoração

Preferir começar por módulos de menor risco.

Ordem sugerida:

```text
1. resources
2. scheduling
3. reports
4. users
5. auth
6. printing
```

Módulos críticos, como `auth` e `printing`, devem ser deixados para depois, quando o padrão modular já estiver mais consolidado.

---

## Critério para considerar um módulo refatorado

Um módulo pode ser considerado refatorado quando:

- possui estrutura clara;
- possui `router.py`, `service.py`, `repository.py` e `schemas.py` quando necessário;
- não possui SQL em rotas;
- não possui regra de negócio em templates;
- não possui arquivos excessivamente grandes;
- possui funções com responsabilidade clara;
- mantém comportamento anterior;
- possui checklist manual validado.

---

## Prompt padrão recomendado

Use este modelo para pedir uma refatoração:

```text
Leia AGENTS.md e ARCHITECTURE.md.

Refatore apenas o módulo [NOME_DO_MODULO].

Objetivo:
organizar o módulo seguindo a arquitetura modular:
router.py, service.py, repository.py, schemas.py e models.py quando necessário.

Restrições:
- não alterar comportamento existente;
- não alterar rotas públicas;
- não alterar banco de dados;
- não mexer em outros módulos;
- não criar arquivos com mais de 300 linhas sem justificar;
- não remover funcionalidades;
- preservar compatibilidade com templates e JavaScript existentes.

Antes de alterar arquivos:
1. liste os arquivos envolvidos;
2. explique o problema atual;
3. proponha o plano de refatoração;
4. aponte riscos;
5. aguarde aprovação.
```

---

## Princípio principal

> Tudo que muda pelo mesmo motivo deve ficar perto.

Se a mudança é sobre impressão, ela deve estar principalmente em `modules/printing`.

Se a mudança é sobre agendamento, ela deve estar principalmente em `modules/scheduling`.

Se a mudança é sobre autenticação, ela deve estar principalmente em `modules/auth`.

A arquitetura deve facilitar manutenção, não apenas criar pastas bonitas.
