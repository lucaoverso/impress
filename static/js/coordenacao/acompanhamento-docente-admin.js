let acompanhamentoDocenteCatalogo = {
    dimensions: [],
    criteria: [],
    models: [],
    record_types: [],
    modes: [],
    target_roles: []
};

function preencherSelectAcompanhamentoDocente(id, itens, valorAtual = "") {
    const select = el(id);
    if (!select) return;
    select.innerHTML = "";
    itens.forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.id);
        option.innerText = item.label || item.name || String(item.id);
        if (String(item.id) === String(valorAtual)) option.selected = true;
        select.appendChild(option);
    });
}

function criteriosDocentesAtivosPorTipo(tipo) {
    return acompanhamentoDocenteCatalogo.criteria.filter((criterio) => (
        criterio.active
        && criterio.target_role === "teacher"
        && (!tipo || criterio.record_type === tipo)
    ));
}

function atualizarSelectCriterioRegistroDocente() {
    const tipo = el("registroDocenteTipo")?.value || "positive";
    const criterios = criteriosDocentesAtivosPorTipo(tipo).map((criterio) => ({
        id: criterio.id,
        label: `${criterio.name} - ${criterio.dimension_name || "Sem dimensão"}`
    }));
    preencherSelectAcompanhamentoDocente("registroDocenteCriterio", criterios);
}

function renderAdminDimensoesDocente() {
    const lista = el("listaDimensoesDocente");
    if (!lista) return;
    lista.innerHTML = "";
    acompanhamentoDocenteCatalogo.dimensions.forEach((dimensao) => {
        const item = document.createElement("article");
        item.className = "acompanhamento-docente-admin-item";
        const titulo = document.createElement("strong");
        titulo.innerText = dimensao.name;
        const texto = document.createElement("span");
        texto.innerText = dimensao.description || "Sem descrição";
        item.appendChild(titulo);
        item.appendChild(texto);
        lista.appendChild(item);
    });
}

function editarCriterioDocente(criterio) {
    el("criterioDocenteId").value = String(criterio.id || "");
    el("criterioDocenteDimensao").value = String(criterio.dimension_id || "");
    el("criterioDocenteNome").value = criterio.name || "";
    el("criterioDocenteTipo").value = criterio.record_type || "positive";
    el("criterioDocenteModo").value = criterio.mode || "manual";
    el("criterioDocentePublico").value = criterio.target_role || "teacher";
    el("criterioDocenteDescricao").value = criterio.description || "";
    el("criterioDocenteAtivo").checked = Boolean(criterio.active);
    el("criterioDocenteNome")?.focus();
}

function limparFormularioCriterioDocente() {
    el("formCriterioDocente")?.reset();
    el("criterioDocenteId").value = "";
    el("criterioDocenteAtivo").checked = true;
}

function payloadCriterioDocente(criterio = null, ativo = null) {
    return {
        dimension_id: Number(el("criterioDocenteDimensao").value || criterio?.dimension_id || 0),
        name: el("criterioDocenteNome").value || criterio?.name || "",
        description: el("criterioDocenteDescricao").value || criterio?.description || "",
        record_type: el("criterioDocenteTipo").value || criterio?.record_type || "positive",
        mode: el("criterioDocenteModo").value || criterio?.mode || "manual",
        target_role: el("criterioDocentePublico").value || criterio?.target_role || "teacher",
        active: ativo === null ? Boolean(el("criterioDocenteAtivo").checked) : Boolean(ativo)
    };
}

async function alternarCriterioDocente(criterio) {
    await fetchJson(`/teacher-followup/criteria/${criterio.id}`, {
        method: "PATCH",
        headers: headersJson,
        body: JSON.stringify({
            dimension_id: Number(criterio.dimension_id),
            name: criterio.name,
            description: criterio.description || "",
            record_type: criterio.record_type,
            mode: criterio.mode,
            target_role: criterio.target_role,
            active: !criterio.active
        })
    });
    await carregarCatalogoAcompanhamentoDocente();
    setMensagemAcompanhamentoDocente("Critério atualizado.");
}

function renderAdminCriteriosDocente() {
    const lista = el("listaCriteriosDocente");
    if (!lista) return;
    lista.innerHTML = "";
    acompanhamentoDocenteCatalogo.criteria.forEach((criterio) => {
        const item = document.createElement("article");
        item.className = "acompanhamento-docente-admin-item";
        const titulo = document.createElement("strong");
        titulo.innerText = criterio.name;
        const meta = document.createElement("span");
        meta.innerText = [
            criterio.dimension_name,
            criterio.record_type_label,
            criterio.mode_label,
            criterio.target_role_label,
            criterio.active ? "Ativo" : "Inativo"
        ].filter(Boolean).join(" - ");
        const descricao = document.createElement("p");
        descricao.innerText = criterio.description || "Sem descrição";
        const actions = document.createElement("div");
        actions.className = "acompanhamento-docente-admin-actions";
        const editar = document.createElement("button");
        editar.type = "button";
        editar.innerText = "Editar";
        editar.addEventListener("click", () => editarCriterioDocente(criterio));
        const alternar = document.createElement("button");
        alternar.type = "button";
        alternar.innerText = criterio.active ? "Desativar" : "Ativar";
        alternar.addEventListener("click", () => {
            alternarCriterioDocente(criterio).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
        });
        actions.appendChild(editar);
        actions.appendChild(alternar);
        item.appendChild(titulo);
        item.appendChild(meta);
        item.appendChild(descricao);
        item.appendChild(actions);
        lista.appendChild(item);
    });
}

function renderAdminModelosDocente() {
    const lista = el("listaModelosDocente");
    if (!lista) return;
    lista.innerHTML = "";
    acompanhamentoDocenteCatalogo.models.forEach((modelo) => {
        const item = document.createElement("article");
        item.className = "acompanhamento-docente-admin-item";
        const titulo = document.createElement("strong");
        titulo.innerText = modelo.name;
        const meta = document.createElement("span");
        meta.innerText = `${modelo.target_role_label || modelo.target_role} - ${modelo.active ? "Ativo" : "Inativo"}`;
        const texto = document.createElement("p");
        texto.innerText = modelo.description || "Modelo preparado para critérios selecionados.";
        item.appendChild(titulo);
        item.appendChild(meta);
        item.appendChild(texto);
        lista.appendChild(item);
    });
}

function renderCatalogoAcompanhamentoDocente() {
    preencherSelectAcompanhamentoDocente(
        "criterioDocenteDimensao",
        acompanhamentoDocenteCatalogo.dimensions
    );
    preencherSelectAcompanhamentoDocente(
        "criterioDocenteTipo",
        acompanhamentoDocenteCatalogo.record_types
    );
    preencherSelectAcompanhamentoDocente(
        "criterioDocenteModo",
        acompanhamentoDocenteCatalogo.modes
    );
    preencherSelectAcompanhamentoDocente(
        "criterioDocentePublico",
        acompanhamentoDocenteCatalogo.target_roles
    );
    preencherSelectAcompanhamentoDocente(
        "modeloDocentePublico",
        acompanhamentoDocenteCatalogo.target_roles
    );
    preencherSelectAcompanhamentoDocente(
        "modeloDocenteCriterios",
        acompanhamentoDocenteCatalogo.criteria.map((criterio) => ({
            id: criterio.id,
            label: `${criterio.name} - ${criterio.target_role_label || criterio.target_role}`
        }))
    );
    atualizarSelectCriterioRegistroDocente();
    renderAdminDimensoesDocente();
    renderAdminCriteriosDocente();
    renderAdminModelosDocente();
}

async function carregarCatalogoAcompanhamentoDocente() {
    const resposta = await fetchJson("/teacher-followup/catalog", { headers });
    acompanhamentoDocenteCatalogo = {
        dimensions: Array.isArray(resposta.dimensions) ? resposta.dimensions : [],
        criteria: Array.isArray(resposta.criteria) ? resposta.criteria : [],
        models: Array.isArray(resposta.models) ? resposta.models : [],
        record_types: Array.isArray(resposta.record_types) ? resposta.record_types : [],
        modes: Array.isArray(resposta.modes) ? resposta.modes : [],
        target_roles: Array.isArray(resposta.target_roles) ? resposta.target_roles : []
    };
    renderCatalogoAcompanhamentoDocente();
}

async function salvarDimensaoDocente(event) {
    event.preventDefault();
    await fetchJson("/teacher-followup/dimensions", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            name: el("dimensaoDocenteNome").value,
            description: el("dimensaoDocenteDescricao").value,
            active: true
        })
    });
    el("formDimensaoDocente")?.reset();
    await carregarCatalogoAcompanhamentoDocente();
    setMensagemAcompanhamentoDocente("Dimensão salva.");
}

async function salvarCriterioDocente(event) {
    event.preventDefault();
    const criterioId = Number(el("criterioDocenteId").value || 0);
    await fetchJson(criterioId ? `/teacher-followup/criteria/${criterioId}` : "/teacher-followup/criteria", {
        method: criterioId ? "PATCH" : "POST",
        headers: headersJson,
        body: JSON.stringify(payloadCriterioDocente())
    });
    limparFormularioCriterioDocente();
    await carregarCatalogoAcompanhamentoDocente();
    setMensagemAcompanhamentoDocente("Critério salvo.");
}

async function salvarModeloDocente(event) {
    event.preventDefault();
    const criterios = Array.from(el("modeloDocenteCriterios").selectedOptions || [])
        .map((option) => Number(option.value))
        .filter(Boolean);
    await fetchJson("/teacher-followup/models", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            name: el("modeloDocenteNome").value,
            target_role: el("modeloDocentePublico").value,
            description: el("modeloDocenteDescricao").value,
            criterion_ids: criterios,
            active: true
        })
    });
    el("formModeloDocente")?.reset();
    await carregarCatalogoAcompanhamentoDocente();
    setMensagemAcompanhamentoDocente("Modelo salvo.");
}

function registrarEventosAdminAcompanhamentoDocente() {
    el("formDimensaoDocente")?.addEventListener("submit", (event) => {
        salvarDimensaoDocente(event).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("formCriterioDocente")?.addEventListener("submit", (event) => {
        salvarCriterioDocente(event).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("formModeloDocente")?.addEventListener("submit", (event) => {
        salvarModeloDocente(event).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("btnCancelarEdicaoCriterioDocente")?.addEventListener("click", limparFormularioCriterioDocente);
    el("registroDocenteTipo")?.addEventListener("change", atualizarSelectCriterioRegistroDocente);
}
