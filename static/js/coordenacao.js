const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    Authorization: `Bearer ${token}`
};

const headersJson = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
};

let abaCoordAtiva = "ocorrencias";
let ocorrenciaEmEdicaoId = null;
let ocorrenciaSelecionadaId = null;
let estudanteEmEdicao = null;
let ocorrenciasCache = [];
let estudantesCache = [];
let relatorioOcorrenciasCache = [];
let relatorioOcorrenciasCarregado = false;
let opcoesOcorrencias = {
    turmas: [],
    professores: [],
    status: [],
    acoes_aplicadas: [],
    status_padrao: "registrado"
};
const MAX_AULAS_EXIBICAO = 5;
const TURNO_OFFSET_FAIXA = {
    MATUTINO: 0,
    INTEGRAL: 0,
    VESPERTINO: 5,
    VESPERTINO_EM: 5
};

const rotulosAcao = new Map();
const rotulosStatus = new Map();
const mapaBuscaEstudantes = new Map();
let timerBuscaEstudantes = null;

function el(id) {
    return document.getElementById(id);
}

function normalizarCargoUsuario(usuario = {}) {
    const cargo = String(usuario.cargo || "").trim().toUpperCase();
    if (cargo) return cargo;

    const perfil = String(usuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return "ADMIN";
    if (perfil === "coordenador") return "COORDENADOR";
    return "PROFESSOR";
}

function setMensagemOcorrencias(texto, erro = false) {
    const target = el("msgOcorrencias");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function setMensagemEstudantes(texto, erro = false) {
    const target = el("msgEstudantes");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function setMensagemRelatorios(texto, erro = false) {
    const target = el("msgRelatorios");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function normalizarErro(res, body) {
    if (body && body.detail) return body.detail;
    return `Erro ${res.status}`;
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let body = null;
    try {
        body = await res.json();
    } catch (_err) {
        body = null;
    }

    if (res.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
        throw new Error("Sessao expirada.");
    }

    if (!res.ok) {
        const erro = new Error(normalizarErro(res, body));
        erro.status = res.status;
        throw erro;
    }
    return body;
}

async function requisitarExclusao(urlDelete, urlFallback) {
    try {
        return await fetchJson(urlDelete, {
            method: "DELETE",
            headers
        });
    } catch (err) {
        if (err?.status !== 405) {
            throw err;
        }

        return fetchJson(urlFallback, {
            method: "POST",
            headers
        });
    }
}

function formatarDataBr(dataIso) {
    if (!dataIso) return "Nao informada";
    const data = new Date(`${dataIso}T00:00:00`);
    if (Number.isNaN(data.getTime())) return dataIso;
    return data.toLocaleDateString("pt-BR");
}

function formatarDataHora(dataHoraSql) {
    if (!dataHoraSql) return "Nao informado";
    const data = new Date(String(dataHoraSql).replace(" ", "T"));
    if (Number.isNaN(data.getTime())) return String(dataHoraSql);
    return data.toLocaleString("pt-BR");
}

function rotuloAcao(acao) {
    return rotulosAcao.get(acao) || acao || "Nao informado";
}

function rotuloStatus(status) {
    return rotulosStatus.get(status) || status || "Nao informado";
}

function classeStatus(status) {
    const texto = String(status || "").trim().toLowerCase();
    if (!texto) return "status-registrado";
    return `status-${texto.replace(/[^a-z0-9_]/g, "-")}`;
}

function classeStatusEstudante(ativo) {
    return ativo ? "status-resolvido" : "status-aguardando_responsavel";
}

function listarBotoesAbasCoord() {
    return Array.from(document.querySelectorAll("[data-coord-tab-trigger]"));
}

function listarPaineisAbasCoord() {
    return Array.from(document.querySelectorAll("[data-coord-tab-panel]"));
}

function ativarAbaCoordenacao(abaId) {
    abaCoordAtiva = abaId;
    listarBotoesAbasCoord().forEach((botao) => {
        const ativa = botao.dataset.coordTabTrigger === abaId;
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
    });
    listarPaineisAbasCoord().forEach((painel) => {
        const ativo = painel.dataset.coordTabPanel === abaId;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
    if (abaId === "relatorios" && !relatorioOcorrenciasCarregado) {
        carregarRelatorioOcorrencias().catch((err) => {
            setMensagemRelatorios(err.message, true);
        });
    }
}

function painelFormularioOcorrenciaAberto() {
    const painel = el("painelFormOcorrencia");
    return Boolean(painel) && !painel.hidden;
}

function atualizarBotaoNovaOcorrencia() {
    const botao = el("btnNovaOcorrencia");
    if (!botao) return;

    const painelAberto = painelFormularioOcorrenciaAberto();
    if (!painelAberto) {
        botao.innerText = "Registrar ocorrencia";
    } else if (ocorrenciaEmEdicaoId) {
        botao.innerText = "Nova ocorrencia";
    } else {
        botao.innerText = "Ocultar formulario";
    }

    botao.setAttribute("aria-expanded", painelAberto ? "true" : "false");
}

function mostrarPainelFormularioOcorrencia({ scroll = false } = {}) {
    const painel = el("painelFormOcorrencia");
    if (!painel) return;
    painel.hidden = false;
    atualizarBotaoNovaOcorrencia();
    if (scroll) {
        painel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function ocultarPainelFormularioOcorrencia() {
    const painel = el("painelFormOcorrencia");
    if (!painel) return;
    painel.hidden = true;
    atualizarBotaoNovaOcorrencia();
}

function preencherSelect(selectId, opcoes, {
    incluirTodos = false,
    placeholder = "",
    valorPadrao = "",
    obterRotulo = null
} = {}) {
    const select = el(selectId);
    if (!select) return;

    select.innerHTML = "";

    if (incluirTodos) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Todos";
        select.appendChild(option);
    } else if (placeholder) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = placeholder;
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
    }

    (opcoes || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.id);
        option.innerText = typeof obterRotulo === "function"
            ? obterRotulo(item)
            : (item.nome || item.id);
        select.appendChild(option);
    });

    if (valorPadrao !== "") {
        select.value = String(valorPadrao);
    }
}

function preencherDatalist(datalistId, mapa, itens) {
    const datalist = el(datalistId);
    if (!datalist) return;
    datalist.innerHTML = "";
    mapa.clear();

    (itens || []).forEach((item) => {
        const label = String(item.label || item.nome || "").trim();
        if (!label) return;

        const option = document.createElement("option");
        option.value = label;
        datalist.appendChild(option);
        mapa.set(label, item);
    });
}

function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
}

function aulaLabel(aula) {
    return `${aula}ª aula`;
}

function faixaGlobalPorTurnoEAula(turnoId, aulaTurno) {
    const turno = normalizarTurnoId(turnoId);
    const aula = Number(aulaTurno || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(aula) || aula <= 0) return 0;

    let faixaGlobal = aula + offset;
    if (turno === "INTEGRAL" && aula > 5) {
        faixaGlobal += 1;
    }
    return faixaGlobal;
}

function aulaTurnoPorFaixa(turnoId, faixaGlobal) {
    const turno = normalizarTurnoId(turnoId);
    const faixa = Number(faixaGlobal || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(faixa) || faixa <= 0) return 0;

    if (turno === "INTEGRAL") {
        if (faixa >= 1 && faixa <= 5) return faixa;
        if (faixa >= 7) return faixa - 1;
        return 0;
    }

    return faixa - offset;
}

function obterTurmaOpcaoPorId(turmaId) {
    const turmaIdNumero = Number(turmaId || 0);
    return (opcoesOcorrencias.turmas || []).find((item) => Number(item.id) === turmaIdNumero) || null;
}

function obterProfessorOpcaoPorId(professorId) {
    const professorIdNumero = Number(professorId || 0);
    return (opcoesOcorrencias.professores || []).find((item) => Number(item.id) === professorIdNumero) || null;
}

function faixasDisponiveisTurma(turma) {
    if (!turma || !turma.turno_valido) return [];

    const faixasApi = Array.isArray(turma.faixas_disponiveis)
        ? turma.faixas_disponiveis.map((valor) => Number(valor)).filter((valor) => Number.isInteger(valor) && valor > 0)
        : [];
    if (faixasApi.length > 0) {
        return faixasApi;
    }

    const totalAulas = Number(turma.aulas || 0);
    const faixasCalculadas = [];
    for (let aula = 1; aula <= totalAulas; aula++) {
        const faixa = faixaGlobalPorTurnoEAula(turma.turno, aula);
        if (faixa > 0) {
            faixasCalculadas.push(faixa);
        }
    }
    return faixasCalculadas;
}

function resolverFaixaOcorrenciaParaTurma(turma, aulaValor) {
    const texto = String(aulaValor || "").trim();
    if (!texto) return 0;

    const numero = Number.parseInt(texto, 10);
    if (!Number.isInteger(numero) || numero <= 0) return 0;

    const faixasTurma = faixasDisponiveisTurma(turma);
    if (faixasTurma.includes(numero)) {
        return numero;
    }

    const totalAulas = Number(turma?.aulas || 0);
    if (Number.isInteger(totalAulas) && numero <= totalAulas) {
        const faixaCalculada = faixaGlobalPorTurnoEAula(turma.turno, numero);
        if (faixaCalculada > 0 && faixasTurma.includes(faixaCalculada)) {
            return faixaCalculada;
        }
    }

    return 0;
}

function formatarAulaOcorrencia(ocorrencia) {
    const turma = obterTurmaOpcaoPorId(ocorrencia?.turma_id);
    const faixa = resolverFaixaOcorrenciaParaTurma(turma, ocorrencia?.aula);
    if (faixa <= 0 || !turma) {
        return ocorrencia?.aula || "Nao informada";
    }

    const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
    if (aulaTurno <= 0) {
        return `Faixa ${faixa}`;
    }
    return `${aulaLabel(aulaTurno)} (faixa ${faixa})`;
}

function atualizarSelectAulasPorTurma(turmaId, faixaSelecionada = null) {
    const select = el("ocorrenciaAula");
    const turma = obterTurmaOpcaoPorId(turmaId);

    select.innerHTML = "";
    if (!turma || !turma.turno_valido || Number(turma.aulas || 0) <= 0) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Configure o turno da turma no painel admin";
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        return;
    }

    const faixasTurma = faixasDisponiveisTurma(turma);
    const faixasManha = faixasTurma.filter((faixa) => faixa <= MAX_AULAS_EXIBICAO);
    const faixasTarde = faixasTurma.filter((faixa) => faixa > MAX_AULAS_EXIBICAO);

    const adicionarSeparadorTurno = (rotulo) => {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = `----- ${rotulo} -----`;
        option.disabled = true;
        select.appendChild(option);
    };

    const adicionarOpcaoFaixa = (faixa) => {
        const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
        const option = document.createElement("option");
        option.value = String(faixa);
        option.innerText = aulaTurno > 0
            ? `${aulaLabel(aulaTurno)}`
            : `Faixa ${faixa}`;
        select.appendChild(option);
    };

    if (faixasManha.length > 0) {
        adicionarSeparadorTurno("Matutino");
        faixasManha.forEach(adicionarOpcaoFaixa);
    }
    if (faixasTarde.length > 0) {
        adicionarSeparadorTurno("Vespertino");
        faixasTarde.forEach(adicionarOpcaoFaixa);
    }

    select.disabled = false;
    const faixaPreferida = Number(faixaSelecionada || 0);
    if (faixaPreferida > 0 && faixasTurma.includes(faixaPreferida)) {
        select.value = String(faixaPreferida);
    } else {
        select.value = faixasTurma.length > 0 ? String(faixasTurma[0]) : "";
    }
}

function limparFormularioOcorrencia({ manterAberto = false } = {}) {
    el("formOcorrencia").reset();
    ocorrenciaEmEdicaoId = null;
    el("ocorrenciaEstudanteId").value = "";

    const turmaSelect = el("ocorrenciaTurmaId");
    const professorSelect = el("ocorrenciaProfessorRequerenteId");
    if (opcoesOcorrencias.turmas.length > 0) {
        turmaSelect.value = String(opcoesOcorrencias.turmas[0].id);
    }
    if (opcoesOcorrencias.professores.length > 0) {
        professorSelect.value = String(opcoesOcorrencias.professores[0].id);
    }
    atualizarSelectAulasPorTurma(turmaSelect.value);

    const hoje = new Date();
    el("ocorrenciaData").value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    if (opcoesOcorrencias.status_padrao) {
        el("ocorrenciaStatus").value = opcoesOcorrencias.status_padrao;
    }
    el("tituloFormOcorrencia").innerText = "Nova ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "none";
    if (manterAberto) {
        mostrarPainelFormularioOcorrencia();
    } else {
        ocultarPainelFormularioOcorrencia();
    }
}

function preencherFormularioOcorrencia(ocorrencia) {
    ocorrenciaEmEdicaoId = Number(ocorrencia.id);
    el("ocorrenciaBuscaEstudante").value = ocorrencia.nome_estudante || "";
    el("ocorrenciaEstudanteId").value = ocorrencia.estudante_id || "";

    const turmaId = String(ocorrencia.turma_id || "");
    el("ocorrenciaTurmaId").value = turmaId;

    const turmaAtual = obterTurmaOpcaoPorId(turmaId);
    const faixaAula = resolverFaixaOcorrenciaParaTurma(turmaAtual, ocorrencia.aula);
    atualizarSelectAulasPorTurma(turmaId, faixaAula);

    const professorPorId = obterProfessorOpcaoPorId(ocorrencia.professor_requerente_id);
    if (professorPorId) {
        el("ocorrenciaProfessorRequerenteId").value = String(professorPorId.id);
    } else {
        const professorPorNome = (opcoesOcorrencias.professores || []).find(
            (professor) => String(professor.nome || "").trim().toLowerCase() === String(ocorrencia.professor_requerente || "").trim().toLowerCase()
        );
        el("ocorrenciaProfessorRequerenteId").value = professorPorNome ? String(professorPorNome.id) : "";
    }

    el("ocorrenciaDisciplina").value = ocorrencia.disciplina || "";
    el("ocorrenciaData").value = ocorrencia.data_ocorrencia || "";
    el("ocorrenciaHorario").value = ocorrencia.horario_ocorrencia || "";
    el("ocorrenciaDescricao").value = ocorrencia.descricao || "";
    el("ocorrenciaAcaoAplicada").value = ocorrencia.acao_aplicada || "";
    el("ocorrenciaStatus").value = ocorrencia.status || opcoesOcorrencias.status_padrao || "registrado";
    el("tituloFormOcorrencia").innerText = "Editar ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "inline-block";
    ativarAbaCoordenacao("ocorrencias");
    mostrarPainelFormularioOcorrencia({ scroll: true });
}

function selecionarOcorrencia(ocorrencia) {
    ocorrenciaSelecionadaId = ocorrencia ? Number(ocorrencia.id || 0) || null : null;
    renderDetalhesOcorrencia(ocorrencia || null);
    renderTabelaOcorrencias();
}

function renderDetalhesOcorrencia(ocorrencia) {
    const container = el("detalhesOcorrencia");
    if (!container) return;
    if (!ocorrencia) {
        container.innerText = "Selecione uma ocorrencia para visualizar os detalhes.";
        return;
    }

    container.innerHTML = "";
    const campos = [
        ["Estudante", ocorrencia.nome_estudante],
        ["Turma", ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`],
        ["Professor requerente", ocorrencia.professor_requerente],
        ["Disciplina", ocorrencia.disciplina],
        ["Data", formatarDataBr(ocorrencia.data_ocorrencia)],
        ["Aula", formatarAulaOcorrencia(ocorrencia)],
        ["Horario", ocorrencia.horario_ocorrencia],
        ["Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)],
        ["Status", rotuloStatus(ocorrencia.status)],
        ["Descricao", ocorrencia.descricao],
        ["Criado em", formatarDataHora(ocorrencia.criado_em)],
        ["Atualizado em", formatarDataHora(ocorrencia.atualizado_em)]
    ];

    campos.forEach(([rotulo, valor]) => {
        const linha = document.createElement("p");
        linha.className = "coordenacao-detail-line";
        const strong = document.createElement("strong");
        strong.innerText = `${rotulo}: `;
        const span = document.createElement("span");
        span.innerText = valor || "Nao informado";
        linha.appendChild(strong);
        linha.appendChild(span);
        container.appendChild(linha);
    });
}

function valorCampo(id) {
    return String(el(id)?.value || "").trim();
}

function montarQueryOcorrencias({
    nomeEstudanteId,
    turmaIdId,
    statusId,
    dataInicialId,
    dataFinalId
}) {
    const params = new URLSearchParams();
    const nomeEstudante = valorCampo(nomeEstudanteId);
    const turmaId = valorCampo(turmaIdId);
    const status = valorCampo(statusId);
    const dataInicial = valorCampo(dataInicialId);
    const dataFinal = valorCampo(dataFinalId);

    if (nomeEstudante) params.set("nome_estudante", nomeEstudante);
    if (turmaId) params.set("turma_id", turmaId);
    if (status) params.set("status", status);
    if (dataInicial) params.set("data_inicial", dataInicial);
    if (dataFinal) params.set("data_final", dataFinal);

    return params.toString() ? `?${params.toString()}` : "";
}

function descreverFiltrosOcorrencias(configuracao) {
    const partes = [];
    const nomeEstudante = valorCampo(configuracao.nomeEstudanteId);
    const turmaId = valorCampo(configuracao.turmaIdId);
    const status = valorCampo(configuracao.statusId);
    const dataInicial = valorCampo(configuracao.dataInicialId);
    const dataFinal = valorCampo(configuracao.dataFinalId);

    if (nomeEstudante) {
        partes.push(`Estudante: ${nomeEstudante}`);
    }
    if (turmaId) {
        const turma = obterTurmaOpcaoPorId(turmaId);
        partes.push(`Turma: ${turma?.nome || `ID ${turmaId}`}`);
    }
    if (status) {
        partes.push(`Status: ${rotuloStatus(status)}`);
    }
    if (dataInicial && dataFinal) {
        partes.push(`Periodo: ${formatarDataBr(dataInicial)} ate ${formatarDataBr(dataFinal)}`);
    } else if (dataInicial) {
        partes.push(`A partir de: ${formatarDataBr(dataInicial)}`);
    } else if (dataFinal) {
        partes.push(`Ate: ${formatarDataBr(dataFinal)}`);
    }

    return partes.length > 0 ? partes.join(" | ") : "Sem filtro aplicado.";
}

function totalOcorrenciasPorStatus(lista, status) {
    return (lista || []).filter((ocorrencia) => String(ocorrencia.status || "").trim() === status).length;
}

function atualizarResumoOcorrencias() {
    const total = ocorrenciasCache.length;
    const acompanhamento = totalOcorrenciasPorStatus(ocorrenciasCache, "em_acompanhamento");
    const aguardando = totalOcorrenciasPorStatus(ocorrenciasCache, "aguardando_responsavel");
    const resolvido = totalOcorrenciasPorStatus(ocorrenciasCache, "resolvido");

    if (el("resumoOcorrenciasTotal")) {
        el("resumoOcorrenciasTotal").innerText = String(total);
    }
    if (el("resumoOcorrenciasAcompanhamento")) {
        el("resumoOcorrenciasAcompanhamento").innerText = String(acompanhamento);
    }
    if (el("resumoOcorrenciasAguardando")) {
        el("resumoOcorrenciasAguardando").innerText = String(aguardando);
    }
    if (el("resumoOcorrenciasResolvido")) {
        el("resumoOcorrenciasResolvido").innerText = String(resolvido);
    }
    if (el("resumoOcorrenciasPeriodo")) {
        el("resumoOcorrenciasPeriodo").innerText = descreverFiltrosOcorrencias({
            nomeEstudanteId: "filtroNomeEstudante",
            turmaIdId: "filtroTurmaId",
            statusId: "filtroStatus",
            dataInicialId: "filtroDataInicial",
            dataFinalId: "filtroDataFinal"
        });
    }
}

function agruparOcorrencias(lista, obterChave, obterRotulo) {
    const mapa = new Map();

    (lista || []).forEach((ocorrencia) => {
        const chaveBruta = obterChave(ocorrencia);
        const rotuloBruto = obterRotulo(ocorrencia);
        const chave = String(chaveBruta || rotuloBruto || "nao_informado").trim();
        const rotulo = String(rotuloBruto || chaveBruta || "Nao informado").trim() || "Nao informado";
        const atual = mapa.get(chave) || { label: rotulo, total: 0 };
        atual.total += 1;
        mapa.set(chave, atual);
    });

    return Array.from(mapa.values()).sort((a, b) => {
        if (b.total !== a.total) {
            return b.total - a.total;
        }
        return a.label.localeCompare(b.label, "pt-BR");
    });
}

function renderRankingLista(idLista, itens, vazio, totalBase = 0) {
    const lista = el(idLista);
    if (!lista) return;
    lista.innerHTML = "";

    if (!Array.isArray(itens) || itens.length === 0) {
        const itemVazio = document.createElement("li");
        itemVazio.className = "coordenacao-empty-state";
        itemVazio.innerText = vazio;
        lista.appendChild(itemVazio);
        return;
    }

    itens.slice(0, 5).forEach((item) => {
        const li = document.createElement("li");
        li.className = "coordenacao-ranking-item";

        const label = document.createElement("span");
        label.className = "coordenacao-ranking-label";
        label.innerText = item.label;

        const total = document.createElement("strong");
        total.innerText = String(item.total);

        const meta = document.createElement("span");
        meta.className = "coordenacao-ranking-meta";
        if (totalBase > 0) {
            const percentual = Math.round((item.total / totalBase) * 100);
            meta.innerText = `${percentual}% do relatorio`;
        } else {
            meta.innerText = `${item.total} registro(s)`;
        }

        li.appendChild(label);
        li.appendChild(total);
        li.appendChild(meta);
        lista.appendChild(li);
    });
}

function atualizarResumoRelatorioOcorrencias() {
    const total = relatorioOcorrenciasCache.length;
    const resolvidas = totalOcorrenciasPorStatus(relatorioOcorrenciasCache, "resolvido");
    const abertas = total - resolvidas;
    const turmasImpactadas = new Set(
        relatorioOcorrenciasCache
            .map((ocorrencia) => String(ocorrencia.turma_nome || ocorrencia.turma_id || "").trim())
            .filter(Boolean)
    ).size;

    if (el("relatorioMetricasTotal")) {
        el("relatorioMetricasTotal").innerText = String(total);
    }
    if (el("relatorioMetricasAbertas")) {
        el("relatorioMetricasAbertas").innerText = String(abertas);
    }
    if (el("relatorioMetricasResolvidas")) {
        el("relatorioMetricasResolvidas").innerText = String(resolvidas);
    }
    if (el("relatorioMetricasTurmas")) {
        el("relatorioMetricasTurmas").innerText = String(turmasImpactadas);
    }

    const descricaoFiltros = descreverFiltrosOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
    if (el("relatorioPeriodo")) {
        el("relatorioPeriodo").innerText = total > 0
            ? `Recorte atual: ${descricaoFiltros}`
            : `Nenhuma ocorrencia encontrada. ${descricaoFiltros}`;
    }

    renderRankingLista(
        "relatorioResumoStatus",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.status,
            (ocorrencia) => rotuloStatus(ocorrencia.status)
        ),
        "Nenhum status encontrado para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoTurmas",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.turma_id,
            (ocorrencia) => ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`
        ),
        "Nenhuma turma encontrada para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoProfessores",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.professor_requerente_id || ocorrencia.professor_requerente,
            (ocorrencia) => ocorrencia.professor_requerente || "Nao informado"
        ),
        "Nenhum professor encontrado para o recorte selecionado.",
        total
    );
}

function renderTabelaRelatorioOcorrencias() {
    const tbody = el("tbodyRelatorioOcorrencias");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(relatorioOcorrenciasCache) || relatorioOcorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 6;
        td.className = "booking-empty";
        td.innerText = "Nenhuma ocorrencia encontrada para o relatorio.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    relatorioOcorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Estudante", ocorrencia.nome_estudante || ""));
        tr.appendChild(criarCelulaTabela("Turma", ocorrencia.turma_nome || ""));
        tr.appendChild(criarCelulaTabela("Professor requerente", ocorrencia.professor_requerente || ""));
        tr.appendChild(criarCelulaTabela("Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)));
        tr.appendChild(criarCelulaTabela("Status", rotuloStatus(ocorrencia.status)));
        tbody.appendChild(tr);
    });
}

function renderRelatorioOcorrencias() {
    atualizarResumoRelatorioOcorrencias();
    renderTabelaRelatorioOcorrencias();
}

function invalidarRelatorioOcorrencias() {
    if (!relatorioOcorrenciasCarregado) return;
    relatorioOcorrenciasCarregado = false;
    setMensagemRelatorios("Dados atualizados. Gere o relatorio novamente para refletir as alteracoes.");
}

async function carregarOpcoesOcorrencias() {
    const opcoesApi = await fetchJson("/ocorrencias/opcoes", { headers });
    opcoesOcorrencias = {
        turmas: Array.isArray(opcoesApi.turmas) ? opcoesApi.turmas : [],
        professores: Array.isArray(opcoesApi.professores) ? opcoesApi.professores : [],
        status: Array.isArray(opcoesApi.status) ? opcoesApi.status : [],
        acoes_aplicadas: Array.isArray(opcoesApi.acoes_aplicadas) ? opcoesApi.acoes_aplicadas : [],
        status_padrao: opcoesApi.status_padrao || "registrado"
    };

    rotulosAcao.clear();
    rotulosStatus.clear();
    (opcoesOcorrencias.acoes_aplicadas || []).forEach((item) => {
        rotulosAcao.set(String(item.id), item.nome || item.id);
    });
    (opcoesOcorrencias.status || []).forEach((item) => {
        rotulosStatus.set(String(item.id), item.nome || item.id);
    });

    preencherSelect("ocorrenciaTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("relatorioTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("ocorrenciaProfessorRequerenteId", opcoesOcorrencias.professores, {
        placeholder: "Selecione o professor requerente",
        obterRotulo: (item) => {
            const nome = String(item.nome || "").trim();
            const email = String(item.email || "").trim();
            return email ? `${nome} (${email})` : nome;
        }
    });
    preencherSelect("ocorrenciaAcaoAplicada", opcoesOcorrencias.acoes_aplicadas, { placeholder: "Selecione a acao aplicada" });
    preencherSelect("ocorrenciaStatus", opcoesOcorrencias.status, {
        placeholder: "Selecione o status",
        valorPadrao: opcoesOcorrencias.status_padrao || "registrado"
    });
    preencherSelect("filtroStatus", opcoesOcorrencias.status, { incluirTodos: true });
    preencherSelect("relatorioStatus", opcoesOcorrencias.status, { incluirTodos: true });

    preencherSelect("estudanteTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroEstudanteTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });

    const turmaInicial = opcoesOcorrencias.turmas[0];
    atualizarSelectAulasPorTurma(turmaInicial ? turmaInicial.id : "");
}

function queryFiltrosOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "filtroNomeEstudante",
        turmaIdId: "filtroTurmaId",
        statusId: "filtroStatus",
        dataInicialId: "filtroDataInicial",
        dataFinalId: "filtroDataFinal"
    });
}

function queryFiltrosRelatorioOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
}

function queryFiltrosEstudantes() {
    const params = new URLSearchParams();
    const nome = el("filtroEstudanteNome").value.trim();
    const turmaId = el("filtroEstudanteTurmaId").value;
    if (nome) params.set("nome", nome);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("incluir_inativos", "true");
    return `?${params.toString()}`;
}

function criarCelulaTabela(rotulo, conteudo = "") {
    const td = document.createElement("td");
    td.dataset.label = rotulo;
    if (typeof Node !== "undefined" && conteudo instanceof Node) {
        td.appendChild(conteudo);
    } else {
        td.innerText = conteudo ?? "";
    }
    return td;
}

function renderTabelaOcorrencias() {
    const tbody = el("tbodyOcorrencias");
    atualizarResumoOcorrencias();
    tbody.innerHTML = "";

    if (!Array.isArray(ocorrenciasCache) || ocorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 7;
        td.className = "booking-empty";
        td.innerText = "Nenhuma ocorrencia encontrada.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    ocorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        const selecionada = Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId);
        tr.classList.toggle("is-selected", selecionada);
        tr.addEventListener("click", () => {
            selecionarOcorrencia(ocorrencia);
        });

        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Estudante", ocorrencia.nome_estudante || ""));
        tr.appendChild(criarCelulaTabela("Turma", ocorrencia.turma_nome || ""));
        tr.appendChild(criarCelulaTabela("Professor requerente", ocorrencia.professor_requerente || ""));
        tr.appendChild(criarCelulaTabela("Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)));

        const statusBadge = document.createElement("span");
        statusBadge.className = `status-chip ${classeStatus(ocorrencia.status)}`;
        statusBadge.innerText = rotuloStatus(ocorrencia.status);
        tr.appendChild(criarCelulaTabela("Status", statusBadge));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnVer = document.createElement("button");
        btnVer.type = "button";
        btnVer.innerText = "Ver";
        btnVer.addEventListener("click", (event) => {
            event.stopPropagation();
            selecionarOcorrencia(ocorrencia);
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", (event) => {
            event.stopPropagation();
            selecionarOcorrencia(ocorrencia);
            preencherFormularioOcorrencia(ocorrencia);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", (event) => {
            event.stopPropagation();
            excluirOcorrencia(ocorrencia);
        });

        linhaAcoes.appendChild(btnVer);
        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

function renderTabelaEstudantes() {
    const tbody = el("tbodyEstudantes");
    tbody.innerHTML = "";

    const filtroStatus = el("filtroEstudanteStatus").value;
    const estudantesFiltrados = (estudantesCache || []).filter((estudante) => {
        if (filtroStatus === "ativos") return Boolean(estudante.ativo);
        if (filtroStatus === "inativos") return !Boolean(estudante.ativo);
        return true;
    });

    if (estudantesFiltrados.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "booking-empty";
        td.innerText = "Nenhum estudante encontrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    estudantesFiltrados.forEach((estudante) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Nome", estudante.nome || ""));
        tr.appendChild(criarCelulaTabela("Turma", estudante.turma_nome || ""));

        const badge = document.createElement("span");
        badge.className = `status-chip ${classeStatusEstudante(Boolean(estudante.ativo))}`;
        badge.innerText = estudante.ativo ? "Ativo" : "Inativo";
        tr.appendChild(criarCelulaTabela("Status", badge));
        tr.appendChild(criarCelulaTabela("Atualizado em", formatarDataHora(estudante.atualizado_em)));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => iniciarEdicaoEstudante(estudante));

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = estudante.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/estudantes/${estudante.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(estudante.ativo) })
                });
                setMensagemEstudantes("Status atualizado.");
                await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
            } catch (err) {
                setMensagemEstudantes(err.message, true);
            }
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", () => {
            excluirEstudante(estudante);
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnStatus);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

async function carregarOcorrencias() {
    ocorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosOcorrencias()}`, { headers });
    const ocorrenciaSelecionada = ocorrenciasCache.find(
        (ocorrencia) => Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId)
    ) || null;

    if (ocorrenciaSelecionada) {
        renderDetalhesOcorrencia(ocorrenciaSelecionada);
    } else if (ocorrenciaSelecionadaId) {
        ocorrenciaSelecionadaId = null;
        renderDetalhesOcorrencia(null);
    }

    renderTabelaOcorrencias();
}

async function carregarRelatorioOcorrencias() {
    setMensagemRelatorios("");
    relatorioOcorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosRelatorioOcorrencias()}`, { headers });
    relatorioOcorrenciasCarregado = true;
    renderRelatorioOcorrencias();
}

async function carregarEstudantes() {
    estudantesCache = await fetchJson(`/estudantes${queryFiltrosEstudantes()}`, { headers });
    renderTabelaEstudantes();
}

function limparFormularioEstudante() {
    estudanteEmEdicao = null;
    el("formEstudante").reset();
    el("tituloFormEstudante").innerText = "Cadastrar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "none";
}

function iniciarEdicaoEstudante(estudante) {
    estudanteEmEdicao = estudante;
    el("estudanteNome").value = estudante.nome || "";
    el("estudanteTurmaId").value = String(estudante.turma_id || "");
    el("tituloFormEstudante").innerText = "Editar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "inline-block";
    ativarAbaCoordenacao("estudantes");
}

function aplicarSelecaoEstudantePorTexto() {
    const input = el("ocorrenciaBuscaEstudante");
    const hidden = el("ocorrenciaEstudanteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        return;
    }

    const item = mapaBuscaEstudantes.get(texto);
    if (!item) {
        hidden.value = "";
        return;
    }

    hidden.value = String(item.id);
    el("ocorrenciaTurmaId").value = String(item.turma_id);
    atualizarSelectAulasPorTurma(item.turma_id);
}

async function atualizarSugestoesEstudantesBusca(forcar = false) {
    const input = el("ocorrenciaBuscaEstudante");
    const termo = input.value.trim();
    const turmaId = el("ocorrenciaTurmaId").value;
    if (!forcar && termo.length < 2) {
        preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, []);
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("limite", "20");
    const itens = await fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers });
    preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, itens);
}

function agendarBuscaEstudantes() {
    if (timerBuscaEstudantes) clearTimeout(timerBuscaEstudantes);
    timerBuscaEstudantes = setTimeout(() => {
        atualizarSugestoesEstudantesBusca().catch((err) => setMensagemOcorrencias(err.message, true));
    }, 250);
}

function montarPayloadOcorrencia() {
    const textoEstudante = el("ocorrenciaBuscaEstudante").value.trim();
    const itemEstudante = mapaBuscaEstudantes.get(textoEstudante);

    const estudanteIdHidden = Number(el("ocorrenciaEstudanteId").value || 0);
    const professorIdSelecionado = Number(el("ocorrenciaProfessorRequerenteId").value || 0);
    const professorSelecionado = obterProfessorOpcaoPorId(professorIdSelecionado);

    const estudanteId = estudanteIdHidden || (itemEstudante ? Number(itemEstudante.id) : 0);
    const nomeEstudante = itemEstudante ? itemEstudante.nome : textoEstudante;

    return {
        nome_estudante: nomeEstudante || null,
        estudante_id: estudanteId > 0 ? estudanteId : null,
        turma_id: Number(el("ocorrenciaTurmaId").value),
        professor_requerente: professorSelecionado ? professorSelecionado.nome : null,
        professor_requerente_id: professorSelecionado ? Number(professorSelecionado.id) : null,
        disciplina: el("ocorrenciaDisciplina").value.trim(),
        data_ocorrencia: el("ocorrenciaData").value,
        aula: String(el("ocorrenciaAula").value || "").trim(),
        horario_ocorrencia: el("ocorrenciaHorario").value.trim(),
        descricao: el("ocorrenciaDescricao").value.trim(),
        acao_aplicada: el("ocorrenciaAcaoAplicada").value,
        status: el("ocorrenciaStatus").value || opcoesOcorrencias.status_padrao || "registrado"
    };
}

async function salvarOcorrencia(event) {
    event.preventDefault();
    const payload = montarPayloadOcorrencia();

    try {
        let ocorrencia;
        if (ocorrenciaEmEdicaoId) {
            ocorrencia = await fetchJson(`/ocorrencias/${ocorrenciaEmEdicaoId}`, {
                method: "PATCH",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Ocorrencia atualizada com sucesso.");
        } else {
            ocorrencia = await fetchJson("/ocorrencias", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Ocorrencia registrada com sucesso.");
        }

        limparFormularioOcorrencia();
        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        selecionarOcorrencia(ocorrencia);
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function limparFiltrosOcorrencias() {
    el("formFiltrosOcorrencias").reset();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarRelatorioOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function limparFiltrosRelatorioOcorrencias() {
    el("formRelatorioOcorrencias").reset();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function excluirOcorrencia(ocorrencia) {
    const nomeEstudante = String(ocorrencia?.nome_estudante || "este registro").trim();
    const confirmou = window.confirm(`Excluir a ocorrencia de ${nomeEstudante}? Esta acao nao pode ser desfeita.`);
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/ocorrencias/${ocorrencia.id}`,
            `/ocorrencias/${ocorrencia.id}/excluir`
        );

        if (Number(ocorrenciaEmEdicaoId) === Number(ocorrencia.id)) {
            limparFormularioOcorrencia();
        }
        if (Number(ocorrenciaSelecionadaId) === Number(ocorrencia.id)) {
            selecionarOcorrencia(null);
        }

        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        setMensagemOcorrencias(resposta?.mensagem || "Ocorrencia excluida com sucesso.");
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function excluirEstudante(estudante) {
    const nomeEstudante = String(estudante?.nome || "este estudante").trim();
    const confirmou = window.confirm(
        `Excluir o cadastro de ${nomeEstudante}? As ocorrencias ja registradas serao preservadas no historico.`
    );
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/estudantes/${estudante.id}`,
            `/estudantes/${estudante.id}/excluir`
        );

        if (Number(estudanteEmEdicao?.id) === Number(estudante.id)) {
            limparFormularioEstudante();
        }
        if (Number(el("ocorrenciaEstudanteId")?.value || 0) === Number(estudante.id)) {
            el("ocorrenciaEstudanteId").value = "";
        }

        invalidarRelatorioOcorrencias();
        await Promise.all([
            carregarEstudantes(),
            carregarOcorrencias(),
            atualizarSugestoesEstudantesBusca(true)
        ]);

        const totalDesvinculado = Number(resposta?.ocorrencias_desvinculadas || 0);
        const sufixo = totalDesvinculado > 0
            ? ` ${totalDesvinculado} ocorrencia(s) ficaram apenas com o nome do estudante no historico.`
            : "";
        setMensagemEstudantes((resposta?.mensagem || "Estudante excluido com sucesso.") + sufixo);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function salvarEstudante(event) {
    event.preventDefault();
    const payload = {
        nome: el("estudanteNome").value.trim(),
        turma_id: Number(el("estudanteTurmaId").value)
    };

    try {
        if (estudanteEmEdicao) {
            await fetchJson(`/estudantes/${estudanteEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    ativo: Boolean(estudanteEmEdicao.ativo)
                })
            });
            setMensagemEstudantes("Estudante atualizado com sucesso.");
        } else {
            await fetchJson("/estudantes", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemEstudantes("Estudante cadastrado com sucesso.");
        }

        limparFormularioEstudante();
        await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function filtrarEstudantes(event) {
    event.preventDefault();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function limparFiltrosEstudantes() {
    el("formFiltrosEstudantes").reset();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function validarAcessoGestao() {
    const usuario = await fetchJson("/me", { headers });
    const cargo = normalizarCargoUsuario(usuario);
    const ehGestor = cargo === "ADMIN" || cargo === "COORDENADOR";
    if (!ehGestor) {
        window.location.href = "/servicos";
        return false;
    }
    return true;
}

function registrarEventosAbas() {
    listarBotoesAbasCoord().forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAbaCoordenacao(botao.dataset.coordTabTrigger);
        });
    });
}

function registrarEventosOcorrencias() {
    el("formFiltrosOcorrencias").addEventListener("submit", filtrarOcorrencias);
    el("formOcorrencia").addEventListener("submit", salvarOcorrencia);
    el("btnLimparFiltros").addEventListener("click", limparFiltrosOcorrencias);
    el("btnNovaOcorrencia").addEventListener("click", () => {
        const painelAberto = painelFormularioOcorrenciaAberto();
        if (painelAberto && !ocorrenciaEmEdicaoId) {
            limparFormularioOcorrencia();
            return;
        }

        limparFormularioOcorrencia({ manterAberto: true });
        mostrarPainelFormularioOcorrencia({ scroll: true });
        el("ocorrenciaBuscaEstudante").focus();
    });
    el("btnFecharPainelOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });
    el("btnCancelarEdicaoOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });

    el("ocorrenciaBuscaEstudante").addEventListener("input", () => {
        el("ocorrenciaEstudanteId").value = "";
        agendarBuscaEstudantes();
    });
    el("ocorrenciaBuscaEstudante").addEventListener("change", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("blur", aplicarSelecaoEstudantePorTexto);

    el("ocorrenciaTurmaId").addEventListener("change", () => {
        el("ocorrenciaEstudanteId").value = "";
        atualizarSelectAulasPorTurma(el("ocorrenciaTurmaId").value);
        agendarBuscaEstudantes();
    });
}

function registrarEventosRelatorios() {
    el("formRelatorioOcorrencias").addEventListener("submit", filtrarRelatorioOcorrencias);
    el("btnLimparRelatorioOcorrencias").addEventListener("click", limparFiltrosRelatorioOcorrencias);
}

function registrarEventosEstudantes() {
    el("formEstudante").addEventListener("submit", salvarEstudante);
    el("btnCancelarEdicaoEstudante").addEventListener("click", limparFormularioEstudante);
    el("formFiltrosEstudantes").addEventListener("submit", filtrarEstudantes);
    el("btnLimparFiltrosEstudantes").addEventListener("click", limparFiltrosEstudantes);
    el("filtroEstudanteStatus").addEventListener("change", renderTabelaEstudantes);
}

function registrarEventosGerais() {
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnIrAdmin").addEventListener("click", () => {
        window.location.href = "/admin";
    });
    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        const autorizado = await validarAcessoGestao();
        if (!autorizado) return;

        registrarEventosAbas();
        registrarEventosOcorrencias();
        registrarEventosRelatorios();
        registrarEventosEstudantes();
        registrarEventosGerais();

        await carregarOpcoesOcorrencias();
        limparFormularioOcorrencia();
        limparFormularioEstudante();
        renderDetalhesOcorrencia(null);
        renderRelatorioOcorrencias();
        ativarAbaCoordenacao(abaCoordAtiva);

        await Promise.all([
            carregarOcorrencias(),
            carregarEstudantes()
        ]);
    } catch (err) {
        setMensagemOcorrencias(err.message || "Erro ao carregar modulo de coordenacao.", true);
    }
}

init();
