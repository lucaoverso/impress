# Plano de padronização visual

## Objetivo

Unificar o padrão visual dos módulos sem alterar rotas, banco de dados ou regras de negócio. Navbar, sidebar, largura do conteúdo, cabeçalhos, controles e comportamento responsivo devem seguir o design system compartilhado.

## Escopo

- Módulos: serviços, impressão, agendamento, download, horário escolar, APC, PCPI, pré-conselho, coordenação, relatórios, gestão, notificações e perfil.
- Camada principal: templates Jinja e CSS compartilhado/de página.
- Fora do escopo: autenticação, regras de negócio, APIs e banco de dados.

## Problemas confirmados

- [x] O `<main>` pode encolher conforme o conteúdo, produzindo larguras diferentes entre módulos.
- [x] Serviços altera navbar e sidebar apenas no mobile.
- [x] Títulos principais variam entre 26, 32, 34 e 48 px.
- [x] Parte dos templates não usa `page-shell`, `page-header`, `page-title` e `page-lead`.
- [x] Botões equivalentes usam alturas e raios diferentes.
- [x] Agendamento importa estilos completos do módulo de impressão.
- [x] Notificações e perfil não possuem uma variante explícita do shell sem sidebar.
- [x] Upload de impressão e texto final do PCPI precisam de nome acessível.

## Implementação

### 1. Shell compartilhado

- [x] Fixar a largura útil do conteúdo com sidebar sem depender do tamanho interno.
- [x] Preservar as variantes `page-shell--wide`, `--medium` e `--compact`.
- [x] Remover as alterações mobile de navbar/sidebar exclusivas de Serviços.
- [x] Criar uma variante compartilhada e explícita para páginas globais sem sidebar.

### 2. Hierarquia e componentes

- [x] Aplicar o cabeçalho canônico aos templates ainda legados.
- [x] Padronizar título principal em 34 px no desktop e 24 px no mobile.
- [x] Padronizar ações comuns em 44 px e raio de 12 px.
- [x] Padronizar campos em 48 px e raio de 12 px.
- [x] Manter cards apenas para unidades independentes, preservando superfícies contínuas.

### 3. CSS dos módulos

- [x] Remover sobrescritas locais conflitantes de título, botão e shell.
- [x] Reduzir o acoplamento do Agendamento com estilos de Impressão.
- [x] Preservar estilos realmente específicos de cada fluxo.
- [x] Adicionar contratos automatizados contra novas sobrescritas do app shell.

### 4. Acessibilidade

- [x] Associar nome acessível ao upload da Impressão.
- [x] Associar nome acessível ao texto final do PCPI.
- [x] Garantir alvos de toque de pelo menos 44 px no mobile.

### 5. Verificação

- [x] Executar testes automatizados relacionados a layout e acessibilidade.
- [x] Verificar desktop em 1280 px nos módulos principais.
- [x] Verificar mobile em 390 px nos módulos principais.
- [x] Confirmar navbar, sidebar, fonte, título e largura do conteúdo por métricas.
- [x] Confirmar ausência de rolagem horizontal.
- [ ] Revisar visualmente páginas irmãs dentro de cada módulo.

### 6. Consistência interna por módulo

- [x] Impressão: comparar Nova impressão e Meu histórico no desktop.
- [x] Agendamento: confirmar o mesmo shell em Novo agendamento, Meus agendamentos, Calendário e Recursos no desktop.
- [x] APC: confirmar o mesmo shell em Central de APC e Calendário no desktop.
- [x] Gestão: confirmar o mesmo shell nas oito páginas administrativas no desktop.
- [x] Demais módulos: confirmar o shell em Serviços, Download, Horário, PCPI, Pré-conselho, Coordenação e Relatórios no desktop.
- [ ] Comparar visualmente páginas irmãs e estados vazios, carregados e responsivos no mobile.

### 7. Evidências da nova auditoria

- [x] Navbar: `1280 × 81 px` em todas as páginas verificadas.
- [x] Sidebar: `252 px` em todas as páginas verificadas que possuem navegação lateral.
- [x] Conteúdo com sidebar: `1004 px`, início em `x = 276` e padding `16 / 16 / 24 px`.
- [x] Títulos sem elemento anterior: `34 px`, início em `x = 292 / y = 97`.
- [x] Ausência de overflow horizontal nas páginas verificadas em 1280 px.
- [x] Componentes em 19 páginas: nenhuma divergência de altura, raio, sombra ou overflow nos contratos auditados.
- [x] Ações comuns: mínimo `44 px`, raio `12 px`.
- [x] Campos: altura `48 px`, raio `12 px`.
- [x] Unidades independentes: raio `16 px`, borda discreta e sem sombra decorativa.
- [x] Superfícies principais: sem borda, raio ou sombra.
- [x] Suíte direcionada: 68 testes aprovados.

### 8. Correções funcionais posteriores

- [x] Catálogo de recursos inicia sem recurso pré-selecionado.
- [x] Cards do catálogo abrem os detalhes por clique, Enter ou Espaço.
- [x] Trocar filtros limpa a seleção quando o recurso deixa de estar visível.

## Riscos

- A cascata CSS atual possui arquivos grandes e seletores legados; a remoção será restrita a regras comprovadamente conflitantes.
- Páginas administrativas têm densidades diferentes; a largura será unificada sem forçar todos os conteúdos a usar a mesma grade interna.
- Notificações e Perfil são páginas globais; continuarão sem navegação lateral, mas usarão o mesmo alinhamento e hierarquia do shell.
- Alterações atuais do Agendamento serão preservadas e incorporadas aos contratos compartilhados.

## Checklist manual recomendado

- [x] Navbar mantém altura, logo, busca, ajuda, notificações e perfil em todos os módulos.
- [x] Sidebar mantém largura e comportamento mobile em todos os módulos que a utilizam.
- [x] Serviços não transforma a sidebar em barra inferior.
- [x] Títulos principais têm a mesma escala visual.
- [x] Páginas de Gestão ocupam toda a largura útil.
- [ ] Agendamento, Impressão, APC, Coordenação e Relatórios abrem sem perda de conteúdo.
- [x] Notificações e Perfil alinham o conteúdo ao shell global.
- [ ] Formulários continuam enviando e validando normalmente.
- [x] Não existe rolagem horizontal em 390 px.
