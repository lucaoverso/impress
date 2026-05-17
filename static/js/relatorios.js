const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchJson } = window.AppApi;
const { paraIso } = window.AppFormat;

const token = garantirToken();
const headers = criarHeadersAuth(token);

let usuarioAtual = null;
let dashboardAtual = null;
const graficos = {};

function formatarNumero(valor) {
    return new Intl.NumberFormat("pt-BR").format(Number(valor || 0));
}

function formatarDecimal(valor, casas = 1) {
    return new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
    }).format(Number(valor || 0));
}

function formatarValorCard(valor) {
    if (typeof valor === "number") {
        return formatarNumero(valor);
    }

    const texto = String(valor || "").trim();
    if (!texto) {
        return "0";
    }

    if (/^\d+(?:\.\d+)?%$/.test(texto)) {
        return texto.replace(".", ",");
    }

    return texto;
}

function setMensagem(texto, tipo = "info") {
    const msg = el("msgRelatorios");
    if (!msg) {
        return;
    }

    msg.innerText = texto || "";
    msg.dataset.tipo = tipo;
}

function obterPeriodoAtual() {
    const hoje = new Date();
    const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    return {
        inicio: paraIso(inicio),
        fim: paraIso(hoje),
    };
}

function aplicarPeriodoAtual() {
    const periodo = obterPeriodoAtual();
    el("relDataInicio").value = periodo.inicio;
    el("relDataFim").value = periodo.fim;
}

function queryPeriodo() {
    const params = new URLSearchParams();
    const dataInicio = el("relDataInicio").value;
    const dataFim = el("relDataFim").value;

    if (dataInicio) {
        params.set("data_inicio", dataInicio);
    }
    if (dataFim) {
        params.set("data_fim", dataFim);
    }

    const query = params.toString();
    return query ? `?${query}` : "";
}

function atualizarResumoPeriodo(periodo = {}) {
    const dataInicio = String(periodo.data_inicio || "").trim();
    const dataFim = String(periodo.data_fim || "").trim();
    const diasPeriodo = formatarNumero(periodo.dias_periodo || 0);
    const diasUteis = formatarNumero(periodo.dias_uteis || 0);
    const capacidadeDia = formatarNumero(periodo.capacidade_aulas_por_dia || 0);

    el("relatoriosPeriodoInfo").innerText = dataInicio && dataFim
        ? `Periodo: ${dataInicio} ate ${dataFim} | ${diasPeriodo} dia(s), ${diasUteis} dia(s) uteis | base de ${capacidadeDia} uso(s) por dia util.`
        : "";
}

function usuarioTemAcessoRelatorios(usuario = {}) {
    if (Boolean(usuario.tem_acesso_coordenacao)) {
        return true;
    }
    const cargo = normalizarCargoUsuario(usuario);
    return cargo === "ADMIN" || cargo === "COORDENADOR";
}

function renderCards(cards = []) {
    const container = el("relatoriosCards");
    container.innerHTML = "";

    if (!Array.isArray(cards) || cards.length === 0) {
        container.innerHTML = '<article class="reports-metric-card"><p class="booking-empty">Nenhum indicador disponivel no periodo.</p></article>';
        return;
    }

    cards.forEach((card) => {
        const article = document.createElement("article");
        article.className = "reports-metric-card";

        const titulo = document.createElement("p");
        titulo.className = "reports-metric-label";
        titulo.innerText = card.titulo || "Indicador";

        const valor = document.createElement("strong");
        valor.className = "reports-metric-value";
        valor.innerText = formatarValorCard(card.valor);

        const descricao = document.createElement("p");
        descricao.className = "reports-metric-description";
        descricao.innerText = card.descricao || "";

        article.appendChild(titulo);
        article.appendChild(valor);
        article.appendChild(descricao);
        container.appendChild(article);
    });
}

function renderResumoSimples(containerId, itens = []) {
    const container = el(containerId);
    container.innerHTML = "";

    itens.forEach((item) => {
        const article = document.createElement("article");
        article.className = "reports-summary-card";

        const titulo = document.createElement("p");
        titulo.className = "reports-summary-label";
        titulo.innerText = item.titulo || "Resumo";

        const valor = document.createElement("strong");
        valor.className = "reports-summary-value";
        valor.innerText = item.valor;

        article.appendChild(titulo);
        article.appendChild(valor);
        container.appendChild(article);
    });
}

function destruirGrafico(idGrafico) {
    if (graficos[idGrafico]) {
        graficos[idGrafico].destroy();
        delete graficos[idGrafico];
    }
}

function mostrarEstadoGrafico(canvasId, vazioId, mensagem) {
    const canvas = el(canvasId);
    const vazio = el(vazioId);
    if (canvas) {
        canvas.hidden = true;
    }
    if (vazio) {
        vazio.hidden = false;
        vazio.innerText = mensagem;
    }
}

function exibirGrafico(canvasId, vazioId) {
    const canvas = el(canvasId);
    const vazio = el(vazioId);
    if (canvas) {
        canvas.hidden = false;
    }
    if (vazio) {
        vazio.hidden = true;
        vazio.innerText = "";
    }
}

function temValoresNoGrafico(datasets = []) {
    return (datasets || []).some((dataset) =>
        Array.isArray(dataset.data) && dataset.data.some((valor) => Number(valor || 0) > 0)
    );
}

function criarGrafico(idGrafico, canvasId, vazioId, configuracao, mensagemVazio) {
    destruirGrafico(idGrafico);

    if (typeof window.Chart === "undefined") {
        mostrarEstadoGrafico(
            canvasId,
            vazioId,
            "Chart.js nao ficou disponivel. Os dados seguem visiveis em cards e tabelas."
        );
        return;
    }

    const labels = configuracao?.data?.labels || [];
    const datasets = configuracao?.data?.datasets || [];
    if (labels.length === 0 || !temValoresNoGrafico(datasets)) {
        mostrarEstadoGrafico(canvasId, vazioId, mensagemVazio || "Sem dados no periodo.");
        return;
    }

    exibirGrafico(canvasId, vazioId);
    const canvas = el(canvasId);
    graficos[idGrafico] = new window.Chart(canvas, configuracao);
}

function opcoesBaseGrafico(extra = {}) {
    return Object.assign(
        {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: "#405165",
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: "#5b6b7f" },
                    grid: { color: "rgba(148, 163, 184, 0.15)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: "#5b6b7f" },
                    grid: { color: "rgba(148, 163, 184, 0.15)" },
                },
            },
        },
        extra
    );
}

function renderTabelaVazia(tbodyId, colspan, mensagem = "Sem dados no periodo selecionado.") {
    const tbody = el(tbodyId);
    tbody.innerHTML = "";

    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = colspan;
    td.className = "booking-empty reports-empty-cell";
    td.innerText = mensagem;
    tr.appendChild(td);
    tbody.appendChild(tr);
}

function renderTabelaImpressoes(itens = []) {
    const tbodyId = "tabelaImpressoesBody";
    if (!Array.isArray(itens) || itens.length === 0) {
        renderTabelaVazia(tbodyId, 3);
        return;
    }

    const tbody = el(tbodyId);
    tbody.innerHTML = "";

    itens.forEach((item) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.nome || "Professor nao informado"}</td>
            <td>${formatarNumero(item.total_jobs || 0)}</td>
            <td>${formatarNumero(item.total_paginas || 0)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderTabelaRecursos(itens = []) {
    const tbodyId = "tabelaRecursosBody";
    if (!Array.isArray(itens) || itens.length === 0) {
        renderTabelaVazia(tbodyId, 6);
        return;
    }

    const tbody = el(tbodyId);
    tbody.innerHTML = "";

    itens.forEach((item) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.recurso_nome || "Recurso nao informado"}</td>
            <td>${item.recurso_tipo || "-"}</td>
            <td>${formatarNumero(item.total_reservas || 0)}</td>
            <td>${formatarNumero(item.professores_distintos || 0)}</td>
            <td>${formatarNumero(item.capacidade_periodo || 0)}</td>
            <td>${formatarDecimal(item.percentual_uso || 0)}%</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderTabelaRecursosProfessor(itens = []) {
    const tbodyId = "tabelaRecursosProfessorBody";
    if (!Array.isArray(itens) || itens.length === 0) {
        renderTabelaVazia(tbodyId, 2);
        return;
    }

    const tbody = el(tbodyId);
    tbody.innerHTML = "";

    itens.forEach((item) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.nome || "Professor nao informado"}</td>
            <td>${formatarNumero(item.total_reservas || 0)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDashboard(payload = {}) {
    renderCards(payload.cards || []);

    const dashboard = payload.dashboard_geral?.graficos || {};

    criarGrafico(
        "movimentoPeriodo",
        "graficoMovimentoPeriodo",
        "graficoMovimentoPeriodoVazio",
        {
            type: "line",
            data: {
                labels: dashboard.movimento_periodo?.labels || [],
                datasets: [
                    {
                        label: "Paginas impressas",
                        data: dashboard.movimento_periodo?.paginas || [],
                        borderColor: "#0f766e",
                        backgroundColor: "rgba(15, 118, 110, 0.18)",
                        tension: 0.25,
                        fill: true,
                    },
                    {
                        label: "Reservas de recursos",
                        data: dashboard.movimento_periodo?.reservas || [],
                        borderColor: "#1d4ed8",
                        backgroundColor: "rgba(29, 78, 216, 0.12)",
                        tension: 0.25,
                        fill: false,
                    },
                ],
            },
            options: opcoesBaseGrafico(),
        },
        "Sem movimento registrado no periodo."
    );

    criarGrafico(
        "impressoesProfessor",
        "graficoImpressoesProfessor",
        "graficoImpressoesProfessorVazio",
        {
            type: "bar",
            data: {
                labels: dashboard.impressoes_por_professor?.labels || [],
                datasets: [
                    {
                        label: "Paginas",
                        data: dashboard.impressoes_por_professor?.valores || [],
                        backgroundColor: "#0f766e",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                plugins: { legend: { display: false } },
            }),
        },
        "Nenhuma impressao registrada no periodo."
    );

    criarGrafico(
        "reservasRecurso",
        "graficoReservasRecurso",
        "graficoReservasRecursoVazio",
        {
            type: "doughnut",
            data: {
                labels: dashboard.reservas_por_recurso?.labels || [],
                datasets: [
                    {
                        data: dashboard.reservas_por_recurso?.valores || [],
                        backgroundColor: [
                            "#0f766e",
                            "#1d4ed8",
                            "#f59e0b",
                            "#ef4444",
                            "#7c3aed",
                            "#0ea5e9",
                            "#84cc16",
                        ],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#405165",
                        },
                    },
                },
            },
        },
        "Nenhuma reserva registrada no periodo."
    );

    criarGrafico(
        "utilizacaoRecursos",
        "graficoUtilizacaoRecursos",
        "graficoUtilizacaoRecursosVazio",
        {
            type: "bar",
            data: {
                labels: dashboard.utilizacao_recursos?.labels || [],
                datasets: [
                    {
                        label: "% de uso",
                        data: dashboard.utilizacao_recursos?.valores || [],
                        backgroundColor: "#1d4ed8",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                plugins: {
                    legend: { display: false },
                },
            }),
        },
        "Sem dados suficientes para calcular capacidade de uso."
    );
}

function renderImpressoes(payload = {}) {
    const resumo = payload.impressoes?.resumo || {};
    renderResumoSimples("impressoesResumo", [
        { titulo: "Paginas impressas", valor: formatarNumero(resumo.total_paginas || 0) },
        { titulo: "Jobs concluidos", valor: formatarNumero(resumo.total_jobs || 0) },
        { titulo: "Media por job", valor: formatarDecimal(resumo.media_paginas_por_job || 0) },
        { titulo: "Professores com impressoes", valor: formatarNumero(resumo.professores_com_impressoes || 0) },
    ]);

    const serie = payload.impressoes?.serie_diaria || {};
    criarGrafico(
        "impressoesDiarias",
        "graficoImpressoesDiarias",
        "graficoImpressoesDiariasVazio",
        {
            type: "bar",
            data: {
                labels: serie.labels || [],
                datasets: [
                    {
                        label: "Jobs",
                        data: serie.jobs || [],
                        backgroundColor: "rgba(29, 78, 216, 0.74)",
                        borderRadius: 8,
                    },
                    {
                        label: "Paginas",
                        data: serie.paginas || [],
                        backgroundColor: "rgba(15, 118, 110, 0.84)",
                        borderRadius: 8,
                    },
                ],
            },
            options: opcoesBaseGrafico(),
        },
        "Nenhuma impressao registrada no periodo."
    );

    renderTabelaImpressoes(payload.impressoes?.ranking_professores || []);
}

function renderRecursos(payload = {}) {
    const resumo = payload.recursos?.resumo || {};
    renderResumoSimples("recursosResumo", [
        { titulo: "Reservas", valor: formatarNumero(resumo.total_reservas || 0) },
        { titulo: "Professores usando recursos", valor: formatarNumero(resumo.professores_com_reservas || 0) },
        { titulo: "Recursos utilizados", valor: formatarNumero(resumo.recursos_utilizados || 0) },
        { titulo: "Uso medio da capacidade", valor: `${formatarDecimal(resumo.taxa_uso_geral || 0)}%` },
    ]);

    const serie = payload.recursos?.serie_diaria || {};
    criarGrafico(
        "recursosDiarios",
        "graficoRecursosDiarios",
        "graficoRecursosDiariosVazio",
        {
            type: "line",
            data: {
                labels: serie.labels || [],
                datasets: [
                    {
                        label: "Reservas",
                        data: serie.reservas || [],
                        borderColor: "#1d4ed8",
                        backgroundColor: "rgba(29, 78, 216, 0.14)",
                        fill: true,
                        tension: 0.25,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                plugins: { legend: { display: false } },
            }),
        },
        "Nenhuma reserva registrada no periodo."
    );

    renderTabelaRecursos(payload.recursos?.ranking_recursos || []);
    renderTabelaRecursosProfessor(payload.recursos?.ranking_professores || []);
}

function ativarTab(tabId) {
    document.querySelectorAll("[data-relatorios-tab-trigger]").forEach((botao) => {
        const ativo = botao.dataset.relatoriosTabTrigger === tabId;
        botao.classList.toggle("is-active", ativo);
        botao.setAttribute("aria-selected", ativo ? "true" : "false");
    });

    document.querySelectorAll("[data-relatorios-tab-panel]").forEach((painel) => {
        const ativo = painel.dataset.relatoriosTabPanel === tabId;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

async function carregarUsuario() {
    const usuario = await fetchJson("/me", { headers });
    if (!usuarioTemAcessoRelatorios(usuario)) {
        window.location.href = "/servicos";
        return null;
    }

    usuarioAtual = usuario;
    const cargo = normalizarCargoUsuario(usuario);
    el("relatoriosUsuario").innerText = `${usuario.nome} | ${cargo}`;
    return usuario;
}

async function carregarDashboard() {
    setMensagem("Atualizando relatorios...");
    const payload = await fetchJson(`/api/relatorios/dashboard${queryPeriodo()}`, { headers });
    dashboardAtual = payload;

    atualizarResumoPeriodo(payload.periodo || {});
    renderDashboard(payload);
    renderImpressoes(payload);
    renderRecursos(payload);
    setMensagem("Relatorios atualizados.");
}

function registrarEventos() {
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });

    el("btnAplicarRelatorios").addEventListener("click", async () => {
        try {
            await carregarDashboard();
        } catch (err) {
            setMensagem(err.message || "Nao foi possivel carregar os relatorios.", "erro");
        }
    });

    el("btnPeriodoAtual").addEventListener("click", async () => {
        aplicarPeriodoAtual();
        try {
            await carregarDashboard();
        } catch (err) {
            setMensagem(err.message || "Nao foi possivel carregar os relatorios.", "erro");
        }
    });

    document
        .querySelectorAll("[data-relatorios-tab-trigger]:not([disabled])")
        .forEach((botao) => {
            botao.addEventListener("click", () => {
                ativarTab(botao.dataset.relatoriosTabTrigger);
            });
        });
}

async function init() {
    try {
        aplicarPeriodoAtual();
        registrarEventos();
        const usuario = await carregarUsuario();
        if (!usuario) {
            return;
        }
        await carregarDashboard();
    } catch (err) {
        setMensagem(err.message || "Erro ao carregar o modulo de relatorios.", "erro");
    }
}

init();
