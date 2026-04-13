from ._proxy import proxy

alterar_prioridade = proxy("alterar_prioridade")
atualizar_regras_cota = proxy("atualizar_regras_cota")
atualizar_erro_job = proxy("atualizar_erro_job")
atualizar_job_cups = proxy("atualizar_job_cups")
atualizar_status = proxy("atualizar_status")
buscar_cota = proxy("buscar_cota")
buscar_cota_do_usuario = proxy("buscar_cota_do_usuario")
buscar_job = proxy("buscar_job")
buscar_proximo_job = proxy("buscar_proximo_job")
calcular_cotas_mensais_professores = proxy("calcular_cotas_mensais_professores")
calcular_limite_cota_usuario = proxy("calcular_limite_cota_usuario")
cancelar_job = proxy("cancelar_job")
consumir_cota = proxy("consumir_cota")
criar_cota = proxy("criar_cota")
criar_job = proxy("criar_job")
gerar_relatorio_impressao = proxy("gerar_relatorio_impressao")
gerar_relatorio_uso_recursos = proxy("gerar_relatorio_uso_recursos")
gerar_relatorio_uso_recursos_por_professor = proxy("gerar_relatorio_uso_recursos_por_professor")
listar_fila = proxy("listar_fila")
listar_historico = proxy("listar_historico")
listar_jobs_ativos = proxy("listar_jobs_ativos")
listar_jobs_por_usuario = proxy("listar_jobs_por_usuario")
obter_regras_cota = proxy("obter_regras_cota")
recalcular_cotas_mes = proxy("recalcular_cotas_mes")

__all__ = [
    "alterar_prioridade",
    "atualizar_regras_cota",
    "atualizar_erro_job",
    "atualizar_job_cups",
    "atualizar_status",
    "buscar_cota",
    "buscar_cota_do_usuario",
    "buscar_job",
    "buscar_proximo_job",
    "calcular_cotas_mensais_professores",
    "calcular_limite_cota_usuario",
    "cancelar_job",
    "consumir_cota",
    "criar_cota",
    "criar_job",
    "gerar_relatorio_impressao",
    "gerar_relatorio_uso_recursos",
    "gerar_relatorio_uso_recursos_por_professor",
    "listar_fila",
    "listar_historico",
    "listar_jobs_ativos",
    "listar_jobs_por_usuario",
    "obter_regras_cota",
    "recalcular_cotas_mes",
]
