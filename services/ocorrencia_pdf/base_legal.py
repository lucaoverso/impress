from __future__ import annotations

import re


def _formatar_linha_artigo(
    numero: str | None, descricao: str | None, rotulo_legado: str | None = None
) -> str:
    numero_limpo = re.sub(r"^art\.?\s*", "", str(numero or "").strip(), flags=re.IGNORECASE)
    descricao_limpa = str(descricao or "").strip()
    if numero_limpo:
        prefixo = f"Art. {numero_limpo}."
        return f"{prefixo} {descricao_limpa}".strip() if descricao_limpa else prefixo
    return str(rotulo_legado or descricao_limpa or "Sem artigo").strip() or "Sem artigo"


def _formatar_linha_inciso(numero: str | None, descricao: str | None) -> str:
    numero_limpo = str(numero or "").strip()
    descricao_limpa = str(descricao or "").strip()
    if numero_limpo and descricao_limpa:
        return f"{numero_limpo} - {descricao_limpa}"
    return numero_limpo or descricao_limpa


def _formatar_linha_alinea(identificador: str | None, descricao: str | None) -> str:
    identificador_limpo = str(identificador or "").strip()
    descricao_limpa = str(descricao or "").strip()
    if identificador_limpo and descricao_limpa:
        return f"{identificador_limpo}) {descricao_limpa}"
    return identificador_limpo or descricao_limpa


def _normalizar_texto_chave(valor: str | None) -> str:
    return re.sub(r"\s+", " ", str(valor or "").strip()).casefold()


def _limpar_rotulo_artigo_legado(rotulo: str | None) -> str:
    texto = str(rotulo or "").strip()
    if not texto:
        return ""
    if " - Art." in texto:
        texto = f"Art.{texto.split(' - Art.', 1)[1]}"
    texto = re.sub(r",?\s*alinea\s+[a-z]\b.*$", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r",?\s*inciso\s+[IVXLCDM]+\b.*$", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s*-\s*[IVXLCDM]+\b.*$", "", texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip(" ,;-")


def _montar_chave_artigo(item: dict, chave_lei: str, ordem: int) -> str | int:
    artigo_id = item.get("artigo_id")
    if artigo_id is not None and int(artigo_id) > 0:
        return int(artigo_id)
    artigo_numero = _normalizar_texto_chave(item.get("artigo_numero"))
    if artigo_numero:
        return f"{chave_lei}|artigo|{artigo_numero}"
    rotulo_legado = _normalizar_texto_chave(_limpar_rotulo_artigo_legado(item.get("artigo")))
    if rotulo_legado:
        return f"{chave_lei}|artigo-legado|{rotulo_legado}"
    return f"{chave_lei}|artigo-ordem|{ordem}"


def _montar_chave_inciso(item: dict, chave_artigo: str | int, ordem: int) -> str | int:
    inciso_id = item.get("inciso_id")
    if inciso_id is not None and int(inciso_id) > 0:
        return int(inciso_id)
    inciso_numero = _normalizar_texto_chave(item.get("inciso_numero"))
    if inciso_numero:
        return f"{chave_artigo}|inciso|{inciso_numero}"
    return f"{chave_artigo}|inciso-ordem|{ordem}"


def _montar_chave_alinea(item: dict, chave_inciso: str | int, ordem: int) -> str | int:
    alinea_id = item.get("alinea_id")
    if alinea_id is not None and int(alinea_id) > 0:
        return int(alinea_id)
    alinea_identificador = _normalizar_texto_chave(item.get("alinea_identificador"))
    if alinea_identificador:
        return f"{chave_inciso}|alinea|{alinea_identificador}"
    return f"{chave_inciso}|alinea-ordem|{ordem}"


def _obter_itens_regimento_ocorrencia(ocorrencia: dict) -> list[dict]:
    itens = ocorrencia.get("regimento_itens")
    if not isinstance(itens, list):
        return []

    regex_artigo = re.compile(r"Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)", re.IGNORECASE)
    regex_inciso = re.compile(r"(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)", re.IGNORECASE)
    regex_alinea = re.compile(r"alinea\s+([a-z])\b", re.IGNORECASE)

    itens_norm = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        artigo = str(item.get("artigo") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        if not artigo and not descricao:
            continue

        lei_nome = str(item.get("lei_nome") or "").strip()
        artigo_numero = str(item.get("artigo_numero") or "").strip()
        artigo_descricao = str(item.get("artigo_descricao") or "").strip()
        inciso_numero = str(item.get("inciso_numero") or "").strip()
        inciso_descricao = str(item.get("inciso_descricao") or "").strip()
        alinea_identificador = str(item.get("alinea_identificador") or "").strip()
        alinea_descricao = str(item.get("alinea_descricao") or "").strip()

        if not lei_nome and " - Art." in artigo:
            lei_nome = artigo.split(" - Art.", 1)[0].strip()
        if not artigo_numero:
            match_artigo = regex_artigo.search(artigo)
            if match_artigo:
                artigo_numero = str(match_artigo.group(1) or "").strip()
        if not inciso_numero:
            match_inciso = regex_inciso.search(artigo)
            if match_inciso:
                inciso_numero = str(match_inciso.group(1) or match_inciso.group(2) or "").strip()
        if not alinea_identificador:
            match_alinea = regex_alinea.search(artigo)
            if match_alinea:
                alinea_identificador = str(match_alinea.group(1) or "").strip()

        tipo = str(item.get("tipo") or "").strip().lower()
        if not tipo:
            if alinea_identificador or item.get("alinea_id") is not None:
                tipo = "alinea"
            elif inciso_numero or item.get("inciso_id") is not None:
                tipo = "inciso"
            else:
                tipo = "artigo"
        if tipo == "artigo" and not artigo_descricao:
            artigo_descricao = descricao
        if tipo == "inciso" and not inciso_descricao:
            inciso_descricao = descricao
        if tipo == "alinea" and not alinea_descricao:
            alinea_descricao = descricao

        itens_norm.append(
            {
                "tipo": tipo,
                "artigo_id": int(item["artigo_id"]) if item.get("artigo_id") is not None else None,
                "inciso_id": int(item["inciso_id"]) if item.get("inciso_id") is not None else None,
                "alinea_id": int(item["alinea_id"]) if item.get("alinea_id") is not None else None,
                "lei_nome": lei_nome or None,
                "artigo_numero": artigo_numero or None,
                "artigo_descricao": artigo_descricao or None,
                "inciso_numero": inciso_numero or None,
                "inciso_descricao": inciso_descricao or None,
                "alinea_identificador": alinea_identificador or None,
                "alinea_descricao": alinea_descricao or None,
                "artigo": artigo or "Sem artigo",
                "descricao": descricao,
                "ordem": int(item.get("ordem") or 0),
            }
        )
    return sorted(itens_norm, key=lambda item: (item.get("ordem", 0), item.get("artigo", "")))


def _montar_blocos_base_legal(itens: list[dict]) -> list[dict]:
    if not itens:
        return []
    itens = _obter_itens_regimento_ocorrencia({"regimento_itens": itens})
    if not itens:
        return []

    leis: dict[str, dict] = {}
    for item in itens:
        lei_nome = str(item.get("lei_nome") or "").strip()
        artigo_numero = str(item.get("artigo_numero") or "").strip()
        artigo_descricao = str(item.get("artigo_descricao") or "").strip()
        inciso_numero = str(item.get("inciso_numero") or "").strip()
        inciso_descricao = str(item.get("inciso_descricao") or "").strip()
        alinea_identificador = str(item.get("alinea_identificador") or "").strip()
        alinea_descricao = str(item.get("alinea_descricao") or "").strip()
        ordem = int(item.get("ordem") or 0)
        tipo = str(item.get("tipo") or "").strip().lower() or "artigo"

        chave_lei = lei_nome or "__sem_lei__"
        lei = leis.setdefault(chave_lei, {"nome": lei_nome, "ordem": ordem, "artigos": {}})
        lei["ordem"] = min(int(lei.get("ordem") or ordem), ordem)

        chave_artigo = _montar_chave_artigo(item, chave_lei, ordem)
        artigo = lei["artigos"].setdefault(
            chave_artigo,
            {
                "ordem": ordem,
                "numero": artigo_numero,
                "descricao": artigo_descricao,
                "rotulo_legado": str(item.get("artigo") or "").strip(),
                "incisos": {},
            },
        )
        artigo["ordem"] = min(int(artigo.get("ordem") or ordem), ordem)
        if artigo_numero and not artigo.get("numero"):
            artigo["numero"] = artigo_numero
        if artigo_descricao and not artigo.get("descricao"):
            artigo["descricao"] = artigo_descricao
        if str(item.get("artigo") or "").strip() and not artigo.get("rotulo_legado"):
            artigo["rotulo_legado"] = str(item.get("artigo") or "").strip()
        if tipo == "artigo" and not inciso_numero and not alinea_identificador:
            continue

        chave_inciso = _montar_chave_inciso(item, chave_artigo, ordem)
        inciso = artigo["incisos"].setdefault(
            chave_inciso,
            {"ordem": ordem, "numero": inciso_numero, "descricao": inciso_descricao, "alineas": {}},
        )
        inciso["ordem"] = min(int(inciso.get("ordem") or ordem), ordem)
        if inciso_numero and not inciso.get("numero"):
            inciso["numero"] = inciso_numero
        if inciso_descricao and not inciso.get("descricao"):
            inciso["descricao"] = inciso_descricao
        if tipo != "alinea" and not alinea_identificador:
            continue

        chave_alinea = _montar_chave_alinea(item, chave_inciso, ordem)
        alinea = inciso["alineas"].setdefault(
            chave_alinea,
            {"ordem": ordem, "identificador": alinea_identificador, "descricao": alinea_descricao},
        )
        alinea["ordem"] = min(int(alinea.get("ordem") or ordem), ordem)
        if alinea_identificador and not alinea.get("identificador"):
            alinea["identificador"] = alinea_identificador
        if alinea_descricao and not alinea.get("descricao"):
            alinea["descricao"] = alinea_descricao

    blocos: list[dict] = []
    leis_ordenadas = sorted(leis.values(), key=lambda lei: (int(lei.get("ordem") or 0), str(lei.get("nome") or "").lower()))
    total_leis_nomeadas = len([lei for lei in leis_ordenadas if str(lei.get("nome") or "").strip()])
    mostrar_lei = total_leis_nomeadas > 1

    for lei in leis_ordenadas:
        nome_lei = str(lei.get("nome") or "").strip()
        if mostrar_lei and nome_lei:
            blocos.append({"tipo": "lei", "texto": nome_lei})
        artigos_ordenados = sorted(
            lei["artigos"].values(),
            key=lambda artigo: (int(artigo.get("ordem") or 0), str(artigo.get("numero") or "")),
        )
        for artigo in artigos_ordenados:
            blocos.append(
                {
                    "tipo": "artigo",
                    "texto": _formatar_linha_artigo(
                        artigo.get("numero"),
                        artigo.get("descricao"),
                        artigo.get("rotulo_legado"),
                    ),
                }
            )
            incisos_ordenados = sorted(
                artigo["incisos"].values(),
                key=lambda inciso: (int(inciso.get("ordem") or 0), str(inciso.get("numero") or "")),
            )
            for inciso in incisos_ordenados:
                texto_inciso = _formatar_linha_inciso(inciso.get("numero"), inciso.get("descricao"))
                if texto_inciso:
                    blocos.append({"tipo": "inciso", "texto": texto_inciso})
                alineas_ordenadas = sorted(
                    inciso["alineas"].values(),
                    key=lambda alinea: (int(alinea.get("ordem") or 0), str(alinea.get("identificador") or "")),
                )
                for alinea in alineas_ordenadas:
                    texto_alinea = _formatar_linha_alinea(
                        alinea.get("identificador"),
                        alinea.get("descricao"),
                    )
                    if texto_alinea:
                        blocos.append({"tipo": "alinea", "texto": texto_alinea})
    return blocos
