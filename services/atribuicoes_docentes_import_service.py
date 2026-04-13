import json

from db.catalogos import (
    buscar_disciplina_por_id,
    buscar_disciplina_por_nome,
    buscar_turma_por_id,
    buscar_turma_por_nome,
)
from db.usuarios import (
    buscar_usuario_por_id,
    listar_professores_agendamento,
)
from db.docencia import (
    sincronizar_atribuicoes_docentes_professor_disciplina,
)


LIMITE_ARQUIVO_JSON_BYTES = 2 * 1024 * 1024


def _normalizar_texto(valor) -> str:
    return str(valor or "").strip()


def _decodificar_json(conteudo: bytes) -> object:
    if not conteudo:
        raise ValueError("Arquivo JSON vazio.")
    if len(conteudo) > LIMITE_ARQUIVO_JSON_BYTES:
        raise ValueError("Arquivo JSON muito grande. Envie um arquivo de ate 2 MB.")

    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Nao foi possivel ler o arquivo JSON em UTF-8.") from exc

    if not texto.strip():
        raise ValueError("Arquivo JSON vazio.")

    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON invalido para importacao de atribuicoes docentes.") from exc


def _extrair_itens_json(dados: object) -> list[dict]:
    if isinstance(dados, dict):
        if isinstance(dados.get("atribuicoes"), list):
            itens = dados["atribuicoes"]
        else:
            itens = [dados]
    elif isinstance(dados, list):
        itens = dados
    else:
        raise ValueError("JSON invalido: informe um objeto ou lista de atribuicoes.")

    itens_validos = [item for item in itens if isinstance(item, dict)]
    if not itens_validos:
        raise ValueError("O JSON nao possui atribuicoes docentes para importar.")
    return itens_validos


def _eh_professor(usuario: dict | None) -> bool:
    if not usuario:
        return False
    cargo = _normalizar_texto(usuario.get("cargo")).upper()
    if cargo:
        return cargo == "PROFESSOR"
    return _normalizar_texto(usuario.get("perfil")).lower() == "professor"


def _resolver_professor(item: dict) -> dict:
    email = _normalizar_texto(item.get("professor_email") or item.get("email")).lower()
    if email:
        raise ValueError("Use professor_nome no JSON. A importacao por email nao e mais suportada.")

    nome = _normalizar_texto(item.get("professor_nome") or item.get("professor"))
    if nome:
        candidatos = [
            prof
            for prof in listar_professores_agendamento()
            if _normalizar_texto(prof.get("nome")).casefold() == nome.casefold()
        ]
        if len(candidatos) == 1:
            professor = buscar_usuario_por_id(int(candidatos[0]["id"]))
            if _eh_professor(professor):
                return professor
        if len(candidatos) > 1:
            raise ValueError(
                "Existe mais de um professor com esse nome. Use professor_id para diferenciar."
            )
        raise ValueError("Professor nao encontrado para o nome informado.")

    professor_id = item.get("professor_id")
    if professor_id not in (None, ""):
        try:
            professor = buscar_usuario_por_id(int(professor_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("professor_id invalido.") from exc
        if not _eh_professor(professor):
            raise ValueError("Professor nao encontrado para o professor_id informado.")
        return professor

    raise ValueError("Informe professor_nome, professor ou professor_id.")


def _resolver_disciplina(item: dict) -> dict:
    disciplina_id = item.get("disciplina_id")
    if disciplina_id not in (None, ""):
        try:
            disciplina = buscar_disciplina_por_id(int(disciplina_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("disciplina_id invalido.") from exc
        if not disciplina or not int(disciplina.get("ativo", 0)):
            raise ValueError("Disciplina nao encontrada para o disciplina_id informado.")
        return disciplina

    nome = _normalizar_texto(item.get("disciplina_nome") or item.get("disciplina"))
    if nome:
        disciplina = buscar_disciplina_por_nome(nome, incluir_inativas=False)
        if not disciplina:
            raise ValueError("Disciplina nao encontrada para o nome informado.")
        return disciplina

    raise ValueError("Informe disciplina_id ou disciplina.")


def _resolver_turmas(item: dict) -> list[int]:
    turma_ids = []
    valores_ids = item.get("turma_ids")
    if isinstance(valores_ids, list):
        for valor in valores_ids:
            try:
                turma = buscar_turma_por_id(int(valor))
            except (TypeError, ValueError) as exc:
                raise ValueError("turma_ids contem valor invalido.") from exc
            if not turma or not int(turma.get("ativo", 0)):
                raise ValueError("Uma ou mais turmas informadas por id nao foram encontradas.")
            turma_id = int(turma["id"])
            if turma_id not in turma_ids:
                turma_ids.append(turma_id)

    valores_turmas = item.get("turmas")
    if isinstance(valores_turmas, list):
        for valor in valores_turmas:
            turma = None
            if isinstance(valor, dict):
                if valor.get("id") not in (None, ""):
                    try:
                        turma = buscar_turma_por_id(int(valor["id"]))
                    except (TypeError, ValueError) as exc:
                        raise ValueError("Uma das turmas possui id invalido.") from exc
                elif _normalizar_texto(valor.get("nome")):
                    turma = buscar_turma_por_nome(valor.get("nome"), incluir_inativas=False)
            else:
                turma = buscar_turma_por_nome(valor, incluir_inativas=False)

            if not turma or not int(turma.get("ativo", 0)):
                raise ValueError("Uma ou mais turmas informadas nao foram encontradas.")

            turma_id = int(turma["id"])
            if turma_id not in turma_ids:
                turma_ids.append(turma_id)

    return turma_ids


def importar_atribuicoes_docentes_json(conteudo: bytes) -> dict:
    dados = _decodificar_json(conteudo)
    itens = _extrair_itens_json(dados)

    grupos_processados = 0
    atribuicoes_criadas = 0
    atribuicoes_removidas = 0
    detalhes_erros = []

    for indice, item in enumerate(itens, start=1):
        try:
            professor = _resolver_professor(item)
            disciplina = _resolver_disciplina(item)
            turma_ids = _resolver_turmas(item)
            if not turma_ids and not bool(item.get("permitir_vazio", False)):
                raise ValueError(
                    "Informe ao menos uma turma ou use permitir_vazio=true para limpar a atribuicao."
                )

            resultado = sincronizar_atribuicoes_docentes_professor_disciplina(
                professor_id=int(professor["id"]),
                disciplina_id=int(disciplina["id"]),
                turma_ids=turma_ids,
            )
            grupos_processados += 1
            atribuicoes_criadas += int(resultado.get("criados") or 0)
            atribuicoes_removidas += int(resultado.get("removidos") or 0)
        except ValueError as exc:
            detalhes_erros.append(f"Linha {indice}: {exc}")

    if grupos_processados <= 0:
        raise ValueError(
            "Nenhuma atribuicao docente foi importada. "
            + (detalhes_erros[0] if detalhes_erros else "Confira o arquivo enviado.")
        )

    mensagem = (
        f"Importacao concluida com {grupos_processados} combinacao(oes) processada(s), "
        f"{atribuicoes_criadas} atribuicao(oes) criada(s) e "
        f"{atribuicoes_removidas} atribuicao(oes) removida(s)."
    )
    if detalhes_erros:
        mensagem += f" {len(detalhes_erros)} item(ns) com erro."

    return {
        "mensagem": mensagem,
        "importados": grupos_processados,
        "criados": atribuicoes_criadas,
        "removidos": atribuicoes_removidas,
        "erros": len(detalhes_erros),
        "detalhes_erros": detalhes_erros,
    }


def importar_atribuicoes_docentes_arquivo(
    conteudo: bytes,
    *,
    nome_arquivo: str | None = None,
    tipo_conteudo: str | None = None,
) -> dict:
    nome = _normalizar_texto(nome_arquivo).lower()
    tipo = _normalizar_texto(tipo_conteudo).lower()

    if nome.endswith(".json") or "json" in tipo:
        return importar_atribuicoes_docentes_json(conteudo)

    dados = _decodificar_json(conteudo)
    return importar_atribuicoes_docentes_json(json.dumps(dados, ensure_ascii=False).encode("utf-8"))
