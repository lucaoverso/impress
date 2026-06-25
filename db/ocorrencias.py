from ._proxy import get_database_attr, proxy

ACAO_OCORRENCIA_VALIDAS = get_database_attr("ACAO_OCORRENCIA_VALIDAS")
LEI_PADRAO_IMPORTACAO = get_database_attr("LEI_PADRAO_IMPORTACAO")
QUEM_ASSINA_OCORRENCIA_ESTUDANTE = get_database_attr("QUEM_ASSINA_OCORRENCIA_ESTUDANTE")
QUEM_ASSINA_OCORRENCIA_RESPONSAVEL = get_database_attr("QUEM_ASSINA_OCORRENCIA_RESPONSAVEL")
QUEM_ASSINA_OCORRENCIA_AMBOS = get_database_attr("QUEM_ASSINA_OCORRENCIA_AMBOS")
QUEM_ASSINA_OCORRENCIA_VALIDOS = get_database_attr("QUEM_ASSINA_OCORRENCIA_VALIDOS")
STATUS_OCORRENCIA_REGISTRADO = get_database_attr("STATUS_OCORRENCIA_REGISTRADO")
STATUS_OCORRENCIA_VALIDOS = get_database_attr("STATUS_OCORRENCIA_VALIDOS")
TIPOS_REGISTRO_OCORRENCIA = get_database_attr("TIPOS_REGISTRO_OCORRENCIA")
atualizar_alinea = proxy("atualizar_alinea")
atualizar_artigo = proxy("atualizar_artigo")
atualizar_estudante = proxy("atualizar_estudante")
atualizar_inciso = proxy("atualizar_inciso")
atualizar_lei = proxy("atualizar_lei")
atualizar_ocorrencia = proxy("atualizar_ocorrencia")
atualizar_regimento_item = proxy("atualizar_regimento_item")
atualizar_status_estudante = proxy("atualizar_status_estudante")
atualizar_status_regimento_item = proxy("atualizar_status_regimento_item")
buscar_alinea_por_id = proxy("buscar_alinea_por_id")
buscar_artigo_por_id = proxy("buscar_artigo_por_id")
buscar_estudante_por_id = proxy("buscar_estudante_por_id")
buscar_estudantes_ocorrencia = proxy("buscar_estudantes_ocorrencia")
buscar_inciso_por_id = proxy("buscar_inciso_por_id")
buscar_lei_por_id = proxy("buscar_lei_por_id")
buscar_ocorrencia_por_id = proxy("buscar_ocorrencia_por_id")
buscar_professor_por_id_ocorrencia = proxy("buscar_professor_por_id_ocorrencia")
buscar_professores_ocorrencia = proxy("buscar_professores_ocorrencia")
buscar_regimento_item_por_id = proxy("buscar_regimento_item_por_id")
buscar_regimento_itens_por_ids = proxy("buscar_regimento_itens_por_ids")
criar_alinea = proxy("criar_alinea")
criar_artigo = proxy("criar_artigo")
criar_estudante = proxy("criar_estudante")
criar_inciso = proxy("criar_inciso")
criar_lei = proxy("criar_lei")
criar_ocorrencia = proxy("criar_ocorrencia")
criar_ou_atualizar_estudante_por_nome_turma = proxy("criar_ou_atualizar_estudante_por_nome_turma")
criar_ou_atualizar_regimento_item = proxy("criar_ou_atualizar_regimento_item")
criar_regimento_item = proxy("criar_regimento_item")
listar_alineas = proxy("listar_alineas")
listar_artigos = proxy("listar_artigos")
listar_estudantes = proxy("listar_estudantes")
listar_incisos = proxy("listar_incisos")
listar_leis = proxy("listar_leis")
listar_ocorrencias = proxy("listar_ocorrencias")
listar_regimento_itens = proxy("listar_regimento_itens")
remover_alinea = proxy("remover_alinea")
remover_artigo = proxy("remover_artigo")
remover_estudante = proxy("remover_estudante")
remover_inciso = proxy("remover_inciso")
remover_lei = proxy("remover_lei")
remover_ocorrencia = proxy("remover_ocorrencia")
remover_regimento_item = proxy("remover_regimento_item")
salvar_ocorrencia_estudantes_vinculados = proxy("salvar_ocorrencia_estudantes_vinculados")
salvar_ocorrencia_professores_vinculados = proxy("salvar_ocorrencia_professores_vinculados")
salvar_regimento_itens_ocorrencia = proxy("salvar_regimento_itens_ocorrencia")

__all__ = [
    "ACAO_OCORRENCIA_VALIDAS",
    "LEI_PADRAO_IMPORTACAO",
    "QUEM_ASSINA_OCORRENCIA_ESTUDANTE",
    "QUEM_ASSINA_OCORRENCIA_RESPONSAVEL",
    "QUEM_ASSINA_OCORRENCIA_AMBOS",
    "QUEM_ASSINA_OCORRENCIA_VALIDOS",
    "STATUS_OCORRENCIA_REGISTRADO",
    "STATUS_OCORRENCIA_VALIDOS",
    "TIPOS_REGISTRO_OCORRENCIA",
    "atualizar_alinea",
    "atualizar_artigo",
    "atualizar_estudante",
    "atualizar_inciso",
    "atualizar_lei",
    "atualizar_ocorrencia",
    "atualizar_regimento_item",
    "atualizar_status_estudante",
    "atualizar_status_regimento_item",
    "buscar_alinea_por_id",
    "buscar_artigo_por_id",
    "buscar_estudante_por_id",
    "buscar_estudantes_ocorrencia",
    "buscar_inciso_por_id",
    "buscar_lei_por_id",
    "buscar_ocorrencia_por_id",
    "buscar_professor_por_id_ocorrencia",
    "buscar_professores_ocorrencia",
    "buscar_regimento_item_por_id",
    "buscar_regimento_itens_por_ids",
    "criar_alinea",
    "criar_artigo",
    "criar_estudante",
    "criar_inciso",
    "criar_lei",
    "criar_ocorrencia",
    "criar_ou_atualizar_estudante_por_nome_turma",
    "criar_ou_atualizar_regimento_item",
    "criar_regimento_item",
    "listar_alineas",
    "listar_artigos",
    "listar_estudantes",
    "listar_incisos",
    "listar_leis",
    "listar_ocorrencias",
    "listar_regimento_itens",
    "remover_alinea",
    "remover_artigo",
    "remover_estudante",
    "remover_inciso",
    "remover_lei",
    "remover_ocorrencia",
    "remover_regimento_item",
    "salvar_ocorrencia_estudantes_vinculados",
    "salvar_ocorrencia_professores_vinculados",
    "salvar_regimento_itens_ocorrencia",
]
