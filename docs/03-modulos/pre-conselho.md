# Modulo: Pre-Conselho

Status: pendente de documentacao detalhada.

## Objetivo

Documentar registros, periodos, motivos, consolidado, relatorios e visoes do pre-conselho.

## Paginas

- `/preconselho`: preenchimento e reavaliacao do professor;
- `/preconselho/consolidacao`: consolidacao institucional;
- `/preconselho/reavaliacao`: acompanhamento da reavaliacao pela gestao;
- `/preconselho/relatorios`: indicadores institucionais;
- `/preconselho/rav`: acompanhamento de Recuperar para Avancar;
- `/preconselho/configuracoes`: periodos, motivos e habilidades de RAV.

A rota-base e o nome tecnico permanecem estaveis ate que a futura identidade do
modulo seja definida. As paginas compartilham as mesmas APIs do dominio.

## Fontes recomendadas

- `modules/preconselho/`
- `services/preconselho_service.py`
- `db/preconselho.py`
- `templates/preconselho/index.html`
- `static/js/preconselho/`: scripts separados por responsabilidade e carregados
  em ordem pelo template;
