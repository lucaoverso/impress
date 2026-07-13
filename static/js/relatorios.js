const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchJson } = window.AppApi;
const { paraIso, paraDataBr } = window.AppFormat;

const token = garantirToken();
const headers = criarHeadersAuth(token);

const graficos = {};
const VIEWPORT_TABLET_MAX = 960;
let dashboardAtual = null;
let anexosAtual = null;
let professoresRelatorio = [];
let relatorioProfessorAtual = null;
let viewportCompactoAtual = viewportEhCompactoInicial();

function viewportEhCompactoInicial() {
    return window.innerWidth <= VIEWPORT_TABLET_MAX;
}

function formatarNumero(valor) {
    return new Intl.NumberFormat("pt-BR").format(Number(valor || 0));
}

function formatarDecimal(valor, casas = 1) {
    return new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
    }).format(Number(valor || 0));
}

function formatarDataHoraRelatorios(valor) {
    const texto = String(valor || "").trim();
    if (!texto) {
        return "-";
    }

    const partes = texto.replace("T", " ").split(" ");
    if (partes.length === 1) {
        return partes[0].includes("-") ? paraDataBr(partes[0]) : texto;
    }

    const hora = String(partes[1] || "").slice(0, 5);
    return `${paraDataBr(partes[0])} ${hora}`;
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
    const descricaoCapacidade = String(periodo.descricao_capacidade || "").trim();

    el("relatoriosPeriodoInfo").innerText = dataInicio && dataFim
        ? `Periodo: ${dataInicio} ate ${dataFim} | ${diasPeriodo} dia(s), ${diasUteis} dia(s) uteis | ${descricaoCapacidade || "Base estimada configurada para o periodo."}`
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

function renderResumoCards(containerId, cards = []) {
    renderResumoSimples(
        containerId,
        (Array.isArray(cards) ? cards : []).map((card) => ({
            titulo: card.titulo || "Resumo",
            valor: formatarValorCard(card.valor),
        }))
    );
}

function renderInsights(insights = []) {
    const container = el("relatoriosInsights");
    container.innerHTML = "";

    const listaInsights = Array.isArray(insights) ? insights : [];
    if (listaInsights.length === 0) {
        listaInsights.push({
            titulo: "Dados insuficientes",
            texto: "Ainda não há dados suficientes para gerar insights neste período.",
            tipo: "informativo",
        });
    }

    listaInsights.forEach((insight) => {
        const article = document.createElement("article");
        article.className = "reports-insight-item";
        article.dataset.tipo = insight.tipo || "informativo";

        const titulo = document.createElement("strong");
        titulo.className = "reports-insight-title";
        titulo.innerText = insight.titulo || "Insight";

        const texto = document.createElement("p");
        texto.className = "reports-insight-text";
        texto.innerText = insight.texto || "";

        article.appendChild(titulo);
        article.appendChild(texto);
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

function viewportEhCompacto() {
    return window.innerWidth <= VIEWPORT_TABLET_MAX;
}

function aspectRatioGrafico(tipo = "padrao") {
    const compacto = viewportEhCompacto();

    if (tipo === "linha-amplo") {
        return compacto ? 1.45 : 3.1;
    }
    if (tipo === "barra-amplo") {
        return compacto ? 1.35 : 2.7;
    }
    if (tipo === "barra") {
        return compacto ? 1.18 : 1.8;
    }
    if (tipo === "rosca") {
        return compacto ? 1.1 : 1.65;
    }
    return compacto ? 1.2 : 1.8;
}

function gerarPdfPainel() {
    if (!dashboardAtual) {
        setMensagem("Aguarde o carregamento dos relatorios antes de gerar o PDF.", "erro");
        return;
    }

    Object.values(graficos).forEach((grafico) => grafico.resize());
    setMensagem("Na proxima tela, escolha 'Salvar como PDF'.");
    window.requestAnimationFrame(() => window.print());
}

function opcoesBaseGrafico(extra = {}) {
    return Object.assign(
        {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: aspectRatioGrafico(),
            layout: {
                padding: {
                    top: 8,
                    right: 8,
                    bottom: 4,
                    left: 4,
                },
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#405165",
                        padding: 14,
                        boxWidth: 14,
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: "#5b6b7f", padding: 8 },
                    grid: { color: "rgba(148, 163, 184, 0.15)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: "#5b6b7f", padding: 8 },
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

function appendLinhaTabela(tbody, colunas = []) {
    const tr = document.createElement("tr");
    colunas.forEach((coluna) => {
        const td = document.createElement("td");
        td.innerText = coluna;
        tr.appendChild(td);
    });
    tbody.appendChild(tr);
}

function renderTabelaComLinhas(tbodyId, itens, colspan, criarColunas) {
    if (!Array.isArray(itens) || itens.length === 0) {
        renderTabelaVazia(tbodyId, colspan);
        return;
    }

    const tbody = el(tbodyId);
    tbody.innerHTML = "";

    itens.forEach((item) => {
        appendLinhaTabela(tbody, criarColunas(item));
    });
}

function renderTabelaImpressoes(itens = []) {
    renderTabelaComLinhas("tabelaImpressoesBody", itens, 3, (item) => [
        item.nome || "Professor nao informado",
        formatarNumero(item.total_jobs || 0),
        formatarNumero(item.total_paginas || 0),
    ]);
}

function renderTabelaTagsImpressao(itens = []) {
    renderTabelaComLinhas("tabelaTagsImpressaoBody", itens, 3, (item) => [
        item.tag || "Sem classificacao",
        formatarNumero(item.total_jobs || 0),
        formatarNumero(item.total_paginas || 0),
    ]);
}

function renderTabelaRecursos(itens = []) {
    renderTabelaComLinhas("tabelaRecursosBody", itens, 6, (item) => [
        item.recurso_nome || "Recurso nao informado",
        item.recurso_tipo || "-",
        formatarNumero(item.total_reservas || 0),
        formatarNumero(item.professores_distintos || 0),
        formatarNumero(item.capacidade_periodo || 0),
        `${formatarDecimal(item.percentual_uso || 0)}%`,
    ]);
}

function renderTabelaRecursosProfessor(itens = []) {
    renderTabelaComLinhas("tabelaRecursosProfessorBody", itens, 2, (item) => [
        item.nome || "Professor nao informado",
        formatarNumero(item.total_reservas || 0),
    ]);
}

function renderTabelaPendenciasAnexos(itens = []) {
    renderTabelaComLinhas("tabelaAnexosPendenciasBody", itens, 4, (item) => [
        item.professor || "Professor nao informado",
        item.documento || "Documento nao informado",
        formatarDataHoraRelatorios(item.prazo),
        item.situacao || "Pendente",
    ]);
}

function renderTabelaRecentesAnexos(itens = []) {
    renderTabelaComLinhas("tabelaAnexosRecentesBody", itens, 5, (item) => [
        item.professor || "Professor nao informado",
        item.documento || "Documento nao informado",
        formatarDataHoraRelatorios(item.data_envio),
        formatarDataHoraRelatorios(item.prazo),
        item.situacao || "Pendente",
    ]);
}

function setMensagemProfessor(texto, tipo = "info") {
    const msg = el("msgRelatorioProfessor");
    if (!msg) return;
    msg.innerText = texto || "";
    msg.dataset.tipo = tipo;
}

function renderDashboard(payload = {}) {
    renderCards(payload.cards || []);

    const dashboard = payload.dashboard_geral || {};
    const dashboardGraficos = dashboard.graficos || {};
    renderInsights(dashboard.insights || []);

    criarGrafico(
        "movimentoPeriodo",
        "graficoMovimentoPeriodo",
        "graficoMovimentoPeriodoVazio",
        {
            type: "line",
            data: {
                labels: dashboardGraficos.movimento_periodo?.labels || [],
                datasets: [
                    {
                        label: "Paginas impressas",
                        data: dashboardGraficos.movimento_periodo?.paginas || [],
                        borderColor: "#0f766e",
                        backgroundColor: "rgba(15, 118, 110, 0.18)",
                        tension: 0.25,
                        fill: true,
                    },
                    {
                        label: "Reservas de recursos",
                        data: dashboardGraficos.movimento_periodo?.reservas || [],
                        borderColor: "#1d4ed8",
                        backgroundColor: "rgba(29, 78, 216, 0.12)",
                        tension: 0.25,
                        fill: false,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("linha-amplo"),
            }),
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
                labels: dashboardGraficos.impressoes_por_professor?.labels || [],
                datasets: [
                    {
                        label: "Paginas",
                        data: dashboardGraficos.impressoes_por_professor?.valores || [],
                        backgroundColor: "#0f766e",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("barra"),
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
                labels: dashboardGraficos.reservas_por_recurso?.labels || [],
                datasets: [
                    {
                        data: dashboardGraficos.reservas_por_recurso?.valores || [],
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
                maintainAspectRatio: true,
                aspectRatio: aspectRatioGrafico("rosca"),
                layout: {
                    padding: {
                        top: 10,
                        right: 10,
                        bottom: 10,
                        left: 10,
                    },
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#405165",
                            padding: 14,
                            boxWidth: 14,
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
                labels: dashboardGraficos.utilizacao_recursos?.labels || [],
                datasets: [
                    {
                        label: "% de uso",
                        data: dashboardGraficos.utilizacao_recursos?.valores || [],
                        backgroundColor: "#1d4ed8",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("barra-amplo"),
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
        { titulo: "Tags usadas", valor: formatarNumero(resumo.tags_utilizadas || 0) },
        { titulo: "Tag mais frequente", valor: resumo.tag_mais_frequente || "Sem dados" },
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
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("barra-amplo"),
            }),
        },
        "Nenhuma impressao registrada no periodo."
    );

    const tags = payload.impressoes?.ranking_tags || [];
    criarGrafico(
        "tagsImpressao",
        "graficoTagsImpressao",
        "graficoTagsImpressaoVazio",
        {
            type: "bar",
            data: {
                labels: tags.map((item) => item.tag || "Sem classificacao"),
                datasets: [
                    {
                        label: "Jobs classificados",
                        data: tags.map((item) => item.total_jobs || 0),
                        backgroundColor: "#f59e0b",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("barra"),
                plugins: { legend: { display: false } },
            }),
        },
        "Nenhuma classificacao registrada no periodo."
    );

    renderTabelaImpressoes(payload.impressoes?.ranking_professores || []);
    renderTabelaTagsImpressao(tags);
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
                aspectRatio: aspectRatioGrafico("linha-amplo"),
                plugins: { legend: { display: false } },
            }),
        },
        "Nenhuma reserva registrada no periodo."
    );

    renderTabelaRecursos(payload.recursos?.ranking_recursos || []);
    renderTabelaRecursosProfessor(payload.recursos?.ranking_professores || []);
}

function renderAnexos(payload = {}) {
    renderResumoCards("anexosResumo", payload.cards || []);

    const graficosAnexos = payload.graficos || {};
    criarGrafico(
        "anexosSituacao",
        "graficoAnexosSituacao",
        "graficoAnexosSituacaoVazio",
        {
            type: "doughnut",
            data: {
                labels: graficosAnexos.situacao_entregas?.labels || [],
                datasets: [
                    {
                        data: graficosAnexos.situacao_entregas?.valores || [],
                        backgroundColor: [
                            "#0f766e",
                            "#f59e0b",
                            "#d0d7e3",
                        ],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: aspectRatioGrafico("rosca"),
                layout: {
                    padding: {
                        top: 10,
                        right: 10,
                        bottom: 10,
                        left: 10,
                    },
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#405165",
                            padding: 14,
                            boxWidth: 14,
                        },
                    },
                },
            },
        },
        "Nenhum documento esperado no periodo."
    );

    criarGrafico(
        "anexosTipo",
        "graficoAnexosTipo",
        "graficoAnexosTipoVazio",
        {
            type: "bar",
            data: {
                labels: graficosAnexos.documentos_por_tipo?.labels || [],
                datasets: [
                    {
                        label: "Documentos esperados",
                        data: graficosAnexos.documentos_por_tipo?.valores || [],
                        backgroundColor: "#1d4ed8",
                        borderRadius: 10,
                    },
                ],
            },
            options: opcoesBaseGrafico({
                aspectRatio: aspectRatioGrafico("barra"),
                plugins: { legend: { display: false } },
            }),
        },
        "Nenhum tipo de documento encontrado no periodo."
    );

    renderTabelaPendenciasAnexos(payload.tabelas?.professores_pendencias || []);
    renderTabelaRecentesAnexos(payload.tabelas?.entregas_recentes || []);
}

function preencherSelectProfessores(itens = []) {
    const select = el("relProfessorSelect");
    if (!select) return;
    select.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.innerText = Array.isArray(itens) && itens.length > 0
        ? "Selecione um professor"
        : "Nenhum professor disponivel";
    select.appendChild(placeholder);

    itens.forEach((professor) => {
        const option = document.createElement("option");
        option.value = String(professor.id || "");
        option.innerText = professor.email
            ? `${professor.nome} (${professor.email})`
            : professor.nome;
        select.appendChild(option);
    });
}

async function carregarProfessoresRelatorio() {
    professoresRelatorio = await fetchJson("/api/relatorios/professores", { headers });
    preencherSelectProfessores(professoresRelatorio);
}

function obterProfessorRelatorioSelecionadoId() {
    return Number(el("relProfessorSelect")?.value || 0);
}

function atualizarAcoesRelatorioProfessor(habilitado) {
    const podeAgir = Boolean(habilitado);
    el("btnBaixarRelatorioProfessor").disabled = !podeAgir;
    el("btnEnviarRelatorioProfessor").disabled = !podeAgir;
}

function renderListaAlertasProfessor(alertas = []) {
    const lista = el("listaAlertasProfessor");
    lista.innerHTML = "";
    const itens = Array.isArray(alertas) && alertas.length > 0
        ? alertas
        : ["Sem alertas relevantes para o periodo."];

    itens.forEach((texto) => {
        const li = document.createElement("li");
        li.innerText = texto;
        lista.appendChild(li);
    });
}

function renderTabelaProfessorPendencias(itens = []) {
    renderTabelaComLinhas("tabelaProfessorPendenciasBody", itens, 3, (item) => [
        item.documento || "Documento nao informado",
        formatarDataHoraRelatorios(item.prazo),
        item.situacao || "Pendente",
    ]);
}

function renderTabelaProfessorImpressoes(itens = []) {
    renderTabelaComLinhas("tabelaProfessorImpressoesBody", itens, 4, (item) => [
        item.arquivo || "Arquivo nao informado",
        formatarDataHoraRelatorios(item.criado_em),
        formatarNumero(item.paginas_totais || 0),
        formatarNumero(item.copias || 1),
    ]);
}

function renderTabelaProfessorRecursos(itens = []) {
    renderTabelaComLinhas("tabelaProfessorRecursosBody", itens, 4, (item) => [
        paraDataBr(item.data || ""),
        item.recurso_nome || "Recurso nao informado",
        item.turma || "-",
        item.tema_aula || "-",
    ]);
}

function renderRelatorioProfessor(payload = {}) {
    const resumo = payload.resumo || {};
    renderResumoSimples("professorResumo", [
        { titulo: "Paginas impressas", valor: formatarNumero(resumo.total_paginas || 0) },
        { titulo: "Jobs de impressao", valor: formatarNumero(resumo.total_jobs || 0) },
        { titulo: "Reservas de recursos", valor: formatarNumero(resumo.total_reservas || 0) },
        { titulo: "Pendencias de anexos", valor: formatarNumero(resumo.total_pendencias || 0) },
        { titulo: "Entregas registradas", valor: formatarNumero(resumo.total_entregas || 0) },
    ]);
    renderListaAlertasProfessor(payload.alertas || []);
    renderTabelaProfessorPendencias(payload.anexos?.pendencias || []);
    renderTabelaProfessorImpressoes(payload.impressoes?.recentes || []);
    renderTabelaProfessorRecursos(payload.recursos?.recentes || []);
}

async function carregarRelatorioProfessor() {
    const professorId = obterProfessorRelatorioSelecionadoId();
    if (!professorId) {
        setMensagemProfessor("Selecione um professor para gerar o resumo.", "erro");
        atualizarAcoesRelatorioProfessor(false);
        return;
    }

    setMensagemProfessor("Carregando resumo do professor...");
    relatorioProfessorAtual = await fetchJson(
        `/api/relatorios/professores/${professorId}/resumo${queryPeriodo()}`,
        { headers }
    );
    renderRelatorioProfessor(relatorioProfessorAtual);
    atualizarAcoesRelatorioProfessor(true);
    setMensagemProfessor("Resumo do professor atualizado.");
}

function baixarRelatorioProfessorPdf() {
    const professorId = obterProfessorRelatorioSelecionadoId();
    if (!professorId) {
        setMensagemProfessor("Selecione um professor antes de baixar o PDF.", "erro");
        return;
    }
    window.open(`/api/relatorios/professores/${professorId}/pdf${queryPeriodo()}`, "_blank", "noopener");
}

async function enviarRelatorioProfessorEmail() {
    const professorId = obterProfessorRelatorioSelecionadoId();
    if (!professorId) {
        setMensagemProfessor("Selecione um professor antes de enviar o relatorio.", "erro");
        return;
    }

    setMensagemProfessor("Enviando relatorio por email...");
    const resposta = await fetchJson(
        `/api/relatorios/professores/${professorId}/email${queryPeriodo()}`,
        {
            method: "POST",
            headers: Object.assign({}, headers, { "Content-Type": "application/json" }),
            body: JSON.stringify({}),
        }
    );
    setMensagemProfessor(resposta?.mensagem || "Relatorio enviado com sucesso.");
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

    const cargo = normalizarCargoUsuario(usuario);
    el("relatoriosUsuario").innerText = `${usuario.nome} | ${cargo}`;
    return usuario;
}

async function carregarRelatorios() {
    setMensagem("Atualizando relatorios...");
    const [payloadDashboard, payloadAnexos] = await Promise.all([
        fetchJson(`/api/relatorios/dashboard${queryPeriodo()}`, { headers }),
        fetchJson(`/api/relatorios/anexos${queryPeriodo()}`, { headers }),
    ]);

    dashboardAtual = payloadDashboard;
    anexosAtual = payloadAnexos;

    atualizarResumoPeriodo(payloadDashboard.periodo || {});
    renderDashboard(payloadDashboard);
    renderImpressoes(payloadDashboard);
    renderRecursos(payloadDashboard);
    renderAnexos(payloadAnexos);
    if (obterProfessorRelatorioSelecionadoId()) {
        await carregarRelatorioProfessor();
    }
    setMensagem("Relatorios atualizados.");
}

function registrarResizeGraficos() {
    let resizeTimeoutId = 0;
    window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimeoutId);
        resizeTimeoutId = window.setTimeout(() => {
            const compacto = viewportEhCompacto();
            if (compacto === viewportCompactoAtual || !dashboardAtual) {
                return;
            }

            viewportCompactoAtual = compacto;
            renderDashboard(dashboardAtual);
            renderImpressoes(dashboardAtual);
            renderRecursos(dashboardAtual);
            if (anexosAtual) {
                renderAnexos(anexosAtual);
            }
        }, 120);
    });
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
            await carregarRelatorios();
        } catch (err) {
            setMensagem(err.message || "Nao foi possivel carregar os relatorios.", "erro");
        }
    });

    el("btnPeriodoAtual").addEventListener("click", async () => {
        aplicarPeriodoAtual();
        try {
            await carregarRelatorios();
        } catch (err) {
            setMensagem(err.message || "Nao foi possivel carregar os relatorios.", "erro");
        }
    });

    el("btnExportarPdf").addEventListener("click", gerarPdfPainel);

    document
        .querySelectorAll("[data-relatorios-tab-trigger]:not([disabled])")
        .forEach((botao) => {
            botao.addEventListener("click", () => {
                ativarTab(botao.dataset.relatoriosTabTrigger);
            });
        });

    el("btnCarregarRelatorioProfessor").addEventListener("click", async () => {
        try {
            await carregarRelatorioProfessor();
        } catch (err) {
            setMensagemProfessor(err.message || "Nao foi possivel carregar o relatorio do professor.", "erro");
        }
    });

    el("btnBaixarRelatorioProfessor").addEventListener("click", () => {
        baixarRelatorioProfessorPdf();
    });

    el("btnEnviarRelatorioProfessor").addEventListener("click", async () => {
        try {
            await enviarRelatorioProfessorEmail();
        } catch (err) {
            setMensagemProfessor(err.message || "Nao foi possivel enviar o relatorio.", "erro");
        }
    });

    el("relProfessorSelect").addEventListener("change", () => {
        relatorioProfessorAtual = null;
        atualizarAcoesRelatorioProfessor(false);
        setMensagemProfessor("");
    });
}

async function init() {
    try {
        aplicarPeriodoAtual();
        registrarEventos();
        registrarResizeGraficos();
        const usuario = await carregarUsuario();
        if (!usuario) {
            return;
        }
        await carregarProfessoresRelatorio();
        await carregarRelatorios();
    } catch (err) {
        setMensagem(err.message || "Erro ao carregar o modulo de relatorios.", "erro");
    }
}

init();
