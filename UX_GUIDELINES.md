# UI_REFACTOR_PLAN.md

## Objetivo

Refatorar a interface da Suíte Escolar para torná-la mais simples, intuitiva, responsiva e consistente, especialmente para uso por professores, coordenação e gestão escolar.

O sistema deve priorizar clareza, poucos passos, linguagem simples e prevenção de erros.

## Princípios de UX

### 1. Uma ação principal por tela

Cada tela deve deixar claro qual é a ação principal.

Exemplos:
- Tela de impressão: enviar uma nova impressão.
- Tela de agendamento: reservar um recurso.
- Tela de serviços: escolher um módulo.
- Tela de histórico: consultar pedidos anteriores.

Evitar telas com muitas ações concorrendo visualmente.

### 2. Mostrar complexidade aos poucos

Não exibir todas as opções de uma vez.

Configurações avançadas devem ficar agrupadas, recolhidas ou aparecer apenas quando necessárias.

Exemplo:
- Na impressão, só mostrar intervalo de páginas quando o usuário escolher "personalizar páginas".
- No agendamento, só mostrar campos extras depois de escolher o recurso e a data.

### 3. Fluxos guiados

Sempre que possível, transformar telas complexas em etapas.

Exemplo para impressão:
1. Escolher arquivo.
2. Configurar impressão.
3. Conferir resumo.
4. Confirmar envio.

Exemplo para agendamento:
1. Escolher recurso.
2. Escolher data e horário.
3. Informar finalidade.
4. Confirmar reserva.

### 4. Mobile first

Toda tela deve funcionar bem em celular.

Regras:
- Evitar três colunas.
- Evitar tabelas largas sem adaptação.
- Usar cards no mobile.
- Botões principais devem ser grandes e fáceis de tocar.
- Pré-visualizações grandes devem abrir em modal ou página separada.

### 5. Linguagem simples

Usar textos próximos da linguagem escolar.

Preferir:
- "Confirmar impressão" em vez de "Submeter job".
- "Meus pedidos" em vez de "Histórico de requisições".
- "Tipo de material" em vez de "Classificação".
- "Reservar recurso" em vez de "Criar agendamento".

### 6. Resumo antes de ações importantes

Antes de concluir ações relevantes, mostrar um resumo.

Exemplo:
- Antes de imprimir, mostrar arquivo, professor, turma, cópias, páginas e total estimado.
- Antes de reservar um recurso, mostrar recurso, data, horário e responsável.
- Antes de cancelar algo, mostrar o que será cancelado.

### 7. Estados claros

Toda tela deve ter bons estados de:
- carregando;
- vazio;
- erro;
- sucesso;
- bloqueado/desabilitado.

Exemplo:
Em vez de uma área vazia:
"Selecione um arquivo para visualizar a prévia."

Em vez de erro genérico:
"Não foi possível carregar o PDF. Tente enviar novamente ou converter o arquivo para PDF."

### 8. Consistência visual

Padronizar:
- botões;
- cards;
- inputs;
- títulos;
- badges;
- mensagens;
- modais;
- tabelas;
- cores de status.

Status sugeridos:
- Pendente
- Em andamento
- Concluído
- Cancelado
- Erro

### 9. Hierarquia visual

A tela deve deixar claro:
- título da página;
- ação principal;
- informações secundárias;
- ações perigosas ou administrativas.

### 10. Não quebrar regras de negócio

A refatoração de UI não deve alterar:
- cálculo de cotas;
- permissões;
- autenticação;
- envio para fila;
- regras de agendamento;
- filtros;
- histórico;
- integrações existentes.