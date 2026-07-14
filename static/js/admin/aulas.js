let configuracaoAulaEmEdicaoId = null;

function atualizarFormularioTipoConfiguracaoAula() {
    const input = el("configAulaNumero");
    if (!input) return;
    const ehAula = tipoConfiguracaoAula({ tipo: el("configAulaTipo")?.value }) === "AULA";
    input.disabled = !ehAula;
    input.required = ehAula;
    input.placeholder = ehAula ? "Número global da aula" : "Não se aplica para intervalo";
    if (!ehAula) input.value = "";
}

function limparFormularioConfiguracaoAula() {
    configuracaoAulaEmEdicaoId = null;
    el("formConfiguracaoAula")?.reset();
    if (el("configAulaTipo")) el("configAulaTipo").value = "AULA";
    if (el("configAulaAtivo")) el("configAulaAtivo").checked = true;
    if (el("tituloFormConfiguracaoAula")) el("tituloFormConfiguracaoAula").innerText = "Cadastrar aula";
    if (el("btnSalvarConfiguracaoAula")) el("btnSalvarConfiguracaoAula").innerText = "Cadastrar aula";
    if (el("btnCancelarEdicaoConfiguracaoAula")) el("btnCancelarEdicaoConfiguracaoAula").style.display = "none";
    atualizarFormularioTipoConfiguracaoAula();
}

function preencherFormularioConfiguracaoAula(item) {
    if (!item) return limparFormularioConfiguracaoAula();
    configuracaoAulaEmEdicaoId = Number(item.id || 0);
    el("configAulaTipo").value = tipoConfiguracaoAula(item);
    el("configAulaNome").value = String(item.nome || "");
    el("configAulaNumero").value = item.aula_numero ? String(item.aula_numero) : "";
    el("configAulaOrdemVisual").value = String(item.ordem_visual || "");
    el("configAulaHorarioInicio").value = String(item.horario_inicio || "");
    el("configAulaHorarioFim").value = String(item.horario_fim || "");
    el("configAulaAtivo").checked = Boolean(item.ativo);
    el("tituloFormConfiguracaoAula").innerText = "Editar item da grade";
    el("btnSalvarConfiguracaoAula").innerText = "Atualizar item";
    el("btnCancelarEdicaoConfiguracaoAula").style.display = "inline-flex";
    atualizarFormularioTipoConfiguracaoAula();
}

function renderListaConfiguracoesAulasAdmin() {
    const lista = el("listaConfiguracaoAulasAdmin");
    if (!lista) return;
    lista.innerHTML = "";
    if (!configuracoesAulasAdmin.length) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhum item configurado na grade escolar.";
        lista.appendChild(vazio);
        return;
    }

    configuracoesAulasAdmin.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        const titulo = document.createElement("p");
        titulo.innerText = rotuloCurtoAulaAdmin(item);
        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = [
            `Tipo: ${tipoConfiguracaoAula(item) === "AULA" ? "Aula" : "Intervalo"}`,
            `Ordem: ${Number(item.ordem_visual || 0)}`,
            item.aula_numero ? `Número global: ${Number(item.aula_numero)}` : null,
            tipoConfiguracaoAula(item) === "AULA" && String(item.periodo || "").trim()
                ? `Período: ${String(item.periodo).toUpperCase() === "MATUTINO" ? "Matutino" : "Vespertino"}`
                : null,
            textoHorarioConfiguracaoAula(item),
            item.ativo ? "Ativo" : "Inativo",
        ].filter(Boolean).join(" | ");

        const editar = document.createElement("button");
        editar.type = "button";
        editar.innerText = "Editar";
        editar.addEventListener("click", () => {
            preencherFormularioConfiguracaoAula(item);
            if (typeof ativarAbaAdmin === "function") ativarAbaAdmin("aulas");
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
        const status = document.createElement("button");
        status.type = "button";
        status.innerText = item.ativo ? "Desativar" : "Ativar";
        status.addEventListener("click", () => alterarStatusConfiguracaoAula(item));
        const acoes = document.createElement("div");
        acoes.className = "admin-inline";
        acoes.append(editar, status);
        li.append(titulo, detalhe, acoes);
        lista.appendChild(li);
    });
}

async function alterarStatusConfiguracaoAula(item) {
    try {
        await fetchJson(`/admin/configuracao-aulas/${item.id}`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                ordem_visual: Number(item.ordem_visual || 0),
                tipo: tipoConfiguracaoAula(item),
                aula_numero: tipoConfiguracaoAula(item) === "AULA" ? Number(item.aula_numero || 0) : null,
                nome: String(item.nome || ""),
                horario_inicio: String(item.horario_inicio || ""),
                horario_fim: String(item.horario_fim || ""),
                ativo: !Boolean(item.ativo),
            }),
        });
        setMensagem(
            "msgConfiguracaoAula",
            `Item ${rotuloCurtoAulaAdmin(item)} ${item.ativo ? "desativado" : "ativado"} com sucesso.`
        );
        await carregarConfiguracoesAulasAdmin();
        if (el("listaTurmasAdmin")) await carregarTurmasAdmin();
    } catch (err) {
        setMensagem("msgConfiguracaoAula", err.message, true);
    }
}

async function carregarConfiguracoesAulasAdmin() {
    configuracoesAulasAdmin = await fetchJson("/admin/configuracao-aulas?incluir_inativas=true", { headers });
    renderListaConfiguracoesAulasAdmin();
    if (typeof atualizarJanelaAulasFormularioTurma === "function") atualizarJanelaAulasFormularioTurma();
    if (!configuracaoAulaEmEdicaoId) return;
    const item = obterConfiguracaoAulaAdminPorId(configuracaoAulaEmEdicaoId);
    if (item) preencherFormularioConfiguracaoAula(item);
    else limparFormularioConfiguracaoAula();
}

async function salvarConfiguracaoAula(event) {
    event.preventDefault();
    const payload = {
        ordem_visual: Number(el("configAulaOrdemVisual")?.value || 0),
        tipo: el("configAulaTipo")?.value || "AULA",
        aula_numero: el("configAulaNumero")?.disabled ? null : Number(el("configAulaNumero")?.value || 0),
        nome: String(el("configAulaNome")?.value || "").trim(),
        horario_inicio: String(el("configAulaHorarioInicio")?.value || "").trim(),
        horario_fim: String(el("configAulaHorarioFim")?.value || "").trim(),
        ativo: Boolean(el("configAulaAtivo")?.checked),
    };
    try {
        const rota = configuracaoAulaEmEdicaoId
            ? `/admin/configuracao-aulas/${configuracaoAulaEmEdicaoId}`
            : "/admin/configuracao-aulas";
        await fetchJson(rota, {
            method: configuracaoAulaEmEdicaoId ? "PUT" : "POST",
            headers: headersJson,
            body: JSON.stringify(payload),
        });
        setMensagem("msgConfiguracaoAula", configuracaoAulaEmEdicaoId ? "Item atualizado com sucesso." : "Item cadastrado com sucesso.");
        limparFormularioConfiguracaoAula();
        await carregarConfiguracoesAulasAdmin();
        if (el("listaTurmasAdmin")) await carregarTurmasAdmin();
    } catch (err) {
        setMensagem("msgConfiguracaoAula", err.message, true);
    }
}
