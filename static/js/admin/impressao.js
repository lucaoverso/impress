function queryHistorico() {
    const params = new URLSearchParams();
    const inicio = el("inicio").value;
    const fim = el("fim").value;
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function renderResumoStatusImpressao(status) {
    const resumo = el("statusResumoImpressao");
    if (!resumo) {
        return;
    }

    const semPapel = Boolean(status?.sem_papel);
    const mensagem = String(status?.mensagem || "").trim();
    const atualizadoEm = String(status?.atualizado_em || "").trim();
    const atualizadoEmFormatado = atualizadoEm ? formatarDataHora(atualizadoEm) : "agora";

    resumo.className = semPapel
        ? "admin-status-box is-warning"
        : "admin-status-box is-ok";
    resumo.innerHTML = semPapel
        ? `<strong>Impressao bloqueada</strong><p>${mensagem || "Sem papel informado no painel administrativo."}</p><small>Atualizado em: ${atualizadoEmFormatado}</small>`
        : `<strong>Impressao liberada</strong><p>Nenhum bloqueio por falta de papel ativo no momento.</p><small>Atualizado em: ${atualizadoEmFormatado}</small>`;
}

async function carregarStatusImpressaoAdmin() {
    const status = await fetchJson("/admin/impressao/status", { headers });

    const checkbox = el("statusSemPapel");
    const inputMensagem = el("statusMensagemImpressao");

    if (checkbox) {
        checkbox.checked = Boolean(status?.sem_papel);
    }
    if (inputMensagem) {
        inputMensagem.value = String(status?.mensagem || "");
    }

    renderResumoStatusImpressao(status);
}

async function salvarStatusImpressao(event) {
    event.preventDefault();
    try {
        const semPapel = Boolean(el("statusSemPapel")?.checked);
        const mensagem = String(el("statusMensagemImpressao")?.value || "").trim();

        await fetchJson("/admin/impressao/status", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                sem_papel: semPapel,
                mensagem,
            }),
        });

        setMensagem(
            "msgStatusImpressao",
            semPapel
                ? "Bloqueio de impressao por falta de papel salvo."
                : "Impressao liberada novamente."
        );
        await carregarStatusImpressaoAdmin();
    } catch (err) {
        setMensagem("msgStatusImpressao", err.message, true);
    }
}

async function carregarFilaAdmin() {
    const jobs = await fetchJson("/admin/fila", { headers });
    const ul = el("fila-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const descricao = document.createElement("p");  
        descricao.innerText = `${job.arquivo} | ${job.status} | ${job.paginas_totais ?? 0} páginas | ${job.professor ? `Professor: ${job.professor.nome}` : "Sem professor associado"}`

        const actions = document.createElement("div");
        actions.className = "admin-inline";

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarJob(job.id));

        const btnUrgente = document.createElement("button");
        btnUrgente.type = "button";
        btnUrgente.innerText = "Urgente";
        btnUrgente.addEventListener("click", () => prioridadeJob(job.id));

        actions.appendChild(btnCancelar);
        actions.appendChild(btnUrgente);
        li.appendChild(descricao);
        li.appendChild(actions);
        ul.appendChild(li);
    });
}

async function cancelarJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/cancelar`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function prioridadeJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/prioridade`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function buscarHistorico() {
    const jobs = await fetchJson(`/admin/historico${queryHistorico()}`, { headers });
    const ul = el("historico-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${job.criado_em} | ${job.arquivo} | ${job.paginas_totais ?? 0} páginas | ${job.usuario_nome || "Usuário não informado"}`;
        ul.appendChild(li);
    });
}

async function carregarImpressorasAdmin() {
    const impressoras = await fetchJson("/admin/impressao/impressoras", { headers });
    const lista = el("listaImpressorasAdmin");
    if (!lista) return;
    lista.innerHTML = "";

    if (!Array.isArray(impressoras) || impressoras.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma impressora cadastrada.";
        lista.appendChild(vazio);
        return;
    }

    impressoras.forEach((impressora) => {
        const item = document.createElement("li");
        item.className = "admin-list-item";

        const nome = document.createElement("p");
        nome.innerText = impressora.name;

        const status = document.createElement("p");
        status.className = "booking-detail";
        status.innerText = impressora.active ? "Ativa" : "Inativa";

        const acoes = document.createElement("div");
        acoes.className = "admin-inline";

        const alternar = document.createElement("button");
        alternar.type = "button";
        alternar.innerText = impressora.active ? "Desativar" : "Ativar";
        alternar.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/impressao/impressoras/${impressora.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ active: !Boolean(impressora.active) }),
                });
                await carregarImpressorasAdmin();
            } catch (err) {
                setMensagem("msgImpressoras", err.message, true);
            }
        });

        const excluir = document.createElement("button");
        excluir.type = "button";
        excluir.innerText = "Excluir";
        excluir.addEventListener("click", async () => {
            if (!window.confirm(`Excluir a impressora ${impressora.name}?`)) return;
            try {
                await fetchJson(`/admin/impressao/impressoras/${impressora.id}`, {
                    method: "DELETE",
                    headers,
                });
                await carregarImpressorasAdmin();
            } catch (err) {
                setMensagem("msgImpressoras", err.message, true);
            }
        });

        acoes.append(alternar, excluir);
        item.append(nome, status, acoes);
        lista.appendChild(item);
    });
}

async function cadastrarImpressora(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/impressao/impressoras", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({ name: el("nomeImpressora").value.trim() }),
        });
        el("formImpressora").reset();
        setMensagem("msgImpressoras", "Impressora cadastrada com sucesso.");
        await carregarImpressorasAdmin();
    } catch (err) {
        setMensagem("msgImpressoras", err.message, true);
    }
}
