function renderTabelaRegimento() {
    const tbody = el("tbodyRegimento");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(regimentoItensCache) || regimentoItensCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "booking-empty";
        td.innerText = "Nenhum item da base legal cadastrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    regimentoItensCache.forEach((item) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Tipo", rotuloTipoBaseLegal(item.tipo)));
        tr.appendChild(criarCelulaTabela("Lei", item.lei_nome || ""));
        tr.appendChild(criarCelulaTabela("Referencia", item.artigo || ""));
        tr.appendChild(criarCelulaTabela("Descricao", item.descricao || ""));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoBaseLegal(item);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", () => {
            excluirBaseLegal(item);
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

function renderTabelaLeisBaseLegal() {
    const tbody = el("tbodyLeisBaseLegal");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(leisBaseLegalCache) || leisBaseLegalCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 2;
        td.className = "booking-empty";
        td.innerText = "Nenhuma lei cadastrada.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    leisBaseLegalCache.forEach((lei) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Lei", lei.nome || ""));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoLeiBaseLegal(lei);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", () => {
            excluirLeiBaseLegal(lei);
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));
        tbody.appendChild(tr);
    });
}

function sincronizarCatalogosBaseLegal({
    leis = [],
    artigos = [],
    incisos = [],
    alineas = []
} = {}) {
    leisBaseLegalCache = Array.isArray(leis) ? leis : [];
    artigosBaseLegalCache = Array.isArray(artigos) ? artigos : [];
    incisosBaseLegalCache = Array.isArray(incisos) ? incisos : [];
    alineasBaseLegalCache = Array.isArray(alineas) ? alineas : [];

    opcoesOcorrencias.leis = leisBaseLegalCache;
    opcoesOcorrencias.artigos = artigosBaseLegalCache;
    opcoesOcorrencias.incisos = incisosBaseLegalCache;
    opcoesOcorrencias.alineas = alineasBaseLegalCache;

    popularSugestoesLeisBaseLegal();
    popularSugestoesArtigosBaseLegal();
    popularSugestoesIncisosBaseLegal();
    renderTabelaLeisBaseLegal();
}

async function carregarCatalogosBaseLegal() {
    const [leis, artigos, incisos, alineas] = await Promise.all([
        fetchJson("/leis", { headers }),
        fetchJson("/artigos", { headers }),
        fetchJson("/incisos", { headers }),
        fetchJson("/alineas", { headers })
    ]);
    sincronizarCatalogosBaseLegal({ leis, artigos, incisos, alineas });
}

function rotuloTipoBaseLegal(tipo) {
    if (tipo === "inciso") return "Inciso";
    if (tipo === "alinea") return "Alinea";
    return "Artigo";
}

function limparFormularioLeiBaseLegal() {
    leiBaseLegalEmEdicao = null;
    el("formLeiBaseLegal").reset();
    el("tituloFormLeiBaseLegal").innerText = "Cadastrar lei";
    el("btnCancelarEdicaoLeiBaseLegal").style.display = "none";
}

function limparFormularioArtigoBaseLegal() {
    artigoBaseLegalEmEdicao = null;
    el("formArtigoBaseLegal").reset();
    el("artigoBaseLegalLeiId").value = "";
    el("tituloFormArtigoBaseLegal").innerText = "Cadastrar artigo";
    el("btnCancelarEdicaoArtigoBaseLegal").style.display = "none";
    ocultarSugestoes("listaLeisBaseLegal");
}

function limparFormularioIncisoBaseLegal() {
    incisoBaseLegalEmEdicao = null;
    el("formIncisoBaseLegal").reset();
    el("incisoBaseLegalArtigoId").value = "";
    el("tituloFormIncisoBaseLegal").innerText = "Cadastrar inciso";
    el("btnCancelarEdicaoIncisoBaseLegal").style.display = "none";
    ocultarSugestoes("listaArtigosBaseLegal");
}

function limparFormularioAlineaBaseLegal() {
    alineaBaseLegalEmEdicao = null;
    el("formAlineaBaseLegal").reset();
    el("alineaBaseLegalIncisoId").value = "";
    el("tituloFormAlineaBaseLegal").innerText = "Cadastrar alinea";
    el("btnCancelarEdicaoAlineaBaseLegal").style.display = "none";
    ocultarSugestoes("listaIncisosBaseLegal");
}

function iniciarEdicaoLeiBaseLegal(lei) {
    leiBaseLegalEmEdicao = lei;
    el("leiBaseLegalNome").value = lei.nome || "";
    el("tituloFormLeiBaseLegal").innerText = "Editar lei";
    el("btnCancelarEdicaoLeiBaseLegal").style.display = "inline-block";
    ativarAbaCoordenacao("regimento");
}

function iniciarEdicaoArtigoBaseLegal(artigo) {
    artigoBaseLegalEmEdicao = artigo;
    el("artigoBaseLegalLeiBusca").value = artigo.lei_nome || "";
    el("artigoBaseLegalLeiId").value = artigo.lei_id ? String(artigo.lei_id) : "";
    el("artigoBaseLegalNumero").value = artigo.numero || artigo.artigo_numero || "";
    el("artigoBaseLegalDescricao").value = artigo.descricao || artigo.artigo_descricao || "";
    el("tituloFormArtigoBaseLegal").innerText = "Editar artigo";
    el("btnCancelarEdicaoArtigoBaseLegal").style.display = "inline-block";
    ativarAbaCoordenacao("regimento");
}

function iniciarEdicaoIncisoBaseLegal(inciso) {
    incisoBaseLegalEmEdicao = inciso;
    el("incisoBaseLegalArtigoBusca").value = inciso.label || inciso.artigo || "";
    el("incisoBaseLegalArtigoId").value = inciso.artigo_id ? String(inciso.artigo_id) : "";
    el("incisoBaseLegalNumero").value = inciso.numero || inciso.inciso_numero || "";
    el("incisoBaseLegalDescricao").value = inciso.descricao || inciso.inciso_descricao || "";
    el("tituloFormIncisoBaseLegal").innerText = "Editar inciso";
    el("btnCancelarEdicaoIncisoBaseLegal").style.display = "inline-block";
    ativarAbaCoordenacao("regimento");
}

function iniciarEdicaoAlineaBaseLegal(alinea) {
    alineaBaseLegalEmEdicao = alinea;
    el("alineaBaseLegalIncisoBusca").value = alinea.label || alinea.artigo || "";
    el("alineaBaseLegalIncisoId").value = alinea.inciso_id ? String(alinea.inciso_id) : "";
    el("alineaBaseLegalIdentificador").value = alinea.identificador || alinea.alinea_identificador || "";
    el("alineaBaseLegalDescricao").value = alinea.descricao || alinea.alinea_descricao || "";
    el("tituloFormAlineaBaseLegal").innerText = "Editar alinea";
    el("btnCancelarEdicaoAlineaBaseLegal").style.display = "inline-block";
    ativarAbaCoordenacao("regimento");
}

function iniciarEdicaoBaseLegal(item) {
    if (!item) return;
    if (item.tipo === "inciso") {
        iniciarEdicaoIncisoBaseLegal({
            id: item.inciso_id,
            artigo_id: item.artigo_id,
            numero: item.inciso_numero,
            descricao: item.inciso_descricao,
            label: item.artigo
        });
        return;
    }
    if (item.tipo === "alinea") {
        iniciarEdicaoAlineaBaseLegal({
            id: item.alinea_id,
            inciso_id: item.inciso_id,
            identificador: item.alinea_identificador,
            descricao: item.alinea_descricao,
            label: item.artigo
        });
        return;
    }
    iniciarEdicaoArtigoBaseLegal({
        id: item.artigo_id,
        lei_id: item.lei_id,
        lei_nome: item.lei_nome,
        numero: item.artigo_numero,
        descricao: item.artigo_descricao
    });
}

function selecionarLeiBaseLegal(item) {
    if (!item) return;
    el("artigoBaseLegalLeiBusca").value = String(item.nome || item.label || "").trim();
    el("artigoBaseLegalLeiId").value = String(item.id || "");
}

function aplicarSelecaoLeiBaseLegalPorTexto() {
    const input = el("artigoBaseLegalLeiBusca");
    const hidden = el("artigoBaseLegalLeiId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaLeisBaseLegal");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaLeisBaseLegal, texto, leisBaseLegalCache);
    if (!item) {
        hidden.value = "";
        ocultarSugestoes("listaLeisBaseLegal");
        return;
    }

    selecionarLeiBaseLegal(item);
    ocultarSugestoes("listaLeisBaseLegal");
}

function atualizarSugestoesLeisBaseLegal(forcar = false) {
    const termo = el("artigoBaseLegalLeiBusca").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaLeisBaseLegal");
        return;
    }

    const itens = filtrarSugestoesLocais(leisBaseLegalCache, termo, {
        limite: 12,
        campos: ["nome", "label"]
    });
    preencherDatalist("listaLeisBaseLegal", mapaBuscaLeisBaseLegal, itens, {
        onSelect: selecionarLeiBaseLegal,
        textoVazio: leisBaseLegalCache.length === 0
            ? "Cadastre uma lei para continuar."
            : "Nenhuma lei encontrada."
    });
}

function selecionarArtigoBaseLegal(item) {
    if (!item) return;
    el("incisoBaseLegalArtigoBusca").value = String(item.label || item.referencia || "").trim();
    el("incisoBaseLegalArtigoId").value = String(item.id || "");
}

function aplicarSelecaoArtigoBaseLegalPorTexto() {
    const input = el("incisoBaseLegalArtigoBusca");
    const hidden = el("incisoBaseLegalArtigoId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaArtigosBaseLegal");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaArtigosBaseLegal, texto, artigosBaseLegalCache);
    if (!item) {
        hidden.value = "";
        ocultarSugestoes("listaArtigosBaseLegal");
        return;
    }

    selecionarArtigoBaseLegal(item);
    ocultarSugestoes("listaArtigosBaseLegal");
}

function atualizarSugestoesArtigosBaseLegal(forcar = false) {
    const termo = el("incisoBaseLegalArtigoBusca").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaArtigosBaseLegal");
        return;
    }

    const itens = filtrarSugestoesLocais(artigosBaseLegalCache, termo, {
        limite: 12,
        campos: ["label", "referencia", "numero", "descricao", "lei_nome"]
    });
    preencherDatalist("listaArtigosBaseLegal", mapaBuscaArtigosBaseLegal, itens, {
        onSelect: selecionarArtigoBaseLegal,
        textoVazio: artigosBaseLegalCache.length === 0
            ? "Cadastre um artigo para continuar."
            : "Nenhum artigo encontrado."
    });
}

function selecionarIncisoBaseLegal(item) {
    if (!item) return;
    el("alineaBaseLegalIncisoBusca").value = String(item.label || item.referencia || "").trim();
    el("alineaBaseLegalIncisoId").value = String(item.id || "");
}

function aplicarSelecaoIncisoBaseLegalPorTexto() {
    const input = el("alineaBaseLegalIncisoBusca");
    const hidden = el("alineaBaseLegalIncisoId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaIncisosBaseLegal");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaIncisosBaseLegal, texto, incisosBaseLegalCache);
    if (!item) {
        hidden.value = "";
        ocultarSugestoes("listaIncisosBaseLegal");
        return;
    }

    selecionarIncisoBaseLegal(item);
    ocultarSugestoes("listaIncisosBaseLegal");
}

function atualizarSugestoesIncisosBaseLegal(forcar = false) {
    const termo = el("alineaBaseLegalIncisoBusca").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaIncisosBaseLegal");
        return;
    }

    const itens = filtrarSugestoesLocais(incisosBaseLegalCache, termo, {
        limite: 12,
        campos: ["label", "referencia", "numero", "descricao", "lei_nome", "artigo_numero"]
    });
    preencherDatalist("listaIncisosBaseLegal", mapaBuscaIncisosBaseLegal, itens, {
        onSelect: selecionarIncisoBaseLegal,
        textoVazio: incisosBaseLegalCache.length === 0
            ? "Cadastre um inciso para continuar."
            : "Nenhum inciso encontrado."
    });
}

async function carregarRegimentoItens(idsSelecionados = null) {
    const idsPreferidos = idsSelecionados === null
        ? obterIdsRegimentoSelecionadosFormulario()
        : idsSelecionados;
    regimentoItensCache = await fetchJson("/regimento-itens?incluir_inativos=true", { headers });
    opcoesOcorrencias.regimento_itens = Array.isArray(regimentoItensCache)
        ? regimentoItensCache.map((item) => ({
            ...item,
            label: item.artigo || `Item ${item.id}`,
            ativo: true
        }))
        : [];
    popularSugestoesRegimento();
    renderTabelaRegimento();
    renderSelecionadorRegimento(idsPreferidos);
    atualizarPreviewOcorrencia();
}

async function salvarLeiBaseLegal(event) {
    event.preventDefault();
    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const payload = {
        nome: el("leiBaseLegalNome").value.trim()
    };

    try {
        if (leiBaseLegalEmEdicao) {
            await fetchJson(`/leis/${leiBaseLegalEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Lei atualizada com sucesso.");
        } else {
            await fetchJson("/leis", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Lei cadastrada com sucesso.");
        }

        limparFormularioLeiBaseLegal();
        await Promise.all([carregarCatalogosBaseLegal(), carregarRegimentoItens(idsSelecionados)]);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

async function salvarArtigoBaseLegal(event) {
    event.preventDefault();
    aplicarSelecaoLeiBaseLegalPorTexto();
    const leiId = Number(el("artigoBaseLegalLeiId").value || 0);
    if (leiId <= 0) {
        setMensagemRegimento("Selecione uma lei cadastrada para salvar o artigo.", true);
        return;
    }

    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const payload = {
        lei_id: leiId,
        numero: el("artigoBaseLegalNumero").value.trim(),
        descricao: el("artigoBaseLegalDescricao").value.trim()
    };

    try {
        if (artigoBaseLegalEmEdicao) {
            await fetchJson(`/artigos/${artigoBaseLegalEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Artigo atualizado com sucesso.");
        } else {
            await fetchJson("/artigos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Artigo cadastrado com sucesso.");
        }

        limparFormularioArtigoBaseLegal();
        await Promise.all([carregarCatalogosBaseLegal(), carregarRegimentoItens(idsSelecionados)]);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

async function salvarIncisoBaseLegal(event) {
    event.preventDefault();
    aplicarSelecaoArtigoBaseLegalPorTexto();
    const artigoId = Number(el("incisoBaseLegalArtigoId").value || 0);
    if (artigoId <= 0) {
        setMensagemRegimento("Selecione um artigo cadastrado para salvar o inciso.", true);
        return;
    }

    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const payload = {
        artigo_id: artigoId,
        numero: el("incisoBaseLegalNumero").value.trim(),
        descricao: el("incisoBaseLegalDescricao").value.trim()
    };

    try {
        if (incisoBaseLegalEmEdicao) {
            await fetchJson(`/incisos/${incisoBaseLegalEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Inciso atualizado com sucesso.");
        } else {
            await fetchJson("/incisos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Inciso cadastrado com sucesso.");
        }

        limparFormularioIncisoBaseLegal();
        await Promise.all([carregarCatalogosBaseLegal(), carregarRegimentoItens(idsSelecionados)]);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

async function salvarAlineaBaseLegal(event) {
    event.preventDefault();
    aplicarSelecaoIncisoBaseLegalPorTexto();
    const incisoId = Number(el("alineaBaseLegalIncisoId").value || 0);
    if (incisoId <= 0) {
        setMensagemRegimento("Selecione um inciso cadastrado para salvar a alinea.", true);
        return;
    }

    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const payload = {
        inciso_id: incisoId,
        identificador: el("alineaBaseLegalIdentificador").value.trim(),
        descricao: el("alineaBaseLegalDescricao").value.trim()
    };

    try {
        if (alineaBaseLegalEmEdicao) {
            await fetchJson(`/alineas/${alineaBaseLegalEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Alinea atualizada com sucesso.");
        } else {
            await fetchJson("/alineas", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Alinea cadastrada com sucesso.");
        }

        limparFormularioAlineaBaseLegal();
        await Promise.all([carregarCatalogosBaseLegal(), carregarRegimentoItens(idsSelecionados)]);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

function limparFormularioRegimento() {
    limparFormularioLeiBaseLegal();
    limparFormularioArtigoBaseLegal();
    limparFormularioIncisoBaseLegal();
    limparFormularioAlineaBaseLegal();
    el("tituloFormRegimento").innerText = "Cadastrar base legal";
}

function iniciarEdicaoRegimento(item) {
    iniciarEdicaoBaseLegal(item);
}

async function salvarRegimento(event) {
    if (event && typeof event.preventDefault === "function") {
        event.preventDefault();
    }
    setMensagemRegimento("Use os formularios separados de lei, artigo, inciso ou alinea.", true);
}

function limparSelecaoLeiBaseLegalSeNecessario(leiId) {
    if (Number(leiBaseLegalEmEdicao?.id || 0) === Number(leiId || 0)) {
        limparFormularioLeiBaseLegal();
    }
    if (Number(el("artigoBaseLegalLeiId")?.value || 0) === Number(leiId || 0)) {
        el("artigoBaseLegalLeiId").value = "";
        el("artigoBaseLegalLeiBusca").value = "";
    }
}

function limparSelecaoArtigoBaseLegalSeNecessario(artigoId) {
    if (Number(artigoBaseLegalEmEdicao?.id || 0) === Number(artigoId || 0)) {
        limparFormularioArtigoBaseLegal();
    }
    if (Number(el("incisoBaseLegalArtigoId")?.value || 0) === Number(artigoId || 0)) {
        el("incisoBaseLegalArtigoId").value = "";
        el("incisoBaseLegalArtigoBusca").value = "";
    }
}

function limparSelecaoIncisoBaseLegalSeNecessario(incisoId) {
    if (Number(incisoBaseLegalEmEdicao?.id || 0) === Number(incisoId || 0)) {
        limparFormularioIncisoBaseLegal();
    }
    if (Number(el("alineaBaseLegalIncisoId")?.value || 0) === Number(incisoId || 0)) {
        el("alineaBaseLegalIncisoId").value = "";
        el("alineaBaseLegalIncisoBusca").value = "";
    }
}

function limparSelecaoAlineaBaseLegalSeNecessario(alineaId) {
    if (Number(alineaBaseLegalEmEdicao?.id || 0) === Number(alineaId || 0)) {
        limparFormularioAlineaBaseLegal();
    }
}

async function excluirLeiBaseLegal(lei) {
    const nomeLei = String(lei?.nome || "esta lei").trim();
    const confirmou = window.confirm(
        `Excluir ${nomeLei}? A exclusao so sera permitida se nao houver artigos vinculados.`
    );
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/leis/${lei.id}`,
            `/leis/${lei.id}/excluir`
        );
        limparSelecaoLeiBaseLegalSeNecessario(lei.id);
        await Promise.all([
            carregarCatalogosBaseLegal(),
            carregarRegimentoItens(obterIdsRegimentoSelecionadosFormulario())
        ]);
        setMensagemRegimento(resposta?.mensagem || "Lei excluida com sucesso.");
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

async function excluirBaseLegal(item) {
    const tipo = rotuloTipoBaseLegal(item?.tipo).toLowerCase();
    const referencia = String(item?.artigo || item?.label || `este ${tipo}`).trim();
    const confirmou = window.confirm(
        `Excluir ${referencia}? A exclusao so sera permitida se nao houver dependencias ou ocorrencias vinculadas.`
    );
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/regimento-itens/${item.id}`,
            `/regimento-itens/${item.id}/excluir`
        );

        if (item?.tipo === "artigo") {
            limparSelecaoArtigoBaseLegalSeNecessario(item.artigo_id || item.id);
        } else if (item?.tipo === "inciso") {
            limparSelecaoIncisoBaseLegalSeNecessario(item.inciso_id);
        } else if (item?.tipo === "alinea") {
            limparSelecaoAlineaBaseLegalSeNecessario(item.alinea_id);
        }

        await Promise.all([
            carregarCatalogosBaseLegal(),
            carregarRegimentoItens(obterIdsRegimentoSelecionadosFormulario())
        ]);
        setMensagemRegimento(resposta?.mensagem || "Item da base legal excluido com sucesso.");
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

