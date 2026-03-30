from __future__ import annotations

import csv
import io
import json
import unicodedata

from database import (
    LEI_PADRAO_IMPORTACAO,
    buscar_turma_por_id,
    buscar_turma_por_nome,
    criar_ou_atualizar_estudante_por_nome_turma,
    criar_ou_atualizar_regimento_item,
)

LIMITE_ARQUIVO_IMPORTACAO_BYTES = 2 * 1024 * 1024

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
    "lei_nome": {
        "lei_nome",
        "lei",
        "nome_lei",
        "base_legal",
        "nome_base_legal",
    },
    "artigo_numero": {
        "artigo_numero",
        "artigo",
        "numero_artigo",
        "referencia",
        "item",
    },
    "artigo_descricao": {
        "artigo_descricao",
        "descricao_artigo",
        "descricao",
        "texto",
        "conteudo",
        "detalhe",
        "trecho",
    },
    "inciso_numero": {
        "inciso_numero",
        "inciso",
        "numero_inciso",
    },
    "inciso_descricao": {
        "inciso_descricao",
        "descricao_inciso",
    },
    "alinea_identificador": {
        "alinea_identificador",
        "alinea",
        "identificador_alinea",
    },
    "alinea_descricao": {
        "alinea_descricao",
        "descricao_alinea",
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


def _decodificar_texto_importacao(conteudo: bytes, *, formato: str = "arquivo") -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Nao foi possivel ler o {formato}. Salve-o em UTF-8.")


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
    if len(conteudo) > LIMITE_ARQUIVO_IMPORTACAO_BYTES:
        raise ValueError("Arquivo CSV muito grande. Envie um arquivo de ate 2 MB.")

    texto = _decodificar_texto_importacao(conteudo, formato="arquivo CSV")
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


def _obter_valor_json(objeto: dict, *aliases: str):
    if not isinstance(objeto, dict):
        return None

    mapa = {
        _normalizar_chave(chave): valor
        for chave, valor in objeto.items()
    }
    for alias in aliases:
        chave = _normalizar_chave(alias)
        if chave in mapa:
            return mapa[chave]
    return None


def _texto_json(valor) -> str:
    return _normalizar_texto("" if valor is None else str(valor))


def _lista_json(valor, *, campo: str) -> list:
    if valor is None:
        return []
    if not isinstance(valor, list):
        raise ValueError(f"O campo {campo} deve ser uma lista.")
    return valor


def _identificador_item_base_legal(
    *,
    lei_nome: str,
    artigo_numero: str,
    inciso_numero: str | None = None,
    alinea_identificador: str | None = None,
) -> str:
    partes = [lei_nome or LEI_PADRAO_IMPORTACAO, f"Art. {artigo_numero}"]
    if _normalizar_texto(inciso_numero):
        partes.append(f"inciso {_normalizar_texto(inciso_numero)}")
    if _normalizar_texto(alinea_identificador):
        partes.append(f"alinea {_normalizar_texto(alinea_identificador)}")
    return " > ".join(partes)


def _extrair_linhas_base_legal_json(conteudo: bytes) -> list[tuple[str, dict[str, str]]]:
    if not conteudo:
        raise ValueError("Arquivo JSON vazio.")
    if len(conteudo) > LIMITE_ARQUIVO_IMPORTACAO_BYTES:
        raise ValueError("Arquivo JSON muito grande. Envie um arquivo de ate 2 MB.")

    texto = _decodificar_texto_importacao(conteudo, formato="arquivo JSON")
    if not texto.strip():
        raise ValueError("Arquivo JSON vazio.")

    try:
        payload = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON invalido para importacao da base legal.") from exc

    if isinstance(payload, list):
        leis = payload
    elif isinstance(payload, dict):
        leis = _obter_valor_json(payload, "leis")
        if leis is None:
            leis = [payload]
    else:
        raise ValueError("JSON invalido: informe um objeto ou lista de leis.")

    leis = _lista_json(leis, campo="leis")
    linhas: list[tuple[str, dict[str, str]]] = []

    for indice_lei, lei_item in enumerate(leis, start=1):
        if not isinstance(lei_item, dict):
            raise ValueError(f"Lei #{indice_lei}: estrutura invalida.")

        lei_nome = _texto_json(
            _obter_valor_json(lei_item, "lei", "lei_nome", "nome")
        ) or LEI_PADRAO_IMPORTACAO
        artigos = _lista_json(
            _obter_valor_json(lei_item, "artigos"),
            campo=f"artigos da lei {lei_nome}",
        )
        if not artigos:
            raise ValueError(f"Lei {lei_nome}: informe ao menos um artigo.")

        for artigo_item in artigos:
            if not isinstance(artigo_item, dict):
                raise ValueError(f"Lei {lei_nome}: artigo com estrutura invalida.")

            artigo_numero = _texto_json(
                _obter_valor_json(artigo_item, "numero", "artigo_numero", "artigo")
            )
            artigo_descricao = _texto_json(
                _obter_valor_json(artigo_item, "descricao", "artigo_descricao", "texto")
            )
            if not artigo_numero:
                raise ValueError(f"Lei {lei_nome}: numero do artigo obrigatorio.")
            if not artigo_descricao:
                raise ValueError(f"Lei {lei_nome} > Art. {artigo_numero}: descricao do artigo obrigatoria.")

            linhas.append((
                _identificador_item_base_legal(
                    lei_nome=lei_nome,
                    artigo_numero=artigo_numero,
                ),
                {
                    "lei_nome": lei_nome,
                    "artigo_numero": artigo_numero,
                    "artigo_descricao": artigo_descricao,
                    "inciso_numero": "",
                    "inciso_descricao": "",
                    "alinea_identificador": "",
                    "alinea_descricao": "",
                }
            ))

            incisos = _lista_json(
                _obter_valor_json(artigo_item, "incisos"),
                campo=f"incisos do artigo {artigo_numero}",
            )
            for inciso_item in incisos:
                if not isinstance(inciso_item, dict):
                    raise ValueError(f"Lei {lei_nome} > Art. {artigo_numero}: inciso com estrutura invalida.")

                inciso_numero = _texto_json(
                    _obter_valor_json(inciso_item, "numero", "inciso_numero", "inciso")
                )
                inciso_descricao = _texto_json(
                    _obter_valor_json(inciso_item, "descricao", "inciso_descricao", "texto")
                )
                if not inciso_numero:
                    raise ValueError(f"Lei {lei_nome} > Art. {artigo_numero}: numero do inciso obrigatorio.")
                if not inciso_descricao:
                    raise ValueError(
                        f"Lei {lei_nome} > Art. {artigo_numero} > inciso {inciso_numero}: descricao do inciso obrigatoria."
                    )

                linhas.append((
                    _identificador_item_base_legal(
                        lei_nome=lei_nome,
                        artigo_numero=artigo_numero,
                        inciso_numero=inciso_numero,
                    ),
                    {
                        "lei_nome": lei_nome,
                        "artigo_numero": artigo_numero,
                        "artigo_descricao": artigo_descricao,
                        "inciso_numero": inciso_numero,
                        "inciso_descricao": inciso_descricao,
                        "alinea_identificador": "",
                        "alinea_descricao": "",
                    }
                ))

                alineas = _lista_json(
                    _obter_valor_json(inciso_item, "alineas"),
                    campo=f"alineas do inciso {inciso_numero}",
                )
                for alinea_item in alineas:
                    if not isinstance(alinea_item, dict):
                        raise ValueError(
                            f"Lei {lei_nome} > Art. {artigo_numero} > inciso {inciso_numero}: alinea com estrutura invalida."
                        )

                    alinea_identificador = _texto_json(
                        _obter_valor_json(alinea_item, "identificador", "alinea_identificador", "alinea")
                    )
                    alinea_descricao = _texto_json(
                        _obter_valor_json(alinea_item, "descricao", "alinea_descricao", "texto")
                    )
                    if not alinea_identificador:
                        raise ValueError(
                            f"Lei {lei_nome} > Art. {artigo_numero} > inciso {inciso_numero}: identificador da alinea obrigatorio."
                        )
                    if not alinea_descricao:
                        raise ValueError(
                            f"Lei {lei_nome} > Art. {artigo_numero} > inciso {inciso_numero} > alinea {alinea_identificador}: descricao da alinea obrigatoria."
                        )

                    linhas.append((
                        _identificador_item_base_legal(
                            lei_nome=lei_nome,
                            artigo_numero=artigo_numero,
                            inciso_numero=inciso_numero,
                            alinea_identificador=alinea_identificador,
                        ),
                        {
                            "lei_nome": lei_nome,
                            "artigo_numero": artigo_numero,
                            "artigo_descricao": artigo_descricao,
                            "inciso_numero": inciso_numero,
                            "inciso_descricao": inciso_descricao,
                            "alinea_identificador": alinea_identificador,
                            "alinea_descricao": alinea_descricao,
                        }
                    ))

    if not linhas:
        raise ValueError("O JSON nao possui itens de base legal para importar.")
    return linhas


def _importar_linhas_base_legal(linhas: list[tuple[int | str, dict[str, str]]]) -> dict:
    criados = 0
    atualizados = 0
    detalhes_erros = []

    for origem, linha in linhas:
        try:
            lei_nome = _normalizar_texto(linha.get("lei_nome")) or LEI_PADRAO_IMPORTACAO
            artigo_numero = _normalizar_texto(linha.get("artigo_numero"))
            artigo_descricao = _normalizar_texto(linha.get("artigo_descricao"))
            inciso_numero = _normalizar_texto(linha.get("inciso_numero"))
            inciso_descricao = _normalizar_texto(linha.get("inciso_descricao"))
            alinea_identificador = _normalizar_texto(linha.get("alinea_identificador"))
            alinea_descricao = _normalizar_texto(linha.get("alinea_descricao"))

            if not artigo_numero:
                raise ValueError("Numero do artigo obrigatorio.")
            if not artigo_descricao:
                raise ValueError("Descricao do artigo obrigatoria.")
            if bool(inciso_numero) != bool(inciso_descricao):
                raise ValueError("Inciso e descricao do inciso devem ser informados juntos.")
            if alinea_identificador and not inciso_numero:
                raise ValueError("Informe um inciso antes de cadastrar uma alinea.")
            if bool(alinea_identificador) != bool(alinea_descricao):
                raise ValueError("Alinea e descricao da alinea devem ser informadas juntas.")

            _item_id, criado = criar_ou_atualizar_regimento_item(
                lei_nome=lei_nome,
                artigo_numero=artigo_numero,
                artigo_descricao=artigo_descricao,
                inciso_numero=inciso_numero or None,
                inciso_descricao=inciso_descricao or None,
                alinea_identificador=alinea_identificador or None,
                alinea_descricao=alinea_descricao or None,
            )
            if criado:
                criados += 1
            else:
                atualizados += 1
        except ValueError as exc:
            prefixo = f"Linha {origem}" if isinstance(origem, int) else f"Item {origem}"
            detalhes_erros.append(f"{prefixo}: {exc}")

    return _montar_resultado_importacao(
        entidade="base legal",
        linhas_processadas=len(linhas),
        criados=criados,
        atualizados=atualizados,
        detalhes_erros=detalhes_erros,
    )


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
        colunas_obrigatorias={"artigo_numero", "artigo_descricao"},
    )
    return _importar_linhas_base_legal(linhas)


def importar_base_legal_json(conteudo: bytes) -> dict:
    linhas = _extrair_linhas_base_legal_json(conteudo)
    return _importar_linhas_base_legal(linhas)


def importar_base_legal_arquivo(
    conteudo: bytes,
    *,
    nome_arquivo: str | None = None,
    tipo_conteudo: str | None = None,
) -> dict:
    nome = _normalizar_texto(nome_arquivo).lower()
    tipo = _normalizar_texto(tipo_conteudo).lower()

    if nome.endswith(".json") or "json" in tipo:
        return importar_base_legal_json(conteudo)
    if nome.endswith(".csv") or "csv" in tipo:
        return importar_base_legal_csv(conteudo)

    texto = _decodificar_texto_importacao(conteudo)
    if texto.lstrip().startswith("{") or texto.lstrip().startswith("["):
        return importar_base_legal_json(conteudo)
    return importar_base_legal_csv(conteudo)
