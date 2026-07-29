function queryPeriodo(prefix = "") {
    const inicio = el(`${prefix}relDataInicio`) ? el(`${prefix}relDataInicio`).value : el("relDataInicio").value;
    const fim = el(`${prefix}relDataFim`) ? el(`${prefix}relDataFim`).value : el("relDataFim").value;

    const params = new URLSearchParams();
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function renderListaRelatorio(id, itens, formatador, vazio = "Sem dados no período.") {
    const ul = el(id);
    ul.innerHTML = "";

    if (!itens || itens.length === 0) {
        const li = document.createElement("li");
        li.className = "booking-empty";
        li.innerText = vazio;
        ul.appendChild(li);
        return;
    }

    itens.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = formatador(item);
        ul.appendChild(li);
    });
}

async function carregarRelatorios() {
    try {
        const query = queryPeriodo();
        const relImpressao = await fetchJson(`/admin/relatorio/impressao${query}`, { headers });
        const relRecursos = await fetchJson(`/admin/relatorio/recursos${query}`, { headers });

        renderListaRelatorio(
            "relatorioImpressaoAdmin",
            relImpressao,
            (item) => `${item.nome}: ${item.total_jobs} job(s), ${item.total_paginas} páginas`
        );

        renderListaRelatorio(
            "relatorioRecursosAdmin",
            relRecursos.por_recurso,
            (item) => `${item.recurso_nome} (${item.recurso_tipo}): ${item.total_reservas} reservas, ${item.professores_distintos} professor(es)`
        );

        renderListaRelatorio(
            "relatorioRecursosProfessorAdmin",
            relRecursos.por_professor,
            (item) => `${item.nome}: ${item.total_reservas} reserva(s)`
        );

        setMensagem("msgRelatorios", "Relatórios atualizados.");
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}
