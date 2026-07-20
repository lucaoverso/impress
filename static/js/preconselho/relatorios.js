function construirParametrosRelatorio() {
    return new URLSearchParams({
        periodo_id: String(el("preconselhoPeriodoRelatorio").value || "")
    });
}

function registrarTurmasRelatorioExpandidas() {
    const container = el("listaRelatorioTurmasPreconselho");
    if (!container) {
        return;
    }

    estadoRelatorio.turmasExpandidas = new Set(
        Array.from(container.querySelectorAll("details[data-turma-id][open]"))
            .map((details) => String(details.dataset.turmaId || "").trim())
            .filter(Boolean)
    );
}

function renderizarItensRankingRelatorio(itens = [], mensagemVazia = "Nenhum dado disponível.") {
    if (!Array.isArray(itens) || itens.length === 0) {
        return criarEstadoVazio(mensagemVazia);
    }

    return itens.map((item) => {
        const total = Number(item?.total_registros || 0);
        const extra = String(item?.extra || "").trim();
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(item?.nome || "Sem identificação")}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-manual">${total} ${total === 1 ? "registro" : "registros"}</span>
                            </div>
                        </div>
                        ${extra ? `<p class="pcpi-item-note">${escaparHtml(extra)}</p>` : ""}
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarItensTextoRelatorio(itens = [], mensagemVazia = "Nenhum destaque disponível.") {
    if (!Array.isArray(itens) || itens.length === 0) {
        return criarEstadoVazio(mensagemVazia);
    }

    return itens.map((texto) => `
        <li class="pcpi-item pcpi-item-automatico">
            <div class="pcpi-checkbox-row">
                <div class="pcpi-item-body">
                    <p class="pcpi-item-note">${escaparHtml(String(texto || ""))}</p>
                </div>
            </div>
        </li>
    `).join("");
}

function renderizarTurmasRelatorio(turmas = []) {
    const container = el("listaRelatorioTurmasPreconselho");
    if (!container) {
        return;
    }

    registrarTurmasRelatorioExpandidas();

    if (!Array.isArray(turmas) || turmas.length === 0) {
        container.innerHTML = '<p class="preconselho-empty-state">Nenhuma turma disponível para o período selecionado.</p>';
        return;
    }

    container.innerHTML = turmas.map((turma) => {
        const totalRegistros = Number(turma?.total_registros || 0);
        const totalEstudantes = Number(turma?.total_estudantes_sinalizados || 0);
        const quantidadeEstudantes = Number(turma?.quantidade_estudantes || 0);
        const professorDestaque = turma?.professor_destaque || {};
        const motivos = Array.isArray(turma?.motivos_frequentes) ? turma.motivos_frequentes : [];
        const motivoTopo = motivos[0] || null;
        const turno = String(turma?.turno || "").trim();
        const metaTurma = [
            turno ? nomeTurno(turno) : "",
            `${quantidadeEstudantes} estudante(s) cadastrados`,
            `${totalEstudantes} sinalizado(s)`
        ].filter(Boolean).join(" | ");

        return `
            <details class="admin-accordion-item preconselho-relatorio-accordion" data-turma-id="${Number(turma?.turma_id || 0)}">
                <summary class="admin-accordion-summary">
                    <div class="admin-accordion-title">
                        <strong>${escaparHtml(turma?.turma_nome || "Turma")}</strong>
                        <span>${escaparHtml(metaTurma)}</span>
                    </div>
                    <span class="admin-accordion-badge">${totalRegistros} ${totalRegistros === 1 ? "registro" : "registros"}</span>
                </summary>
                <div class="admin-accordion-body preconselho-relatorio-body">
                    <div class="preconselho-summary-grid preconselho-summary-grid-turma">
                        <article class="preconselho-summary-card">
                            <span>Registros</span>
                            <strong>${totalRegistros}</strong>
                            <small>Total de apontamentos lançados na turma.</small>
                        </article>
                        <article class="preconselho-summary-card">
                            <span>Professor em destaque</span>
                            <strong>${escaparHtml(professorDestaque?.nome || "Sem registros")}</strong>
                            <small>${escaparHtml(professorDestaque?.extra || "Nenhum professor registrou apontamentos nesta turma.")}</small>
                        </article>
                        <article class="preconselho-summary-card">
                            <span>Motivo recorrente</span>
                            <strong>${escaparHtml(motivoTopo?.nome || "Sem recorrência")}</strong>
                            <small>${motivoTopo ? `${Number(motivoTopo.total_registros || 0)} ocorrência(s) no período.` : "Sem registros suficientes para ranqueamento."}</small>
                        </article>
                    </div>

                    <div class="preconselho-report-columns">
                        <section class="preconselho-report-column">
                            <div class="pcpi-subsection-header">
                                <h3>Pontos de atenção</h3>
                            </div>
                            <ul class="pcpi-list">
                                ${renderizarItensTextoRelatorio(turma?.pontos_atencao || [], "Nenhum ponto crítico destacado para esta turma.")}
                            </ul>
                        </section>

                        <section class="preconselho-report-column">
                            <div class="pcpi-subsection-header">
                                <h3>Estudantes com mais registros</h3>
                            </div>
                            <ul class="pcpi-list">
                                ${renderizarItensRankingRelatorio(turma?.estudantes_destaque || [], "Nenhum estudante sinalizado nesta turma.")}
                            </ul>
                        </section>

                        <section class="preconselho-report-column">
                            <div class="pcpi-subsection-header">
                                <h3>Professores relacionados</h3>
                            </div>
                            <ul class="pcpi-list">
                                ${renderizarItensRankingRelatorio(turma?.professores_relacionados || [], "Nenhum professor relacionado foi encontrado para esta turma.")}
                            </ul>
                        </section>
                    </div>
                </div>
            </details>
        `;
    }).join("");

    const detalhes = Array.from(container.querySelectorAll("details[data-turma-id]"));
    detalhes.forEach((details, index) => {
        const turmaId = String(details.dataset.turmaId || "").trim();
        const manterAberto = estadoRelatorio.turmasExpandidas.has(turmaId) || (
            estadoRelatorio.turmasExpandidas.size === 0 && index === 0
        );
        details.open = manterAberto;
        details.addEventListener("toggle", () => {
            if (details.open) {
                estadoRelatorio.turmasExpandidas.add(turmaId);
            } else {
                estadoRelatorio.turmasExpandidas.delete(turmaId);
            }
        });
    });
}

function renderizarRelatorio() {
    const dados = estadoRelatorio.dados;
    const listaPontos = el("listaPontosCriticosPreconselho");
    const listaEstudantes = el("listaEstudantesDestaqueRelatorio");

    if (!dados) {
        el("preconselhoResumoRelatorioRegistros").textContent = "0";
        el("preconselhoResumoRelatorioEstudantes").textContent = "0";
        el("preconselhoResumoRelatorioTurma").textContent = "Nenhuma";
        el("preconselhoResumoRelatorioTurmaMeta").textContent = "Sem dados para o período.";
        el("preconselhoResumoRelatorioProfessor").textContent = "Nenhum";
        el("preconselhoResumoRelatorioProfessorMeta").textContent = "Sem dados para o período.";
        listaPontos.innerHTML = criarEstadoVazio("A leitura crítica do período aparecerá aqui.");
        listaEstudantes.innerHTML = criarEstadoVazio("O ranking geral dos estudantes aparecerá aqui.");
        renderizarTurmasRelatorio([]);
        return;
    }

    const turmaDestaque = dados?.turma_destaque || {};
    const professorDestaque = dados?.professor_destaque || {};

    el("preconselhoResumoRelatorioRegistros").textContent = String(Number(dados?.total_registros || 0));
    el("preconselhoResumoRelatorioEstudantes").textContent = String(Number(dados?.total_estudantes_sinalizados || 0));
    el("preconselhoResumoRelatorioTurma").textContent = turmaDestaque?.nome || "Nenhuma";
    el("preconselhoResumoRelatorioTurmaMeta").textContent = turmaDestaque?.extra || "Sem dados para o período.";
    el("preconselhoResumoRelatorioProfessor").textContent = professorDestaque?.nome || "Nenhum";
    el("preconselhoResumoRelatorioProfessorMeta").textContent = professorDestaque?.extra || "Sem dados para o período.";

    listaPontos.innerHTML = renderizarItensTextoRelatorio(
        dados?.pontos_criticos || [],
        "Nenhum ponto crítico foi identificado para o período."
    );
    listaEstudantes.innerHTML = renderizarItensRankingRelatorio(
        dados?.estudantes_destaque || [],
        "Nenhum estudante foi sinalizado neste período."
    );
    renderizarTurmasRelatorio(Array.isArray(dados?.turmas) ? dados.turmas : []);
}

async function carregarRelatorio() {
    limparMensagem("msgPreconselhoRelatorio");
    const periodoId = Number(el("preconselhoPeriodoRelatorio").value || 0);
    if (!periodoId) {
        estadoRelatorio.dados = null;
        renderizarRelatorio();
        return;
    }

    try {
        const resposta = await fetchComAuth(`/preconselho/relatorio?${construirParametrosRelatorio().toString()}`, { headers });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar o relatório."));
        }

        estadoRelatorio.dados = await resposta.json();
        renderizarRelatorio();
        definirMensagem("msgPreconselhoRelatorio", "Relatório atualizado.");
    } catch (erro) {
        estadoRelatorio.dados = null;
        renderizarRelatorio();
        definirMensagem("msgPreconselhoRelatorio", erro.message || "Não foi possível carregar o relatório.", true);
    }
}

