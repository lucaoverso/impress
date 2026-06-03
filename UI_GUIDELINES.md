# GUIA.md — Guia de UX/UI da Suíte Escolar

## 1. Objetivo do guia

Este arquivo define os padrões de UX/UI da **Suíte Escolar**.

A Suíte Escolar é um sistema escolar com módulos como:

- Impressão;
- Agendamento de recursos;
- Administração;
- Relatórios;
- Biblioteca, futuramente;
- Outros serviços escolares que podem surgir conforme a necessidade.

O objetivo deste guia é garantir que todas as telas sigam uma mesma lógica visual e de experiência, evitando que cada módulo tenha um estilo diferente.

A interface deve ser:

- simples;
- intuitiva;
- responsiva;
- consistente;
- acessível;
- amigável para professores, coordenação e gestão;
- fácil de manter e evoluir.

A regra principal é:

> O usuário não deve precisar entender o sistema para conseguir usar o sistema.

---

## 2. Público-alvo

A interface da Suíte Escolar deve considerar três perfis principais de usuários.

### 2.1 Professor

O professor quer realizar tarefas rapidamente, normalmente entre uma aula e outra.

Exemplos de ações:

- enviar arquivo para impressão;
- consultar histórico de impressões;
- reservar projetor, STE ou outro recurso;
- consultar agendamentos;
- acessar serviços da escola.

A interface para professor deve ser direta, com linguagem simples e poucos passos.

### 2.2 Coordenação/Gestão

A coordenação e a gestão precisam acompanhar, revisar, organizar e tomar decisões.

Exemplos de ações:

- consultar fila de impressão;
- verificar histórico;
- acompanhar uso de cotas;
- gerenciar recursos;
- consultar relatórios;
- organizar solicitações.

A interface para gestão pode mostrar mais informações, mas ainda deve evitar excesso visual.

### 2.3 Administrador

O administrador configura o sistema.

Exemplos de ações:

- gerenciar usuários;
- ajustar cotas;
- gerenciar permissões;
- configurar impressoras;
- editar dados do sistema;
- consultar logs;
- resolver erros.

A interface administrativa pode ser mais técnica, mas deve continuar clara e organizada.

---

## 3. Princípios gerais de UX

## 3.1 Uma ação principal por tela

Cada tela deve deixar evidente qual é a ação principal.

Exemplos:

- Tela de impressão: enviar uma nova impressão.
- Tela de agendamento: reservar um recurso.
- Tela de histórico: consultar pedidos anteriores.
- Tela de administração: gerenciar dados.
- Tela de relatórios: analisar informações.

Evitar telas onde várias ações disputam atenção ao mesmo tempo.

### Correto

```txt
Nova impressão
Envie um arquivo, configure a impressão e confirme a solicitação.

[Selecionar arquivo]
```

### Evitar

```txt
Nova impressão + Histórico + Cota + Relatórios + Filtros + Configurações
```

---

## 3.2 Mostrar complexidade aos poucos

Nem todas as opções precisam aparecer ao mesmo tempo.

A interface deve revelar campos avançados apenas quando forem necessários.

Exemplo no módulo de impressão:

- Primeiro mostrar upload do arquivo;
- Depois professor, turma e cópias;
- Depois opções de impressão;
- Por fim resumo e confirmação.

Exemplo:

```txt
Páginas
(●) Todas as páginas
( ) Personalizar intervalo
```

O campo de intervalo só aparece se o usuário escolher "Personalizar intervalo".

---

## 3.3 Fluxos guiados para tarefas complexas

Tarefas com muitos campos devem ser divididas em etapas.

### Impressão

```txt
1. Arquivo
2. Dados
3. Impressão
4. Conferir
```

### Agendamento

```txt
1. Recurso
2. Data e horário
3. Finalidade
4. Conferir
```

### Administração

```txt
1. Localizar registro
2. Editar dados
3. Conferir alteração
4. Salvar
```

---

## 3.4 Resumo antes de ações importantes

Antes de concluir uma ação importante, mostrar um resumo.

Isso evita erros e aumenta a confiança do usuário.

Exemplos de ações que exigem resumo:

- confirmar impressão;
- confirmar agendamento;
- cancelar solicitação;
- alterar cota;
- excluir usuário;
- redefinir senha;
- alterar configuração do sistema.

Exemplo:

```txt
Resumo da impressão

Arquivo: Atividade.pdf
Professor: Ana Paula
Turma: 8º A
Cópias: 30
Páginas: Todas
Layout: 1 por folha
Frente e verso: Não
Total estimado: 180 páginas

[Confirmar impressão]
```

---

## 3.5 Linguagem simples

A linguagem do sistema deve ser próxima da realidade escolar.

Preferir termos claros.

| Evitar | Preferir |
|---|---|
| Job de impressão | Pedido de impressão |
| Submeter | Enviar |
| Requisição | Solicitação |
| Classificação | Tipo de material |
| Deletar | Excluir |
| Resource booking | Reserva de recurso |
| Dashboard | Painel |
| Input inválido | Verifique este campo |
| Operação realizada | Ação concluída |

---

## 3.6 Estados claros

Toda tela deve ter estados bem definidos:

- vazio;
- carregando;
- sucesso;
- erro;
- bloqueado;
- sem permissão;
- sem conexão, quando aplicável.

### Estado vazio

```txt
Nenhuma impressão encontrada.
Quando você enviar uma impressão, ela aparecerá aqui.
```

### Estado de carregamento

```txt
Carregando pré-visualização...
```

### Estado de erro

```txt
Não foi possível carregar o arquivo.
Tente enviar novamente ou converter o arquivo para PDF.
```

### Estado sem permissão

```txt
Você não tem permissão para acessar esta área.
Caso precise de acesso, procure a coordenação ou o administrador do sistema.
```

---

## 3.7 Prevenção de erros

A interface deve impedir erros sempre que possível.

Regras:

- desabilitar botões quando campos obrigatórios não estiverem preenchidos;
- explicar por que o botão está desabilitado;
- pedir confirmação para ações irreversíveis;
- mostrar resumo antes de concluir;
- validar campos no momento certo;
- evitar mensagens genéricas.

### Exemplo

```txt
[Confirmar impressão]

Desabilitado porque:
Selecione pelo menos um tipo de material.
```

---

## 3.8 Mobile first

Toda tela deve funcionar bem em celular.

Regras:

- evitar layout com três colunas;
- evitar tabelas largas;
- transformar tabelas em cards;
- usar botões grandes;
- evitar textos muito pequenos;
- usar modais ou telas separadas para previews grandes;
- evitar scroll horizontal;
- manter a ação principal fácil de encontrar.

No mobile, a interface deve ser vertical e guiada.

---

## 3.9 Consistência visual

Todos os módulos devem parecer parte do mesmo sistema.

Padronizar:

- cores;
- botões;
- cards;
- inputs;
- badges;
- tabelas;
- modais;
- mensagens;
- espaçamentos;
- sombras;
- títulos;
- ícones;
- textos de ajuda.

---

## 3.10 Interface como produto escolar, não painel técnico

A Suíte Escolar deve parecer um sistema feito para escola, não um painel técnico de servidor.

O usuário deve sentir que está fazendo ações escolares:

- enviar uma atividade;
- reservar uma sala;
- acompanhar uma solicitação;
- organizar recursos;
- consultar relatórios.

Evitar termos técnicos quando não forem necessários.

---

# 4. Paleta de cores

A paleta da Suíte Escolar deve transmitir:

- organização;
- confiança;
- tranquilidade;
- clareza;
- modernidade;
- ambiente educacional.

A cor principal sugerida é um **verde-petróleo**, que combina bem com o contexto escolar e passa seriedade sem parecer pesado.

---

## 4.1 Tokens de cores

```css
:root {
  /* Cores principais */
  --color-primary: #0D7A6F;
  --color-primary-hover: #0B655B;
  --color-primary-light: #E6F4F2;

  /* Fundos e superfícies */
  --color-background: #F6F8FC;
  --color-surface: #FFFFFF;
  --color-surface-muted: #F1F4F8;

  /* Bordas */
  --color-border: #E3E8EF;
  --color-border-strong: #CBD5E1;

  /* Textos */
  --color-text: #0F172A;
  --color-text-muted: #64748B;
  --color-text-soft: #94A3B8;

  /* Estados */
  --color-success: #16A34A;
  --color-success-light: #DCFCE7;

  --color-warning: #F59E0B;
  --color-warning-light: #FEF3C7;

  --color-danger: #EF4444;
  --color-danger-light: #FEE2E2;

  --color-info: #3B82F6;
  --color-info-light: #DBEAFE;
}
```

---

## 4.2 Uso das cores

### Primária

Usar em:

- botões principais;
- links importantes;
- etapa ativa;
- elementos selecionados;
- destaque positivo principal.

Exemplo:

```txt
[Confirmar impressão]
[Reservar recurso]
[Salvar alterações]
```

### Primária clara

Usar em:

- fundo de badges suaves;
- cards selecionados;
- estado ativo leve;
- destaque sem agressividade.

Exemplo:

```txt
Etapa atual no stepper
Card de recurso selecionado
```

### Fundo

Usar como fundo geral da aplicação.

```txt
Tela geral do sistema
```

### Superfície branca

Usar em:

- cards;
- formulários;
- modais;
- tabelas;
- painéis.

### Borda

Usar em:

- cards;
- inputs;
- divisórias;
- tabelas;
- botões secundários.

### Sucesso

Usar em:

- status concluído;
- ação feita com sucesso;
- confirmação positiva.

### Alerta

Usar em:

- pendências;
- avisos;
- atenção necessária;
- recursos em conflito, quando não for erro.

### Erro

Usar em:

- falhas;
- ações perigosas;
- bloqueios;
- cancelamentos;
- campos inválidos.

### Informação

Usar em:

- dicas;
- mensagens de orientação;
- informações neutras;
- avisos explicativos.

---

## 4.3 Regras de contraste

- Texto principal deve usar `--color-text`.
- Texto secundário deve usar `--color-text-muted`.
- Não usar texto cinza muito claro em fundo branco.
- Botões primários devem ter texto branco.
- Badges claros devem ter texto escuro na cor correspondente.
- Evitar usar apenas cor para transmitir status. Sempre combinar com texto.

Exemplo correto:

```txt
[✓ Concluído]
[! Pendente]
[x Cancelado]
```

---

# 5. Tipografia

## 5.1 Fonte

Usar fonte sem serifa, limpa e legível.

Sugestões:

```css
font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Se não houver Inter, usar `system-ui`.

---

## 5.2 Hierarquia tipográfica

```css
:root {
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-md: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  --font-size-2xl: 32px;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}
```

---

## 5.3 Uso recomendado

### Título da página

```css
font-size: 24px;
font-weight: 700;
color: var(--color-text);
```

Exemplo:

```txt
Nova impressão
```

### Descrição da página

```css
font-size: 14px;
font-weight: 400;
color: var(--color-text-muted);
```

Exemplo:

```txt
Envie um arquivo, confira as configurações e confirme a solicitação.
```

### Título de seção

```css
font-size: 18px;
font-weight: 700;
color: var(--color-text);
```

Exemplo:

```txt
Dados da solicitação
```

### Label de formulário

```css
font-size: 14px;
font-weight: 600;
color: var(--color-text);
```

Exemplo:

```txt
Professor solicitante
```

### Texto auxiliar

```css
font-size: 12px;
font-weight: 400;
color: var(--color-text-muted);
```

Exemplo:

```txt
Ao selecionar uma turma, o sistema pode sugerir a quantidade de cópias.
```

---

# 6. Espaçamentos

Usar espaçamentos consistentes.

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;
}
```

---

## 6.1 Regras de espaçamento

- Espaçamento interno de cards: `16px` a `24px`.
- Espaçamento entre seções: `24px` a `32px`.
- Espaçamento entre campos: `12px` a `16px`.
- Espaçamento entre título e descrição: `4px` a `8px`.
- Espaçamento entre navbar e conteúdo: `24px`.
- Evitar elementos grudados nas bordas da tela.

---

## 6.2 Largura de conteúdo

```css
.page-container {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
}
```

No mobile:

```css
.page-container {
  padding: 16px;
}
```

---

# 7. Bordas, cantos e sombras

## 7.1 Tokens

```css
:root {
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 18px;
  --radius-xl: 24px;
  --radius-pill: 999px;

  --shadow-sm: 0 2px 6px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 8px 24px rgba(15, 23, 42, 0.10);
  --shadow-lg: 0 16px 40px rgba(15, 23, 42, 0.14);
}
```

---

## 7.2 Regras

- Cards usam `--radius-lg`.
- Inputs usam `--radius-md`.
- Botões usam `--radius-md` ou `--radius-pill`.
- Badges usam `--radius-pill`.
- Modais usam `--radius-lg`.
- Sombras devem ser suaves.
- Evitar sombras escuras demais.
- Bordas devem ser sutis, mas visíveis.

---

# 8. Componentes base

A Suíte Escolar deve possuir componentes reutilizáveis.

Componentes base recomendados:

```txt
Navbar
Footer
PageHeader
SectionCard
ActionBar
Button
Input
Select
Checkbox
Radio
Badge
StatusBadge
Stepper
SummaryCard
EmptyState
LoadingState
ErrorState
ConfirmDialog
Modal
Drawer
ResponsiveTable
MobileCardList
Toast
```

---

# 9. Navbar

## 9.1 Objetivo

A Navbar deve indicar:

- nome do sistema;
- área atual;
- acesso aos serviços;
- opção de sair;
- menu mobile.

---

## 9.2 Desktop

```txt
┌──────────────────────────────────────────────────────┐
│ Suíte Escolar        Área docente     Serviços  Sair │
└──────────────────────────────────────────────────────┘
```

---

## 9.3 Mobile

```txt
┌──────────────────────────────┐
│ Suíte Escolar            ☰   │
└──────────────────────────────┘
```

Ao clicar no menu:

```txt
Serviços
Minha área
Sair
```

---

## 9.4 Regras

- A navbar deve ser limpa.
- Não colocar muitas ações no topo.
- A ação principal da tela não deve ficar apenas na navbar.
- Em mobile, usar menu compacto.
- O botão "Sair" deve ficar visível ou acessível, mas sem competir com a ação principal.

---

# 10. Footer

## 10.1 Objetivo

O Footer deve trazer informações secundárias.

Exemplo:

```txt
Suíte Escolar · Escola Estadual Padre José Daniel
```

Ou:

```txt
Suíte Escolar · Sistema interno de apoio escolar
```

---

## 10.2 Regras

- Deve ser discreto.
- Pode ser ocultado em telas mobile quando atrapalhar.
- Não deve conter ações principais.
- Pode conter versão do sistema em área administrativa.

Exemplo administrativo:

```txt
Suíte Escolar · v1.4.0 · Ambiente de produção
```

---

# 11. PageHeader

## 11.1 Objetivo

O PageHeader abre cada tela e informa claramente o que o usuário pode fazer.

Estrutura:

```txt
Título da página
Descrição curta
Ação secundária opcional
```

---

## 11.2 Exemplo

```txt
Nova impressão
Envie um arquivo, confira as configurações e confirme a solicitação.
```

---

## 11.3 Exemplo com ação

```txt
Meus pedidos
Acompanhe suas solicitações de impressão.

[ Nova impressão ]
```

---

## 11.4 Regras

- O título deve ser curto.
- A descrição deve explicar a ação da tela.
- Evitar títulos genéricos como "Painel" sem contexto.
- Usar ação secundária apenas quando fizer sentido.

---

# 12. Botões

## 12.1 Tipos de botão

### Botão primário

Uso:

- confirmar impressão;
- reservar recurso;
- salvar;
- continuar;
- criar;
- enviar.

Visual:

```css
.button-primary {
  background: var(--color-primary);
  color: #FFFFFF;
  border: 1px solid var(--color-primary);
}
```

Exemplos:

```txt
[Confirmar impressão]
[Reservar recurso]
[Salvar alterações]
[Continuar]
```

---

### Botão secundário

Uso:

- voltar;
- cancelar ação sem perigo;
- ver detalhes;
- abrir histórico;
- ação alternativa.

Visual:

```css
.button-secondary {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border-strong);
}
```

Exemplos:

```txt
[Voltar]
[Ver detalhes]
[Meus pedidos]
```

---

### Botão fantasma

Uso:

- ações leves;
- links internos;
- limpar filtros;
- abrir opções.

Visual:

```css
.button-ghost {
  background: transparent;
  color: var(--color-primary);
  border: none;
}
```

Exemplos:

```txt
Limpar filtros
Ver histórico
Alterar
```

---

### Botão perigoso

Uso:

- excluir;
- cancelar impressão;
- remover usuário;
- descartar alterações.

Visual:

```css
.button-danger {
  background: var(--color-danger);
  color: #FFFFFF;
  border: 1px solid var(--color-danger);
}
```

Exemplos:

```txt
[Cancelar impressão]
[Excluir usuário]
[Remover]
```

---

## 12.2 Tamanhos

```css
.button-sm {
  min-height: 36px;
  padding: 0 12px;
  font-size: 14px;
}

.button-md {
  min-height: 44px;
  padding: 0 16px;
  font-size: 14px;
}

.button-lg {
  min-height: 52px;
  padding: 0 24px;
  font-size: 16px;
}
```

---

## 12.3 Regras

- Cada tela deve ter apenas uma ação primária principal.
- O botão primário deve ficar próximo do final do fluxo.
- Em formulários longos, usar barra inferior de ação no mobile.
- Botão desabilitado deve indicar motivo quando possível.
- Ações perigosas devem pedir confirmação.
- Não usar botão vermelho para ações comuns.
- Não usar muitos botões lado a lado no mobile.

---

# 13. Cards

## 13.1 Card padrão

Uso:

- agrupar conteúdo;
- separar seções;
- exibir informações;
- mostrar resumos.

Estrutura:

```txt
┌────────────────────────────┐
│ Título                     │
│ Descrição opcional         │
│                            │
│ Conteúdo                   │
└────────────────────────────┘
```

CSS sugerido:

```css
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
}
```

---

## 13.2 Card de seção

Uso:

- formulários;
- blocos da tela;
- agrupamento de campos relacionados.

Exemplo:

```txt
Dados da solicitação
Informe professor, turma e quantidade de cópias.
```

---

## 13.3 Card de módulo

Uso:

- tela inicial de serviços.

Exemplo:

```txt
┌────────────────────────────┐
│ Impressão                  │
│ Envie arquivos para fila   │
│ de impressão da escola.    │
│                            │
│ [Abrir módulo]             │
└────────────────────────────┘
```

---

## 13.4 Card de resumo

Uso:

- revisão antes de concluir ações.

Exemplo:

```txt
Resumo da impressão

Arquivo: Atividade.pdf
Professor: Ana Paula
Turma: 8º A
Cópias: 30
Total estimado: 180 páginas
```

---

## 13.5 Regras

- Um card deve ter um assunto principal.
- Evitar cards com informação demais.
- Se o card ficar grande, dividir em seções.
- Cards clicáveis devem ter indicação visual.
- Cards selecionados devem usar borda primária e fundo primário claro.
- No mobile, cards devem ocupar 100% da largura.

---

# 14. Formulários

## 14.1 Labels

Todos os campos devem ter label visível.

Correto:

```txt
Professor solicitante
[Selecione o professor]
```

Evitar:

```txt
[Selecione o professor]
```

---

## 14.2 Textos de ajuda

Usar textos de ajuda quando o campo puder gerar dúvida.

Exemplo:

```txt
Turma
[8º A]

Ao selecionar uma turma, o sistema pode sugerir a quantidade de cópias.
```

---

## 14.3 Inputs

CSS sugerido:

```css
.input {
  width: 100%;
  min-height: 44px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  padding: 0 12px;
}
```

---

## 14.4 Estados de campo

### Normal

```txt
[Digite aqui]
```

### Foco

Usar borda primária.

```css
.input:focus {
  border-color: var(--color-primary);
  outline: 3px solid var(--color-primary-light);
}
```

### Erro

```txt
Este campo é obrigatório.
```

Usar borda vermelha e mensagem abaixo.

### Desabilitado

```txt
Campo desabilitado
```

Usar fundo suave e texto secundário.

---

## 14.5 Regras

- Campos obrigatórios devem ser claros.
- Não depender apenas de placeholder.
- Validar no envio e, quando possível, durante o preenchimento.
- Evitar formulários longos sem divisão.
- Em mobile, inputs devem ter altura mínima de 44px.
- Selects longos devem ter busca quando necessário.

---

# 15. Checkboxes, radios e seletores

## 15.1 Checkbox

Usar para múltiplas escolhas.

Exemplo:

```txt
[ ] Atividade
[ ] Comunicado
[ ] Lista de exercícios
```

---

## 15.2 Radio

Usar para escolha única.

Exemplo:

```txt
Páginas
(●) Todas
( ) Personalizar intervalo
```

---

## 15.3 Chips selecionáveis

Usar quando a opção for curta e visual.

Exemplo:

```txt
[1 por folha] [2 por folha] [4 por folha]
[Retrato] [Paisagem]
```

Estado selecionado:

- borda primária;
- fundo primário claro;
- texto primário.

---

# 16. Badges e StatusBadge

## 16.1 Objetivo

Badges servem para mostrar status, categorias ou pequenas informações.

---

## 16.2 Status recomendados

### Impressão

```txt
Pendente
Em impressão
Concluído
Cancelado
Erro
```

### Agendamento

```txt
Reservado
Em uso
Concluído
Cancelado
Conflito
```

### Administração

```txt
Ativo
Inativo
Bloqueado
Administrador
Professor
Gestão
```

---

## 16.3 Cores

```txt
Concluído / Ativo / Sucesso:
fundo success-light, texto success

Pendente / Atenção:
fundo warning-light, texto warning

Erro / Cancelado / Bloqueado:
fundo danger-light, texto danger

Informação / Em uso:
fundo info-light, texto info

Neutro:
fundo surface-muted, texto text-muted
```

---

## 16.4 Regras

- Badge deve ter texto curto.
- Não usar só cor.
- Usar ícone simples quando ajudar.
- Evitar badge grande demais.

Exemplo:

```txt
[✓ Concluído]
[! Pendente]
[x Cancelado]
[i Informação]
```

---

# 17. Stepper

## 17.1 Objetivo

O Stepper mostra o progresso em fluxos guiados.

Exemplo:

```txt
[1 Arquivo] ─ [2 Dados] ─ [3 Impressão] ─ [4 Conferir]
```

---

## 17.2 Estados

### Etapa atual

- círculo primário;
- texto primário;
- card ou borda destacada.

### Etapa concluída

- ícone de check;
- aparência discreta.

### Etapa futura

- cinza;
- sem destaque.

---

## 17.3 Regras

- Permitir voltar para etapas anteriores.
- Evitar avançar sem preencher campos obrigatórios.
- Não permitir pular etapas dependentes.
- Em mobile, stepper pode ser compacto.

Mobile:

```txt
Etapa 2 de 4
Dados da solicitação
```

Ou:

```txt
1 ✓  2 ●  3 ○  4 ○
```

---

# 18. SummaryCard

## 18.1 Objetivo

O SummaryCard mostra um resumo antes da conclusão.

---

## 18.2 Exemplo impressão

```txt
Resumo da impressão

Arquivo: Atividade.pdf
Professor: Ana Paula
Turma: 8º A
Cópias: 30
Páginas: Todas
Layout: 1 por folha
Orientação: Retrato
Frente e verso: Não
Total estimado: 180 páginas
```

---

## 18.3 Exemplo agendamento

```txt
Resumo da reserva

Recurso: Projetor HDMI 01
Data: 12/06/2026
Horário: 2ª aula
Responsável: Prof. Maria
Turma: 7º B
Finalidade: Aula com slides
```

---

## 18.4 Regras

- Deve aparecer antes de confirmar.
- Deve usar linguagem clara.
- Deve destacar o total ou consequência principal.
- Deve permitir voltar para corrigir.
- Não deve esconder dados importantes.

---

# 19. EmptyState

## 19.1 Objetivo

Mostrar uma mensagem útil quando não houver dados.

---

## 19.2 Exemplos

### Sem impressões

```txt
Nenhuma impressão encontrada.
Quando você enviar uma impressão, ela aparecerá aqui.

[Nova impressão]
```

### Sem agendamentos

```txt
Nenhum agendamento para este dia.
Escolha outro dia ou reserve um recurso.

[Reservar recurso]
```

### Sem resultados no filtro

```txt
Nenhum resultado encontrado.
Tente alterar os filtros ou limpar a busca.

[Limpar filtros]
```

---

## 19.3 Regras

- Explicar o que aconteceu.
- Orientar o próximo passo.
- Usar botão quando houver ação clara.
- Evitar mensagens frias como "Sem dados".

---

# 20. LoadingState

## 20.1 Objetivo

Indicar que o sistema está trabalhando.

---

## 20.2 Exemplos

```txt
Carregando...
```

```txt
Carregando pré-visualização...
```

```txt
Enviando arquivo...
```

```txt
Buscando agendamentos...
```

---

## 20.3 Regras

- Usar skeleton quando o layout for conhecido.
- Usar spinner apenas para carregamentos curtos.
- Informar ações demoradas.
- Evitar tela totalmente branca.

---

# 21. ErrorState

## 21.1 Objetivo

Mostrar erros de forma clara e recuperável.

---

## 21.2 Exemplos

### Erro de upload

```txt
Não foi possível enviar o arquivo.
Verifique se o arquivo está em PDF, DOCX, PNG ou JPG e tente novamente.
```

### Erro de preview

```txt
Não foi possível gerar a pré-visualização.
Você ainda pode tentar enviar novamente ou converter o arquivo para PDF.
```

### Erro de rede

```txt
Não foi possível conectar ao servidor.
Verifique sua conexão e tente novamente.
```

---

## 21.3 Regras

- Explicar o problema.
- Dizer o que o usuário pode fazer.
- Evitar mensagens técnicas.
- Logs técnicos devem ficar no backend/admin, não para o usuário comum.

Evitar:

```txt
Error 500: Internal Server Error
```

Preferir:

```txt
Não foi possível concluir a ação.
Tente novamente em alguns instantes.
```

---

# 22. Modal

## 22.1 Objetivo

Modais devem ser usados para:

- confirmações;
- alertas importantes;
- preview em tela cheia;
- formulários curtos;
- detalhes rápidos.

---

## 22.2 Modal de confirmação

```txt
Cancelar impressão?

Você está prestes a cancelar a impressão "Atividade.pdf".
Essa ação não poderá ser desfeita se a impressão já tiver iniciado.

[Voltar] [Cancelar impressão]
```

---

## 22.3 Regras

- Modal deve ter título claro.
- Ação perigosa deve ficar em botão perigoso.
- Sempre ter opção de voltar/cancelar.
- Não usar modal para tudo.
- Em mobile, modal pode ocupar quase a tela toda.

---

# 23. Drawer

## 23.1 Objetivo

Drawer é uma lateral deslizante usada para informações secundárias.

Usos recomendados:

- histórico rápido;
- detalhes de pedido;
- filtros;
- lista de recursos;
- notificações.

---

## 23.2 Exemplo

```txt
Meus pedidos

Atividade.pdf
Concluído
8º A · 30 cópias

Comunicado.png
Pendente
Gestão · 1 cópia
```

---

## 23.3 Regras

- Não colocar ação principal dentro do drawer.
- Drawer deve ser fácil de fechar.
- Em mobile, pode virar tela cheia.
- Não usar drawer para fluxos longos.

---

# 24. Toasts e mensagens rápidas

## 24.1 Objetivo

Toasts mostram feedback rápido depois de uma ação.

---

## 24.2 Exemplos

```txt
Impressão enviada com sucesso.
```

```txt
Agendamento criado com sucesso.
```

```txt
Alterações salvas.
```

```txt
Não foi possível concluir a ação.
```

---

## 24.3 Regras

- Toast deve ser curto.
- Não usar toast para informações críticas.
- Erros importantes devem aparecer também na tela.
- Toast não deve sumir rápido demais se tiver informação relevante.

---

# 25. Tabelas e listas

## 25.1 Desktop

No desktop, tabelas são úteis para dados administrativos.

Exemplo:

```txt
Data | Professor | Turma | Arquivo | Status | Ações
```

---

## 25.2 Mobile

No mobile, tabelas devem virar cards.

Exemplo:

```txt
┌────────────────────────────┐
│ Atividade.pdf              │
│ Professor: Ana Paula       │
│ Turma: 8º A                │
│ Status: Concluído          │
│                            │
│ [Ver detalhes]             │
└────────────────────────────┘
```

---

## 25.3 Regras

- Evitar scroll horizontal.
- Usar filtros claros.
- Mostrar poucas colunas por vez.
- Colunas menos importantes podem ir para detalhes.
- Ações perigosas devem pedir confirmação.
- Em tabelas administrativas, permitir busca e filtros.

---

# 26. Filtros

## 26.1 Objetivo

Filtros ajudam a encontrar informações sem poluir a tela.

---

## 26.2 Exemplo

```txt
Buscar
[Digite professor, turma ou arquivo]

Status
[Todos v]

Período
[Este mês v]

[Filtrar] [Limpar]
```

---

## 26.3 Mobile

No mobile, filtros podem ficar recolhidos.

```txt
[Mostrar filtros]
```

Ou em drawer:

```txt
Filtros
Status
Período
Professor
Turma
```

---

## 26.4 Regras

- Não mostrar filtros avançados sempre abertos no mobile.
- Botão "Limpar filtros" deve ser fácil de encontrar.
- Mostrar quando há filtro ativo.

Exemplo:

```txt
Filtros ativos: Status pendente · 8º A
[Limpar]
```

---

# 27. Layout responsivo

## 27.1 Breakpoints sugeridos

```css
:root {
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
}
```

---

## 27.2 Desktop

Pode usar:

- duas colunas;
- preview lateral;
- tabela;
- painel de resumo;
- drawer lateral.

Exemplo:

```txt
┌───────────────────────┬───────────────────────┐
│ Formulário            │ Pré-visualização       │
└───────────────────────┴───────────────────────┘
```

---

## 27.3 Tablet

Usar duas colunas apenas quando houver espaço suficiente.

Se ficar apertado, empilhar:

```txt
Formulário
Preview
Resumo
```

---

## 27.4 Mobile

Usar uma coluna.

```txt
Navbar
PageHeader
Stepper compacto
Conteúdo da etapa
Botão principal
```

Regras:

- largura total;
- cards empilhados;
- botões grandes;
- preview em modal ou tela separada;
- tabelas como cards;
- filtros recolhidos;
- evitar colunas lado a lado.

---

# 28. Acessibilidade básica

## 28.1 Regras gerais

- Todos os inputs devem ter label.
- Botões devem ter texto claro.
- Ícones importantes devem ter texto ou `aria-label`.
- Não usar apenas cor para indicar status.
- Garantir contraste suficiente.
- Foco de teclado deve ser visível.
- Modais devem poder ser fechados com Esc.
- Elementos clicáveis devem ter tamanho mínimo confortável.

---

## 28.2 Tamanho mínimo de toque

No mobile:

```css
min-height: 44px;
min-width: 44px;
```

---

## 28.3 Foco

```css
:focus-visible {
  outline: 3px solid var(--color-primary-light);
  outline-offset: 2px;
}
```

---

# 29. Ícones

## 29.1 Uso

Ícones devem apoiar a leitura, não substituir texto importante.

Exemplos:

```txt
🖨 Confirmar impressão
📅 Reservar recurso
✓ Concluído
! Pendente
x Cancelado
```

---

## 29.2 Regras

- Ícones devem ser consistentes.
- Evitar misturar estilos diferentes.
- Usar ícone + texto em ações principais.
- Em botões pequenos, garantir `aria-label`.

---

# 30. Padrões por módulo

# 30.1 Módulo de Impressão

## Objetivo

Permitir que professores, coordenação e gestão enviem arquivos para impressão de forma clara, segura e rastreável.

---

## Fluxo padrão

```txt
1. Arquivo
2. Dados
3. Impressão
4. Conferir
```

---

## Etapa 1 — Arquivo

Objetivo:

- selecionar arquivo;
- enviar ou preparar pré-visualização;
- validar formato.

Campos/componentes:

- FileUploadCard;
- formatos aceitos;
- estado de upload;
- erro de arquivo inválido.

Wireframe:

```txt
Nova impressão
Envie, confira e confirme sua solicitação de impressão.

[1 Arquivo] ─ [2 Dados] ─ [3 Impressão] ─ [4 Conferir]

┌──────────────────────────────┬───────────────────────────────┐
│ Etapa 1: Escolha o arquivo   │ Pré-visualização              │
│                              │                               │
│ Envie o material que deseja  │ ┌───────────────────────────┐ │
│ imprimir.                    │ │                           │ │
│                              │ │   Selecione um arquivo     │ │
│ ┌──────────────────────────┐ │ │   para visualizar aqui.    │ │
│ │ Arraste o arquivo aqui   │ │ │                           │ │
│ │ ou                       │ │ └───────────────────────────┘ │
│ │ [Selecionar arquivo]     │ │                               │
│ └──────────────────────────┘ │                               │
│                              │                               │
│ Formatos aceitos:            │                               │
│ PDF, DOCX, PNG, JPG, JPEG    │                               │
│                              │                               │
│                    [Continuar]│                              │
└──────────────────────────────┴───────────────────────────────┘
```

---

## Etapa 2 — Dados

Objetivo:

- informar responsável;
- selecionar turma;
- definir cópias.

Campos:

- professor solicitante;
- turma;
- cópias.

Wireframe:

```txt
[1 Arquivo] ─ [2 Dados] ─ [3 Impressão] ─ [4 Conferir]
    ✓             ●              ○              ○

┌──────────────────────────────┬───────────────────────────────┐
│ Etapa 2: Dados da solicitação│ Pré-visualização              │
│                              │                               │
│ Informe para quem esta       │ ┌───────────────────────────┐ │
│ impressão será registrada.   │ │                           │ │
│                              │ │        Página 1            │ │
│ Professor solicitante        │ │                           │ │
│ [Selecione o professor  v]   │ └───────────────────────────┘ │
│                              │                               │
│ Turma                        │ Página 1 de 6                 │
│ [Selecione a turma       v]  │ [1] [2] [3] [4] [5] [6]       │
│                              │                               │
│ Cópias                       │                               │
│ [ 30 ]                       │                               │
│                              │                               │
│ [Voltar]          [Continuar]│                               │
└──────────────────────────────┴───────────────────────────────┘
```

---

## Etapa 3 — Impressão

Objetivo:

- configurar como o arquivo sairá na folha.

Campos:

- páginas;
- intervalo personalizado;
- layout;
- orientação;
- frente e verso.

Wireframe:

```txt
[1 Arquivo] ─ [2 Dados] ─ [3 Impressão] ─ [4 Conferir]
    ✓             ✓              ●              ○

┌──────────────────────────────┬───────────────────────────────┐
│ Etapa 3: Configurar impressão│ Pré-visualização              │
│                              │                               │
│ Escolha como o arquivo deve  │ ┌───────────────────────────┐ │
│ sair na folha.               │ │                           │ │
│                              │ │        Página 1            │ │
│ Páginas                      │ │                           │ │
│ (●) Todas as páginas         │ └───────────────────────────┘ │
│ ( ) Personalizar intervalo   │                               │
│     [Ex: 1-5, 8, 10-14]      │ Página 1 de 6                 │
│                              │ [1] [2] [3] [4] [5] [6]       │
│ Layout                       │                               │
│ [1 por folha] [2 por folha]  │                               │
│ [4 por folha]                │                               │
│                              │                               │
│ Orientação                   │                               │
│ [Retrato] [Paisagem]         │                               │
│                              │                               │
│ [ ] Frente e verso           │                               │
│                              │                               │
│ [Voltar]          [Continuar]│                               │
└──────────────────────────────┴───────────────────────────────┘
```

---

## Etapa 4 — Conferir

Objetivo:

- revisar dados;
- selecionar tipo de material;
- confirmar impressão.

Campos/componentes:

- resumo;
- tipo de material;
- confirmação.

Wireframe:

```txt
[1 Arquivo] ─ [2 Dados] ─ [3 Impressão] ─ [4 Conferir]
    ✓             ✓              ✓              ●

┌──────────────────────────────┬───────────────────────────────┐
│ Etapa 4: Conferir solicitação│ Pré-visualização              │
│                              │                               │
│ Revise os dados antes de     │ ┌───────────────────────────┐ │
│ enviar para impressão.       │ │                           │ │
│                              │ │        Página 1            │ │
│ ┌──────────────────────────┐ │ │                           │ │
│ │ Resumo da impressão      │ │ └───────────────────────────┘ │
│ │                          │ │                               │
│ │ Arquivo: Atividade.pdf   │ │ Página 1 de 6                 │
│ │ Professor: Ana Paula     │ │ [1] [2] [3] [4] [5] [6]       │
│ │ Turma: 8º A              │ │                               │
│ │ Cópias: 30               │ │                               │
│ │ Páginas: Todas           │ │                               │
│ │ Layout: 1 por folha      │ │                               │
│ │ Orientação: Retrato      │ │                               │
│ │ Frente e verso: Não      │ │                               │
│ │ Total: 180 páginas       │ │                               │
│ └──────────────────────────┘ │                               │
│                              │                               │
│ Tipo de material             │                               │
│ [Atividade] [Lista] [Prova]  │                               │
│ [Comunicado] [Simulado]      │                               │
│                              │                               │
│ [Voltar] [Confirmar impressão]                              │
└──────────────────────────────┴───────────────────────────────┘
```

---

## Componentes do módulo de impressão

```txt
PrintPage
PrintStepper
FileUploadCard
PrintRequestForm
PrintSettingsForm
PrintPreview
PrintThumbnailList
PrintSummaryCard
MaterialTypeSelector
PrintHistoryDrawer
PrintStatusBadge
```

---

## Regras específicas

- O botão "Confirmar impressão" só aparece ou só fica ativo na etapa final.
- O botão "Continuar" deve validar a etapa atual.
- O preview só deve ocupar área grande depois de existir arquivo.
- No mobile, o preview deve abrir em modal ou tela separada.
- Histórico não deve competir com nova impressão.
- Cota e histórico devem ficar em card secundário, drawer ou aba separada.
- Sempre mostrar total estimado antes de confirmar.
- Tags/tipo de material devem ser obrigatórias se a regra de negócio exigir.
- O termo preferido é "Confirmar impressão", não apenas "Imprimir".

---

# 30.2 Módulo de Agendamento

## Objetivo

Permitir reservar recursos escolares de forma clara e evitar conflitos.

Recursos possíveis:

- STE;
- projetor;
- caixa de som;
- microfone;
- notebook;
- outros recursos.

---

## Fluxo padrão

```txt
1. Recurso
2. Data e horário
3. Finalidade
4. Conferir
```

---

## Etapa 1 — Recurso

```txt
Escolha o recurso

[STE]
[Projetor HDMI 01]
[Projetor HDMI 02]
[Caixa de som]
[Microfone]
```

---

## Etapa 2 — Data e horário

```txt
Data
[12/06/2026]

Horário
[1ª aula] [2ª aula] [3ª aula]
[4ª aula] [5ª aula]
```

---

## Etapa 3 — Finalidade

```txt
Professor
[Selecione]

Turma
[Selecione]

Finalidade
[Aula com slides]
```

---

## Etapa 4 — Conferir

```txt
Resumo da reserva

Recurso: Projetor HDMI 01
Data: 12/06/2026
Horário: 2ª aula
Professor: Maria
Turma: 8º A
Finalidade: Aula com slides

[Confirmar reserva]
```

---

## Componentes

```txt
BookingPage
ResourceSelector
DateSelector
TimeSlotSelector
AvailabilityBadge
BookingPurposeForm
BookingSummaryCard
BookingHistoryList
```

---

## Regras específicas

- Mostrar disponibilidade de forma visual.
- Não permitir reservar horário indisponível.
- Mostrar conflito com clareza.
- Confirmar antes de cancelar reserva.
- No mobile, horários devem aparecer em botões grandes.
- Histórico deve ficar separado da criação de nova reserva.

---

# 30.3 Módulo de Administração

## Objetivo

Permitir que usuários autorizados gerenciem o sistema.

Áreas possíveis:

- usuários;
- professores;
- turmas;
- cotas;
- impressoras;
- recursos;
- permissões;
- relatórios;
- logs.

---

## Layout sugerido

```txt
Administração

[Usuários]
[Turmas]
[Cotas]
[Impressoras]
[Recursos]
[Relatórios]
[Logs]
```

---

## Regras específicas

- Separar áreas administrativas em cards.
- Usar tabelas no desktop.
- Usar cards no mobile.
- Ações perigosas exigem confirmação.
- Logs técnicos devem ser visíveis apenas para administradores.
- Evitar misturar configuração com operação diária.

---

## Componentes

```txt
AdminDashboard
AdminSectionCard
UserTable
QuotaEditor
PrinterConfigCard
ResourceManagementTable
PermissionBadge
AuditLogTable
ConfirmDialog
```

---

# 30.4 Módulo de Relatórios

## Objetivo

Ajudar gestão e administração a entenderem o uso do sistema.

Relatórios possíveis:

- impressões por professor;
- impressões por turma;
- consumo de cotas;
- tipos de materiais;
- recursos mais usados;
- agendamentos por período;
- erros de impressão;
- volume mensal.

---

## Layout sugerido

```txt
Relatórios

[Total de impressões]
[Páginas impressas]
[Professor com maior uso]
[Turma com maior uso]

Filtros:
Período | Professor | Turma | Tipo

Tabela/Gráfico
```

---

## Regras específicas

- Usar cards de indicadores.
- Filtros devem ser claros.
- Gráficos devem ser simples.
- Evitar excesso de visualização complexa.
- Exportação deve ser clara.

Exemplos:

```txt
[Exportar CSV]
[Exportar PDF]
```

---

## Componentes

```txt
ReportPage
MetricCard
ReportFilterBar
ReportTable
SimpleChart
ExportButton
```

---

# 30.5 Módulo de Biblioteca

## Objetivo

Futuro módulo para controle de livros, empréstimos e devoluções.

Fluxos possíveis:

- cadastrar livro;
- buscar livro;
- emprestar livro;
- devolver livro;
- consultar histórico.

---

## Componentes futuros

```txt
BookSearch
BookCard
BookForm
LoanForm
LoanSummaryCard
LibraryStatusBadge
```

---

# 31. Padrões de texto

## 31.1 Botões

| Ação | Texto recomendado |
|---|---|
| Enviar impressão | Confirmar impressão |
| Avançar etapa | Continuar |
| Voltar etapa | Voltar |
| Criar reserva | Confirmar reserva |
| Cancelar pedido | Cancelar solicitação |
| Salvar edição | Salvar alterações |
| Abrir detalhes | Ver detalhes |
| Limpar filtros | Limpar filtros |
| Sair da conta | Sair |

---

## 31.2 Mensagens de sucesso

```txt
Impressão enviada com sucesso.
Reserva criada com sucesso.
Alterações salvas.
Solicitação cancelada.
Usuário atualizado.
```

---

## 31.3 Mensagens de erro

```txt
Não foi possível concluir a ação.
Tente novamente em alguns instantes.
```

```txt
Selecione um arquivo antes de continuar.
```

```txt
Selecione pelo menos um tipo de material.
```

```txt
Este horário já está reservado.
Escolha outro horário para continuar.
```

---

## 31.4 Mensagens de ajuda

```txt
Ao selecionar uma turma, o sistema pode sugerir a quantidade de cópias.
```

```txt
A impressão pode ser cancelada enquanto ainda não estiver em execução.
```

```txt
Use o intervalo para imprimir apenas algumas páginas, como 1-5, 8 ou 10-14.
```

---

# 32. Padrões de confirmação

## 32.1 Impressão

```txt
Confirmar impressão?

Confira os dados antes de enviar para a fila.

Arquivo: Atividade.pdf
Turma: 8º A
Total estimado: 180 páginas

[Voltar] [Confirmar impressão]
```

---

## 32.2 Cancelamento de impressão

```txt
Cancelar solicitação?

A impressão "Atividade.pdf" será cancelada se ainda não tiver iniciado.

[Voltar] [Cancelar solicitação]
```

---

## 32.3 Exclusão

```txt
Excluir usuário?

Esta ação não poderá ser desfeita.

[Voltar] [Excluir usuário]
```

---

# 33. Organização de componentes no frontend

A estrutura pode variar conforme o framework, mas a sugestão é separar componentes por responsabilidade.

Exemplo:

```txt
src/
  components/
    ui/
      Button.tsx
      Card.tsx
      Input.tsx
      Select.tsx
      Badge.tsx
      Modal.tsx
      Drawer.tsx
      Stepper.tsx
      EmptyState.tsx
      LoadingState.tsx
      ErrorState.tsx

    layout/
      Navbar.tsx
      Footer.tsx
      PageHeader.tsx
      PageContainer.tsx
      ActionBar.tsx

    feedback/
      Toast.tsx
      ConfirmDialog.tsx

  modules/
    print/
      components/
        PrintStepper.tsx
        FileUploadCard.tsx
        PrintPreview.tsx
        PrintSummaryCard.tsx
        MaterialTypeSelector.tsx
      pages/
        PrintPage.tsx

    booking/
      components/
        ResourceSelector.tsx
        TimeSlotSelector.tsx
        BookingSummaryCard.tsx
      pages/
        BookingPage.tsx

    admin/
      components/
      pages/

    reports/
      components/
      pages/
```

---

# 34. Regras para refatoração com Codex

Ao pedir refatoração para o Codex, seguir estas regras:

```txt
1. Não refatorar tudo de uma vez.
2. Não misturar regra de negócio com UI.
3. Não alterar endpoints sem necessidade.
4. Não remover funcionalidades existentes.
5. Componentizar telas grandes.
6. Evitar arquivos com mais de 300 linhas.
7. Preservar cálculo de cotas.
8. Preservar autenticação e permissões.
9. Preservar integração com backend.
10. Garantir responsividade.
11. Criar estados de loading, empty e error.
12. Usar componentes base do guia.
13. Seguir nomes e textos padronizados.
14. Testar desktop e mobile.
```

---

# 35. Padrão de commits para UI

Sugestões:

```txt
docs: add ui guidelines
refactor(ui): create base button component
refactor(ui): create card and badge components
refactor(print): split print page into steps
refactor(print): improve print preview layout
refactor(print): add print summary before confirmation
refactor(print): improve mobile layout
refactor(booking): create booking stepper flow
fix(ui): prevent horizontal overflow on mobile
```

---

# 36. Checklist geral de tela

Antes de finalizar qualquer tela, revisar:

```md
## Checklist de UX/UI

- [ ] A tela tem uma ação principal clara?
- [ ] O usuário entende por onde começar?
- [ ] A linguagem está simples?
- [ ] A tela evita excesso de informação?
- [ ] Existem estados de carregamento?
- [ ] Existem estados vazios?
- [ ] Existem mensagens de erro claras?
- [ ] A tela funciona no mobile?
- [ ] Não há scroll horizontal no celular?
- [ ] Os botões têm tamanho adequado?
- [ ] A ação principal está fácil de encontrar?
- [ ] Ações perigosas pedem confirmação?
- [ ] Existe resumo antes de concluir ações importantes?
- [ ] Os componentes seguem o padrão do guia?
- [ ] As cores seguem os tokens definidos?
- [ ] Os textos seguem a linguagem escolar?
- [ ] O layout não quebra em tablet?
- [ ] A tela preserva as regras de negócio?
```

---

# 37. Checklist específico do módulo de impressão

```md
## Checklist — Impressão

- [ ] O usuário seleciona o arquivo antes de configurar a impressão?
- [ ] O sistema mostra erro claro para arquivo inválido?
- [ ] O preview aparece apenas quando houver arquivo?
- [ ] O preview não atrapalha o formulário no mobile?
- [ ] Professor solicitante está claro?
- [ ] Turma está clara?
- [ ] Cópias estão claras?
- [ ] O campo de intervalo só aparece quando necessário?
- [ ] Layout e orientação são fáceis de entender?
- [ ] Frente e verso está claro?
- [ ] Tipo de material é obrigatório quando necessário?
- [ ] O total estimado aparece antes da confirmação?
- [ ] O botão final diz "Confirmar impressão"?
- [ ] Histórico não compete com nova impressão?
- [ ] Cota aparece de forma informativa, sem poluir?
- [ ] O envio preserva as regras de backend?
```

---

# 38. Checklist específico do módulo de agendamento

```md
## Checklist — Agendamento

- [ ] O usuário escolhe o recurso primeiro?
- [ ] A disponibilidade está clara?
- [ ] Horários indisponíveis não podem ser selecionados?
- [ ] Conflitos são explicados?
- [ ] A finalidade da reserva está clara?
- [ ] Existe resumo antes de confirmar?
- [ ] Cancelamento pede confirmação?
- [ ] A tela funciona bem no celular?
- [ ] Histórico fica separado da nova reserva?
```

---

# 39. Definição de pronto para UI

Uma tela só deve ser considerada pronta quando:

```txt
1. Funciona no desktop.
2. Funciona no mobile.
3. Tem ação principal clara.
4. Tem estado vazio.
5. Tem estado de carregamento.
6. Tem estado de erro.
7. Usa componentes padronizados.
8. Usa textos claros.
9. Preserva regras de negócio.
10. Foi revisada visualmente.
```

---

# 40. Frase-guia do sistema

A Suíte Escolar deve seguir esta ideia:

> Menos painel técnico, mais fluxo escolar.

Na prática, isso significa:

- professor não envia "job";
- professor envia "impressão";
- gestão não analisa "requisições";
- gestão acompanha "solicitações";
- usuário não precisa saber como o sistema funciona por dentro;
- o sistema deve guiar o usuário até a conclusão da tarefa.

---

# 41. Frase-guia do módulo de impressão

> O formulário conduz. O preview confirma. O resumo protege contra erro.

Isso significa:

- o formulário guia o usuário etapa por etapa;
- a pré-visualização ajuda a conferir o arquivo;
- o resumo impede envio errado.

---

# 42. Prompt recomendado para usar com Codex

Use este prompt quando quiser iniciar a refatoração de UI seguindo este guia:

```md
Quero refatorar a UI da Suíte Escolar seguindo o arquivo GUIA.md.

Antes de alterar código:
1. Leia o GUIA.md.
2. Analise a estrutura atual do frontend.
3. Identifique componentes duplicados.
4. Identifique telas grandes demais.
5. Proponha um plano incremental de refatoração.

Regras:
- Não refatorar tudo de uma vez.
- Não alterar regras de negócio sem necessidade.
- Não quebrar integração com backend.
- Não alterar endpoints sem autorização.
- Preservar autenticação, permissões e cálculos existentes.
- Criar componentes reutilizáveis.
- Usar os padrões de cor, botão, card, formulário, badge, modal, drawer e stepper definidos no GUIA.md.
- Garantir responsividade.
- Evitar arquivos com mais de 300 linhas.
- Criar estados de loading, empty e error quando necessário.

Primeira tarefa:
Refatore o módulo de impressão para um fluxo em 4 etapas:
1. Arquivo
2. Dados
3. Impressão
4. Conferir

O preview deve ficar ao lado no desktop e abrir em modal ou tela separada no mobile.
O histórico não deve competir com a ação de nova impressão.
O botão final deve ser "Confirmar impressão".
Antes de confirmar, deve existir um SummaryCard com os dados da solicitação.
```

---

# 43. Observação final

Este guia deve evoluir junto com o sistema.

Sempre que um novo padrão visual for criado, ele deve ser documentado aqui antes de ser repetido em outras telas.

Se uma solução visual for usada em mais de uma tela, ela provavelmente deve virar componente reutilizável.
