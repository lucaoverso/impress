# ARCHITECTURE.md

## Visão geral

Este documento define a arquitetura alvo do projeto.

O sistema deve seguir uma arquitetura modular por domínio, com camadas internas bem definidas. A ideia é organizar o código de forma que cada funcionalidade principal fique em seu próprio módulo, mantendo perto os arquivos que mudam pelo mesmo motivo.

O objetivo da arquitetura é:

- facilitar manutenção;
- reduzir acoplamento;
- evitar arquivos gigantes;
- separar regra de negócio de rotas, templates e banco;
- permitir refatoração gradual;
- tornar o projeto mais previsível para humanos e agentes de código.

---

## Tecnologias principais

O projeto utiliza:

- FastAPI;
- SQLite;
- Jinja2/templates;
- HTML, CSS e JavaScript;
- CUPS ou serviços externos quando aplicável ao módulo de impressão;
- autenticação baseada em sessão, token ou mecanismo já existente no projeto.

A arquitetura não exige troca de tecnologia. O objetivo inicial é organizar o código existente.

---

## Estrutura geral

Estrutura alvo:

```text
app/
  main.py

  core/
    config.py
    database.py
    security.py
    exceptions.py

  shared/
    dependencies.py
    utils.py
    constants.py
    pagination.py

  modules/
    auth/
      router.py
      service.py
      repository.py
      schemas.py
      models.py

    users/
      router.py
      service.py
      repository.py
      schemas.py
      models.py

    printing/
      router.py
      service.py
      repository.py
      schemas.py
      models.py

    scheduling/
      router.py
      service.py
      repository.py
      schemas.py
      models.py

    resources/
      router.py
      service.py
      repository.py
      schemas.py
      models.py

    reports/
      router.py
      service.py
      repository.py
      schemas.py

  templates/
    base.html
    auth/
    users/
    printing/
    scheduling/
    resources/
    reports/
    admin/

  static/
    css/
    js/
    img/

  db/
    schema.sql
    migrations/
```

A estrutura pode ser adaptada conforme a realidade atual do projeto, mas o padrão modular deve ser preservado.

---

## Filosofia da arquitetura

A arquitetura segue o princípio:

> Tudo que muda pelo mesmo motivo deve ficar perto.

Isso significa que uma alteração sobre impressão deve acontecer principalmente dentro de:

```text
modules/printing/
```

Uma alteração sobre agendamento deve acontecer principalmente dentro de:

```text
modules/scheduling/
```

Uma alteração sobre usuários deve acontecer principalmente dentro de:

```text
modules/users/
```

O objetivo é evitar que uma mudança pequena exija procurar lógica espalhada pelo projeto inteiro.

---

## Camadas internas de cada módulo

Cada módulo pode conter os seguintes arquivos:

```text
router.py
service.py
repository.py
schemas.py
models.py
```

Nem todo módulo precisa obrigatoriamente de todos os arquivos desde o início. Porém, quando a responsabilidade existir, ela deve ficar no arquivo correto.

---

## `router.py`

Camada responsável pela entrada HTTP.

Responsabilidades:

- declarar endpoints;
- receber requisições;
- aplicar dependências;
- lidar com autenticação/autorização no nível da rota;
- chamar serviços;
- retornar JSON, redirects ou templates.

Exemplo conceitual:

```python
@router.post("/resources")
def create_resource(data: ResourceCreate):
    return resource_service.create_resource(data)
```

O `router.py` não deve conter:

- SQL;
- regra complexa de negócio;
- cálculos de domínio;
- manipulação direta do banco;
- lógica que deveria estar no service.

---

## `service.py`

Camada responsável pelas regras de negócio.

Responsabilidades:

- validar regras do domínio;
- coordenar operações;
- chamar repositories;
- aplicar permissões de domínio;
- transformar decisões de negócio em ações;
- centralizar lógica importante do módulo.

Exemplos:

- calcular cota de impressão;
- verificar conflito de agendamento;
- validar se um recurso está disponível;
- cancelar solicitação;
- verificar se usuário pode executar determinada ação.

O `service.py` não deve conter:

- SQL direto;
- renderização de templates;
- detalhes de HTTP sem necessidade;
- código visual;
- dependência forte de JavaScript ou HTML.

---

## `repository.py`

Camada responsável pelo acesso a dados.

Responsabilidades:

- executar consultas SQL;
- buscar registros;
- inserir dados;
- atualizar dados;
- excluir dados;
- encapsular detalhes do banco.

Exemplo conceitual:

```python
def get_resource_by_id(resource_id: int):
    query = "SELECT * FROM resources WHERE id = ?"
    return db.fetch_one(query, (resource_id,))
```

O `repository.py` não deve conter:

- regra de negócio;
- decisão de permissão;
- lógica de template;
- dependência de `Request` ou `Response`;
- chamadas HTTP.

---

## `schemas.py`

Camada responsável pelos contratos de dados.

Responsabilidades:

- validar entrada;
- definir estruturas de saída;
- organizar modelos Pydantic;
- documentar os dados esperados pelo módulo.

Exemplo conceitual:

```python
class ResourceCreate(BaseModel):
    name: str
    type: str
    active: bool = True
```

---

## `models.py`

Camada responsável por representar entidades do domínio.

Pode conter:

- dataclasses;
- enums;
- estruturas auxiliares;
- modelos ORM, caso o projeto passe a usar ORM no futuro;
- documentação de entidades relacionadas ao banco.

Se o projeto usar SQLite puro, este arquivo pode ser simples ou inexistente em módulos pequenos.

---

## `core/`

A pasta `core/` contém elementos centrais do sistema.

Exemplos:

```text
core/
  config.py
  database.py
  security.py
  exceptions.py
```

Responsabilidades:

- configuração global;
- conexão com banco;
- funções centrais de segurança;
- exceções base;
- inicialização de recursos globais.

O `core/` não deve virar uma pasta onde qualquer regra de negócio é colocada.

---

## `shared/`

A pasta `shared/` contém recursos compartilhados entre módulos.

Exemplos:

```text
shared/
  dependencies.py
  utils.py
  constants.py
  pagination.py
```

Use `shared/` com cuidado.

Não coloque regra de negócio específica em `shared/`.

Se uma função pertence ao domínio de impressão, ela deve ficar em `modules/printing`.

Se pertence ao domínio de agendamento, ela deve ficar em `modules/scheduling`.

---

## `templates/`

A pasta `templates/` contém arquivos HTML renderizados pelo backend.

Responsabilidades dos templates:

- exibir dados;
- organizar interface visual;
- usar condicionais simples de apresentação;
- reaproveitar layouts base.

Templates não devem conter:

- regra de negócio;
- cálculo crítico;
- decisão de permissão real;
- lógica de banco;
- regras importantes escondidas no HTML.

Permissões e regras devem ser decididas no backend, especialmente em `service.py`.

---

## `static/`

A pasta `static/` contém arquivos estáticos.

Exemplos:

```text
static/
  css/
  js/
  img/
```

O JavaScript pode cuidar de:

- interações de tela;
- requisições assíncronas;
- máscaras de formulário;
- feedback visual;
- atualização dinâmica de componentes.

O JavaScript não deve ser responsável por:

- regra crítica de negócio;
- autorização real;
- cálculo definitivo de cota;
- validação final de permissões;
- segurança.

Tudo que for crítico deve ser validado no backend.

---

## `db/`

A pasta `db/` contém elementos relacionados à estrutura do banco.

Exemplos:

```text
db/
  schema.sql
  migrations/
    001_create_users.sql
    002_create_resources.sql
    003_create_scheduling.sql
```

A conexão com o banco deve ficar em:

```text
core/database.py
```

As consultas específicas devem ficar nos repositories dos módulos.

---

## Fluxo padrão de uma requisição

O fluxo ideal é:

```text
requisição HTTP
    ↓
router.py
    ↓
service.py
    ↓
repository.py
    ↓
core/database.py
    ↓
SQLite
```

Na volta:

```text
SQLite
    ↓
repository.py
    ↓
service.py
    ↓
router.py
    ↓
resposta HTTP ou template
```

---

## Exemplo prático: agendamento

Uma criação de agendamento deve seguir este fluxo:

```text
scheduling/router.py
  recebe a requisição

scheduling/service.py
  valida regras:
  - data válida;
  - recurso existente;
  - usuário permitido;
  - ausência de conflito de horário

scheduling/repository.py
  consulta e grava no banco

core/database.py
  fornece conexão
```

O template apenas mostra a tela.

O JavaScript pode melhorar a experiência, mas a validação final deve ocorrer no backend.

---

## Exemplo prático: impressão

Uma solicitação de impressão deve seguir este fluxo:

```text
printing/router.py
  recebe upload e opções de impressão

printing/service.py
  valida:
  - arquivo válido;
  - usuário permitido;
  - quantidade de páginas;
  - cota disponível;
  - opções de impressão

printing/repository.py
  registra solicitação e atualiza estado no banco

worker ou serviço externo
  processa a fila de impressão
```

A regra de cota pertence ao módulo de impressão.

Ela não deve ficar no template, no JavaScript ou em rotas genéricas.

---

## Sobre módulo `admin`

O módulo `admin` deve ser tratado com cuidado.

Administração geralmente é uma interface sobre vários módulos, não necessariamente um domínio isolado.

Exemplo:

- admin cancela impressão;
- admin gerencia usuários;
- admin vê relatórios;
- admin edita recursos.

Nesses casos, a regra deve continuar no módulo dono do domínio.

Exemplo:

```text
admin/router.py chama printing/service.py
admin/router.py chama users/service.py
admin/router.py chama resources/service.py
```

Evite duplicar regras em `admin`.

---

## Nomenclatura

Preferir nomes em inglês para arquivos, pastas, funções e módulos.

Exemplos:

```text
printing
scheduling
resources
users
reports
auth
```

Evitar misturar português e inglês no código.

Se o projeto já estiver em português, a migração para inglês pode ser feita gradualmente, sem quebrar rotas ou funcionalidades.

---

## Tamanho dos arquivos

Régua recomendada:

```text
até 150 linhas       saudável
150 a 300 linhas    aceitável
acima de 300 linhas revisar divisão
acima de 500 linhas provável arquivo com responsabilidade demais
```

Arquivos com mais de 300 linhas devem ser revisados.

Perguntas úteis:

- este arquivo tem mais de uma responsabilidade?
- parte dele pertence a outro módulo?
- parte dele deveria estar em service?
- parte dele deveria estar em repository?
- há funções grandes demais?
- há código duplicado?

---

## Tamanho das funções

Régua recomendada:

```text
até 30 linhas     saudável
30 a 60 linhas    revisar
acima de 60 linhas provável necessidade de quebrar
```

Funções devem ter uma ação principal clara.

Evite funções que:

- validam;
- consultam banco;
- calculam;
- renderizam;
- enviam resposta;
- atualizam múltiplos estados;

tudo ao mesmo tempo.

---

## Estratégia de refatoração gradual

A refatoração deve ser feita em pequenas etapas.

Ordem recomendada:

```text
1. resources
2. scheduling
3. reports
4. users
5. auth
6. printing
```

Motivo:

- começar por módulos menores reduz risco;
- módulos críticos devem ficar para depois;
- o padrão fica mais maduro antes de mexer nas áreas sensíveis.

---

## Checklist de refatoração de módulo

Antes:

```text
- identificar arquivos atuais do módulo;
- listar rotas existentes;
- localizar regras de negócio;
- localizar SQL;
- localizar dependências de templates;
- entender comportamento atual.
```

Durante:

```text
- criar ou ajustar router.py;
- mover regras para service.py;
- mover SQL para repository.py;
- criar schemas quando necessário;
- manter rotas públicas;
- preservar comportamento;
- evitar mexer em outros módulos.
```

Depois:

```text
- executar o sistema;
- testar tela principal do módulo;
- testar criação;
- testar listagem;
- testar edição, se existir;
- testar exclusão/cancelamento, se existir;
- testar permissões;
- conferir logs;
- revisar arquivos acima de 300 linhas.
```

---

## Critérios de qualidade

Um módulo está saudável quando:

- é fácil encontrar a regra principal;
- a rota não conhece detalhes do banco;
- o repository não conhece regra de negócio;
- o service concentra decisões;
- templates apenas exibem;
- arquivos têm tamanho razoável;
- funções têm nomes claros;
- não há duplicação evidente;
- alterar uma funcionalidade não exige mexer em muitos lugares sem motivo.

---

## Decisões importantes

### Usar arquitetura modular por domínio

Decisão:

```text
modules/nome_do_modulo/
```

Motivo:

- o sistema cresce por áreas funcionais;
- facilita manutenção;
- combina com evolução gradual;
- reduz a busca por arquivos espalhados.

---

### Manter conexão de banco centralizada

Decisão:

```text
core/database.py
```

Motivo:

- evita múltiplas formas de conectar ao SQLite;
- reduz inconsistências;
- facilita manutenção.

---

### Manter queries nos repositories

Decisão:

```text
modules/*/repository.py
```

Motivo:

- evita SQL espalhado;
- facilita troca futura de persistência;
- melhora legibilidade das rotas e services.

---

### Não colocar regra crítica no frontend

Decisão:

```text
validação final sempre no backend
```

Motivo:

- JavaScript pode ser alterado no navegador;
- segurança precisa estar no servidor;
- evita comportamento inconsistente.

---

## Princípio final

A arquitetura deve servir ao projeto, não o contrário.

O objetivo não é criar pastas bonitas. O objetivo é tornar o sistema mais fácil de entender, alterar, testar e evoluir.

Regra principal:

> Se uma pessoa nova abrir o projeto, ela deve conseguir descobrir onde mexer sem precisar adivinhar.
