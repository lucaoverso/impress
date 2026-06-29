# Operacao: Worker

## Modos de execucao

O worker pode rodar de duas formas:

| Modo | Como inicia | Evidencia | Classificacao |
| --- | --- | --- | --- |
| Externo | `worker_main.py` chama `criar_tabelas()` e `worker_loop()`. | `worker_main.py`; `deploy/systemd/sistema-impress-worker.service`. | Confirmada pelo codigo |
| Embutido | `main.py` inicia thread quando `ENABLE_EMBEDDED_WORKER` esta ativo. | `main.py`: `lifespan`; `routers/config.py`. | Confirmada pelo codigo |

No deploy local documentado, o recomendado e `ENABLE_EMBEDDED_WORKER=false` com worker externo via systemd.

Classificacao: **Confirmada pela documentacao**.

## Processamento da fila

`services/worker.py`: `worker_loop`:

1. normaliza jobs pendentes no inicio;
2. registra parametros de cancelamento e retencao;
3. limpa spool expirado quando configurado;
4. busca proximo job com `buscar_proximo_job(atraso_minimo_segundos=JANELA_CANCELAMENTO_SEGUNDOS)`;
5. marca job como `IMPRIMINDO`;
6. chama `services.printer.imprimir_job`;
7. registra `cups_job_id` e `printer_name`;
8. marca job como `CONCLUIDO`;
9. remove arquivo do spool se `KEEP_SPOOL_FILES` estiver desativado;
10. em erro, registra erro e marca job como `ERRO`;
11. se nao houver job de impressao, tenta processar preview APC.

Classificacao: **Confirmada pelo codigo**.

## Spool

| Configuracao | Comportamento | Evidencia |
| --- | --- | --- |
| `SPOOL_DIR` | Define onde ficam arquivos enviados, PDFs preparados e downloads. | `routers/config.py`, `modules/printing/config.py`, `services/youtube_download_service.py`. |
| `KEEP_SPOOL_FILES=true` | Mantem arquivos apos impressao para preview/reimpressao. | `services/worker.py`. |
| `KEEP_SPOOL_FILES=false` | Remove arquivo do job apos conclusao. | `services/worker.py`: `limpar_arquivo_job`. |
| `SPOOL_RETENTION_DAYS=0` | Desativa limpeza automatica por idade. | `services/worker.py`. |
| `SPOOL_RETENTION_DAYS>0` | Remove arquivos antigos, preservando arquivos de jobs em andamento. | `services/worker.py`: `limpar_spool_expirado`. |

Classificacao: **Confirmada pelo codigo**.

## CUPS

`services/printer.py` envia jobs pelo comando configurado em `CUPS_LP_COMMAND`, por padrao `lp`.

Configuracoes relevantes:

- `CUPS_PRINTER`: fila/impressora destino;
- `CUPS_LP_COMMAND`: comando de envio;
- `CUPS_LP_TIMEOUT_SECONDS`: timeout do processo;
- opcoes CUPS sao carregadas de `job["cups_options"]` ou montadas em modo legado;
- layouts `2` ou `4` por folha podem gerar PDF temporario antes do envio.

Erros tratados:

- arquivo ausente;
- `lp` nao encontrado;
- timeout;
- retorno nao zero do comando `lp`.

Classificacao: **Confirmada pelo codigo**.

## Riscos operacionais e de seguranca

| Risco | Evidencia | Classificacao |
| --- | --- | --- |
| Rodar worker embutido e externo ao mesmo tempo pode gerar concorrencia operacional se ambos consumirem fila. | Codigo suporta os dois modos; deploy recomenda externo. | Inferida |
| Spool preservado pode acumular arquivos sensiveis e ocupar disco. | `KEEP_SPOOL_FILES=true`; `SPOOL_RETENTION_DAYS=0`. | Confirmada pelo codigo |
| Falha de CUPS ou ausencia de `lp` coloca jobs em `ERRO`. | `services/printer.py`; `services/worker.py`. | Confirmada pelo codigo |
| Nao foi encontrada rotina de monitoramento de tamanho do spool. | Ausencia de implementacao identificada. | Pendente de validacao |
