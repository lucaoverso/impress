function construirParametrosConsolidacao() {
    const params = new URLSearchParams({
        periodo_id: String(el("preconselhoPeriodoConsolidacao").value || "")
    });

    const professorId = String(el("preconselhoProfessorConsolidacao").value || "").trim();
    const turmaId = String(el("preconselhoTurmaConsolidacao").value || "").trim();
    const disciplinaId = String(el("preconselhoDisciplinaConsolidacao").value || "").trim();

    if (professorId) params.set("professor_id", professorId);
    if (turmaId) params.set("turma_id", turmaId);
    if (disciplinaId) params.set("disciplina_id", disciplinaId);
    params.set("versao", String(el("preconselhoVersaoConsolidacao").value || "preconselho"));
    return params;
}

function renderizarConsolidacao() {
    const dados = estadoConsolidacao.dados;
    const lista = el("listaRegistrosConsolidacao");

    if (!dados) {
        el("preconselhoResumoConsolidadoRegistros").textContent = "0";
        el("preconselhoResumoConsolidadoEstudantes").textContent = "0";
        el("preconselhoResumoConsolidadoMotivos").textContent = "0";
        el("preconselhoMotivosFrequentes").textContent = "A síntese agrupada por estudante aparecerá após a aplicação dos filtros.";
        el("preconselhoTextoConsolidado").value = "";
        el("preconselhoResumoReavaliacaoConsolidado").textContent = "";
        lista.innerHTML = criarEstadoVazio("Nenhum estudante consolidado disponível.");
        return;
    }

    el("preconselhoResumoConsolidadoRegistros").textContent = String(Number(dados.total_registros || 0));
    el("preconselhoResumoConsolidadoEstudantes").textContent = String(Number(dados.total_estudantes || 0));
    el("preconselhoResumoConsolidadoMotivos").textContent = String(Array.isArray(dados.motivos_frequentes) ? dados.motivos_frequentes.length : 0);
    el("preconselhoMotivosFrequentes").textContent = Array.isArray(dados.motivos_frequentes) && dados.motivos_frequentes.length > 0
        ? `Motivos mais frequentes: ${dados.motivos_frequentes.join(", ")}.`
        : "Nenhum motivo recorrente foi destacado nesta consolidação.";
    el("preconselhoTextoConsolidado").value = String(dados.texto || "");
    el("preconselhoResumoReavaliacaoConsolidado").textContent =
        `Reavaliação: ${Number(dados.total_recuperados || 0)} recuperado(s), ${Number(dados.total_mantidos || 0)} mantido(s) e ${Number(dados.total_pendentes || 0)} pendente(s).`;

    const itensAgrupados = Array.isArray(dados.itens_agrupados) ? dados.itens_agrupados : [];
    if (itensAgrupados.length === 0) {
        lista.innerHTML = criarEstadoVazio("Não há estudantes sinalizados para os filtros aplicados.");
        return;
    }

    lista.innerHTML = itensAgrupados.map((item) => {
        const disciplinas = formatarListaNatural(item.disciplinas || []);
        const motivos = formatarListaNatural(item.motivos || []);
        const professores = formatarListaNatural(item.professores || []);
        const observacoes = Array.isArray(item.observacoes)
            ? item.observacoes.map((entrada) => String(entrada || "").trim()).filter(Boolean).join("; ")
            : "";
        const totalRegistros = Number(item.total_registros || 0);

        return `
        <li class="pcpi-item pcpi-item-manual">
            <div class="pcpi-checkbox-row">
                <div class="pcpi-item-body">
                    <div class="pcpi-item-top">
                        <strong>${escaparHtml(item.estudante_nome || "")}</strong>
                        <div class="pcpi-tag-group">
                            ${item.nivel_atencao ? `<span class="pcpi-chip">${escaparHtml(rotuloNivelAtencao(item.nivel_atencao))}</span>` : ""}
                            <span class="pcpi-chip pcpi-chip-manual">${totalRegistros} ${totalRegistros === 1 ? "registro" : "registros"}</span>
                        </div>
                    </div>
                    <p class="pcpi-item-line">${escaparHtml(item.turma_nome || "")}${disciplinas ? ` • ${escaparHtml(disciplinas)}` : ""}</p>
                    ${motivos ? `<p class="pcpi-item-note">${escaparHtml(motivos)}</p>` : ""}
                    ${professores ? `<p class="pcpi-item-note">${escaparHtml(`Professores da turma: ${professores}`)}</p>` : ""}
                    ${observacoes ? `<p class="pcpi-item-note">${escaparHtml(`Relatos complementares: ${observacoes}`)}</p>` : ""}
                    ${item.texto ? `<p class="pcpi-item-note is-secondary">${escaparHtml(item.texto)}</p>` : ""}
                </div>
            </div>
        </li>
    `;
    }).join("");
}

function criarHtmlTextoConsolidadoComEstudantesEmNegrito(dados) {
    const texto = String(dados?.texto || "");
    if (!texto) return "";

    let html = escaparHtml(texto);
    const itensAgrupados = Array.isArray(dados?.itens_agrupados) ? dados.itens_agrupados : [];
    itensAgrupados.forEach((item) => {
        const estudanteNome = String(item?.estudante_nome || "").trim();
        if (!estudanteNome) return;

        const alvo = escaparHtml(`O estudante ${estudanteNome}`);
        const substituto = `O estudante <strong>${escaparHtml(estudanteNome)}</strong>`;
        html = html.split(alvo).join(substituto);
    });

    return html.replace(/\r?\n/g, "<br>");
}

async function carregarConsolidacao() {
    limparMensagem("msgPreconselhoConsolidacao");
    const periodoId = Number(el("preconselhoPeriodoConsolidacao").value || 0);
    if (!periodoId) {
        estadoConsolidacao.dados = null;
        renderizarConsolidacao();
        return;
    }

    try {
        const resposta = await fetchComAuth(`/preconselho/consolidado?${construirParametrosConsolidacao().toString()}`, { headers });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível gerar a consolidação."));
        }

        estadoConsolidacao.dados = await resposta.json();
        renderizarConsolidacao();
        definirMensagem("msgPreconselhoConsolidacao", "Consolidação atualizada.");
    } catch (erro) {
        estadoConsolidacao.dados = null;
        renderizarConsolidacao();
        definirMensagem("msgPreconselhoConsolidacao", erro.message || "Não foi possível carregar a consolidação.", true);
    }
}

