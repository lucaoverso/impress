from __future__ import annotations

import csv
import io
import unicodedata

from database import (
    buscar_turma_por_id,
    buscar_turma_por_nome,
    criar_ou_atualizar_estudante_por_nome_turma,
    criar_ou_atualizar_regimento_item_por_artigo,
)

LIMITE_ARQUIVO_CSV_BYTES = 2 * 1024 * 1024

COLUNAS_ESTUDANTES = {
    "nome": {
        "nome",
        "aluno",
        "estudante",
        "nome_estudante",
        "nome_aluno",
    },
    "turma": {
        "turma",
        "turma_nome",
        "nome_turma",
        "classe",
        "sala",
    },
    "turma_id": {
        "turma_id",
        "id_turma",
    },
    "ativo": {
        "ativo",
        "status",
        "situacao",
    },
}

COLUNAS_BASE_LEGAL = {
    "artigo": {
        "artigo",
        "referencia",
        "base_legal",
        "lei",
        "item",
    },
    "descricao": {
        "descricao",
        "texto",
        "conteudo",
        "detalhe",
        "trecho",
    },
    "ativo": {
        "ativo",
        "status",
        "situacao",
    },
}

VALORES_BOOLEANOS_TRUE = {
    "1",
    "sim",
    "s",
    "true",
    "ativo",
    "yes",
}

VALORES_BOOLEANOS_FALSE = {
    "0",
    "nao",
    "n",
    "false",
    "inativo",
    "no",
}


def _normalizar_texto(valor: str | None) -> str:
    return str(valor or "").strip()


def _normalizar_chave(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", _normalizar_texto(valor))
    texto_ascii = texto.encode("ascii", "ignore").decode("ascii")
    partes = []
    ultimo_foi_underscore = False
    for caractere in texto_ascii.lower():
        if caractere.isalnum():
            partes.append(caractere)
            ultimo_foi_underscore = False
            continue
        if not ultimo_foi_underscore:
            partes.append("_")
            ultimo_foi_underscore = True
    return "".join(partes).strip("_")


def _decodificar_csv(conteudo: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Nao foi possivel ler o arquivo CSV. Salve-o em UTF-8 ou CSV padrao do Excel.")


def _detectar_delimitador(texto: str) -> str:
    primeira_linha = ""
    for linha in texto.splitlines():
        if linha.strip():
            primeira_linha = linha
            break
    if primeira_linha.count(";") > primeira_linha.count(","):
        return ";"
    return ","


def _mapa_aliases(colunas_aceitas: dict[str, set[str]]) -> dict[str, str]:
    mapa = {}
    for campo_canonico, aliases in colunas_aceitas.items():
        mapa[campo_canonico] = campo_canonico
        for alias in aliases:
            mapa[_normalizar_chave(alias)] = campo_canonico
    return mapa


def _carregar_linhas_csv(
    conteudo: bytes,
    *,
    colunas_aceitas: dict[str, set[str]],
    colunas_obrigatorias: set[str],
) -> list[tuple[int, dict[str, str]]]:
    if not conteudo:
        raise ValueError("Arquivo CSV vazio.")
    if len(conteudo) > LIMITE_ARQUIVO_CSV_BYTES:
        raise ValueError("Arquivo CSV muito grande. Envie um arquivo de ate 2 MB.")

    texto = _decodificar_csv(conteudo)
    if not texto.strip():
        raise ValueError("Arquivo CSV vazio.")

    delimitador = _detectar_delimitador(texto)
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador, skipinitialspace=True)
    if not leitor.fieldnames:
        raise ValueError("Cabecalho CSV nao encontrado.")

    aliases = _mapa_aliases(colunas_aceitas)
    colunas_encontradas = set()
    for nome_coluna in leitor.fieldnames:
        campo = aliases.get(_normalizar_chave(nome_coluna))
        if campo:
            colunas_encontradas.add(campo)

    faltantes = [campo for campo in colunas_obrigatorias if campo not in colunas_encontradas]
    if faltantes:
        colunas_esperadas = ", ".join(sorted(colunas_obrigatorias))
        raise ValueError(f"Cabecalho CSV invalido. Colunas obrigatorias: {colunas_esperadas}.")

    linhas = []
    for indice_linha, linha in enumerate(leitor, start=2):
        if not linha:
            continue
        if not any(_normalizar_texto(valor) for valor in linha.values()):
            continue

        linha_normalizada = {}
        for nome_coluna, valor in linha.items():
            campo = aliases.get(_normalizar_chave(nome_coluna))
            if not campo:
                continue
            texto_valor = _normalizar_texto(valor)
            if campo not in linha_normalizada or texto_valor:
                linha_normalizada[campo] = texto_valor

        linhas.append((indice_linha, linha_normalizada))

    if not linhas:
        raise ValueError("O CSV nao possui linhas de dados.")

    return linhas


def _parse_bool_csv(valor: str | None, *, padrao: bool = True) -> bool:
    texto = _normalizar_chave(valor)
    if not texto:
        return padrao
    if texto in VALORES_BOOLEANOS_TRUE:
        return True
    if texto in VALORES_BOOLEANOS_FALSE:
        return False
    raise ValueError("Use ativo/inativo, sim/nao ou 1/0 para a coluna de status.")


def _montar_resultado_importacao(
    *,
    entidade: str,
    linhas_processadas: int,
    criados: int,
    atualizados: int,
    detalhes_erros: list[str],
) -> dict:
    erros = len(detalhes_erros)
    total_importado = criados + atualizados
    mensagem = (
        f"Importacao de {entidade} concluida: "
        f"{criados} criado(s), {atualizados} atualizado(s)"
    )
    if erros:
        mensagem += f" e {erros} linha(s) com erro."
    else:
        mensagem += "."

    return {
        "mensagem": mensagem,
        "linhas_processadas": linhas_processadas,
        "importados": total_importado,
        "criados": criados,
        "atualizados": atualizados,
        "erros": erros,
        "detalhes_erros": detalhes_erros,
    }


def _resolver_turma_importacao(linha: dict[str, str]) -> int:
    turma_id_bruto = _normalizar_texto(linha.get("turma_id"))
    turma_bruta = _normalizar_texto(linha.get("turma"))

    turma = None
    if turma_id_bruto:
        if not turma_id_bruto.isdigit():
            raise ValueError("Turma invalida: o campo turma_id deve ser numerico.")
        turma = buscar_turma_por_id(int(turma_id_bruto))
    elif turma_bruta:
        if turma_bruta.isdigit():
            turma = buscar_turma_por_id(int(turma_bruta))
        if not turma:
            turma = buscar_turma_por_nome(turma_bruta, incluir_inativas=True)
    else:
        raise ValueError("Turma obrigatoria.")

    if not turma:
        identificador = turma_bruta or turma_id_bruto
        raise ValueError(f"Turma nao encontrada: {identificador}.")
    if int(turma.get("ativo") or 0) != 1:
        raise ValueError(f"Turma inativa: {turma.get('nome') or turma.get('id')}.")
    return int(turma["id"])


def importar_estudantes_csv(conteudo: bytes) -> dict:
    linhas = _carregar_linhas_csv(
        conteudo,
        colunas_aceitas=COLUNAS_ESTUDANTES,
        colunas_obrigatorias={"nome"},
    )

    criados = 0
    atualizados = 0
    detalhes_erros = []

    for indice_linha, linha in linhas:
        try:
            nome = _normalizar_texto(linha.get("nome"))
            if not nome:
                raise ValueError("Nome do estudante obrigatorio.")

            turma_id = _resolver_turma_importacao(linha)
            ativo = _parse_bool_csv(linha.get("ativo"), padrao=True)

            _estudante_id, criado = criar_ou_atualizar_estudante_por_nome_turma(
                nome=nome,
                turma_id=turma_id,
                ativo=ativo,
            )
            if criado:
                criados += 1
            else:
                atualizados += 1
        except ValueError as exc:
            detalhes_erros.append(f"Linha {indice_linha}: {exc}")

    return _montar_resultado_importacao(
        entidade="estudantes",
        linhas_processadas=len(linhas),
        criados=criados,
        atualizados=atualizados,
        detalhes_erros=detalhes_erros,
    )


def importar_base_legal_csv(conteudo: bytes) -> dict:
    linhas = _carregar_linhas_csv(
        conteudo,
        colunas_aceitas=COLUNAS_BASE_LEGAL,
        colunas_obrigatorias={"artigo", "descricao"},
    )

    criados = 0
    atualizados = 0
    detalhes_erros = []

    for indice_linha, linha in linhas:
        try:
            artigo = _normalizar_texto(linha.get("artigo"))
            descricao = _normalizar_texto(linha.get("descricao"))
            if not artigo:
                raise ValueError("Artigo ou referencia obrigatoria.")
            if not descricao:
                raise ValueError("Descricao obrigatoria.")

            ativo = _parse_bool_csv(linha.get("ativo"), padrao=True)
            _item_id, criado = criar_ou_atualizar_regimento_item_por_artigo(
                artigo=artigo,
                descricao=descricao,
                ativo=ativo,
            )
            if criado:
                criados += 1
            else:
                atualizados += 1
        except ValueError as exc:
            detalhes_erros.append(f"Linha {indice_linha}: {exc}")

    return _montar_resultado_importacao(
        entidade="base legal",
        linhas_processadas=len(linhas),
        criados=criados,
        atualizados=atualizados,
        detalhes_erros=detalhes_erros,
    )
