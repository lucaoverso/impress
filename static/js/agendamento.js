const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": `Bearer ${token}`
};

const headersJson = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
};

const nomesMeses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
];

const nomesDiasSemana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

const OPCAO_TURNOS_FALLBACK = [
    { id: "INTEGRAL", nome: "Período integral", aulas: 8 },
    { id: "MATUTINO", nome: "Matutino", aulas: 5 },
    { id: "VESPERTINO", nome: "Vespertino", aulas: 5 },
    { id: "VESPERTINO_EM", nome: "Vespertino E.M.", aulas: 6 }
];
const MAX_AULAS_EXIBICAO = 5;

const TURNO_OFFSET_FAIXA = {
    MATUTINO: 0,
    INTEGRAL: 0,
    VESPERTINO: 5,
    VESPERTINO_EM: 5
};

let usuarioAtual = null;
let recursos = [];
let turnos = [];
let turmas = [];
let reservasMes = [];
let mesAtual = new Date();
let dataSelecionada = paraIso(new Date());
const PREFERENCIAS_ORDENACAO_STORAGE_KEY = "agendamento_sort_preferences_v1";
const CAMPOS_ORDENACAO_VALIDOS = {
    dia: new Set(["aula", "turno", "recurso"]),
    minhas: new Set(["data", "aula", "turno", "recurso"])
};
const configuracaoOrdenacao = {
    dia: { campo: "aula", direcao: "asc", agruparPorRecurso: false },
    minhas: { campo: "data", direcao: "asc", agruparPorRecurso: false }
};

function el(id) {
    return document.getElementById(id);
}

function encerrarSessao() {
    localStorage.removeItem("token");
    localStorage.removeItem("token_expira_em");
    window.location.href = "/login-page";
}

async function fetchComAuth(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        encerrarSessao();
        throw new Error("Sessão expirada.");
    }
    return res;
}

function paraIso(dataObj) {
    const ano = dataObj.getFullYear();
    const mes = String(dataObj.getMonth() + 1).padStart(2, "0");
    const dia = String(dataObj.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
}

function paraDataBr(dataIso) {
    const [ano, mes, dia] = dataIso.split("-");
    return `${dia}/${mes}/${ano}`;
}

function aulaLabel(aula) {
    return `${aula}ª aula`;
}

function aulaExibicaoPorFaixa(faixaGlobal) {
    const faixa = Number(faixaGlobal || 0);
    if (!Number.isFinite(faixa) || faixa <= 0) {
        return 0;
    }

    if (faixa <= MAX_AULAS_EXIBICAO) {
        return faixa;
    }

    return Math.min(faixa - MAX_AULAS_EXIBICAO, MAX_AULAS_EXIBICAO);
}

function faixaGlobalPorTurnoEAula(turnoId, aulaTurno) {
    const turno = String(turnoId || "").trim().toUpperCase();
    const aula = Number(aulaTurno || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;

    if (!Number.isFinite(aula) || aula <= 0) {
        return 0;
    }

    return aula + offset;
}

function aulaTurnoPorFaixa(turnoId, faixaGlobal) {
    const turno = String(turnoId || "").trim().toUpperCase();
    const faixa = Number(faixaGlobal || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;

    if (!Number.isFinite(faixa) || faixa <= 0) {
        return 0;
    }

    return faixa - offset;
}

function nomeTurno(turnoId) {
    const turno = turnos.find((item) => item.id === turnoId);
    return turno ? turno.nome : (turnoId || "Turno não informado");
}

function setMensagem(texto, tipo = "info") {
    const msg = el("msgAgendamento");
    msg.innerText = texto || "";
    msg.style.color = tipo === "erro" ? "#b42318" : "#0f766e";
}

function obterTurmaPorNome(nomeTurma) {
    const nome = String(nomeTurma || "").trim();
    return turmas.find((turma) => turma.nome === nome) || null;
}

function faixaGlobalReserva(reserva) {
    const faixaResposta = Number(reserva.faixa_global || 0);
    if (faixaResposta > 0) {
        return faixaResposta;
    }

    const aula = Number(reserva.aula || 0);
    const turno = String(reserva.turno || "").trim().toUpperCase();
    return faixaGlobalPorTurnoEAula(turno, aula);
}

function obterHojeIso() {
    return paraIso(new Date());
}

function dataReservaJaPassou(dataIso) {
    return String(dataIso || "") < obterHojeIso();
}

function reservaPodeSerCancelada(reserva) {
    if (!usuarioAtual || !reserva) {
        return false;
    }

    if (dataReservaJaPassou(reserva.data)) {
        return false;
    }

    return usuarioAtual.perfil === "admin" || reserva.usuario_id === usuarioAtual.id;
}

function salvarPreferenciasOrdenacao() {
    try {
        localStorage.setItem(
            PREFERENCIAS_ORDENACAO_STORAGE_KEY,
            JSON.stringify(configuracaoOrdenacao)
        );
    } catch (_err) {
        // Persistência local indisponível (quota, privacidade, etc).
    }
}

function carregarPreferenciasOrdenacao() {
    let bruto = "";
    try {
        bruto = localStorage.getItem(PREFERENCIAS_ORDENACAO_STORAGE_KEY) || "";
    } catch (_err) {
        return;
    }

    if (!bruto) {
        return;
    }

    try {
        const preferencias = JSON.parse(bruto);
        ["dia", "minhas"].forEach((alvo) => {
            const atual = configuracaoOrdenacao[alvo];
            const salvo = preferencias?.[alvo];
            if (!atual || !salvo || typeof salvo !== "object") {
                return;
            }

            const campoSalvo = String(salvo.campo || "").toLowerCase();
            if (CAMPOS_ORDENACAO_VALIDOS[alvo]?.has(campoSalvo)) {
                atual.campo = campoSalvo;
            }

            atual.direcao = salvo.direcao === "desc" ? "desc" : "asc";
            atual.agruparPorRecurso = Boolean(salvo.agruparPorRecurso);
        });
    } catch (_err) {
        // Se o payload estiver inválido, mantém padrão.
    }
}

function ordemTurno(turnoId) {
    const idTurno = String(turnoId || "").trim().toUpperCase();
    if (!idTurno) {
        return Number.MAX_SAFE_INTEGER;
    }

    const indice = turnos.findIndex((turno) => turno.id === idTurno);
    return indice >= 0 ? indice : Number.MAX_SAFE_INTEGER;
}

function compararTextoPtBr(a, b) {
    return String(a || "").localeCompare(String(b || ""), "pt-BR", { sensitivity: "base" });
}

function compararReservas(a, b, campoOrdenacao) {
    let comparacao = 0;
    const campo = String(campoOrdenacao || "aula").toLowerCase();

    if (campo === "data") {
        comparacao = String(a.data || "").localeCompare(String(b.data || ""));
    } else if (campo === "turno") {
        comparacao = ordemTurno(a.turno) - ordemTurno(b.turno);
    } else if (campo === "recurso") {
        comparacao = compararTextoPtBr(a.recurso_nome, b.recurso_nome);
    } else {
        comparacao = faixaGlobalReserva(a) - faixaGlobalReserva(b);
    }

    if (comparacao !== 0) {
        return comparacao;
    }

    comparacao = String(a.data || "").localeCompare(String(b.data || ""));
    if (comparacao !== 0) {
        return comparacao;
    }

    comparacao = ordemTurno(a.turno) - ordemTurno(b.turno);
    if (comparacao !== 0) {
        return comparacao;
    }

    comparacao = faixaGlobalReserva(a) - faixaGlobalReserva(b);
    if (comparacao !== 0) {
        return comparacao;
    }

    comparacao = compararTextoPtBr(a.recurso_nome, b.recurso_nome);
    if (comparacao !== 0) {
        return comparacao;
    }

    return Number(a.id || 0) - Number(b.id || 0);
}

function ordenarReservas(listaReservas, configOrdenacao) {
    const lista = Array.isArray(listaReservas) ? [...listaReservas] : [];
    const config = configOrdenacao || {};
    const campo = String(config.campo || "aula");
    const direcao = config.direcao === "desc" ? -1 : 1;

    lista.sort((a, b) => compararReservas(a, b, campo) * direcao);
    return lista;
}

function agruparReservasPorRecurso(listaReservasOrdenada) {
    const grupos = new Map();
    (listaReservasOrdenada || []).forEach((reserva) => {
        const nomeRecurso = String(reserva?.recurso_nome || "Recurso não informado");
        if (!grupos.has(nomeRecurso)) {
            grupos.set(nomeRecurso, []);
        }
        grupos.get(nomeRecurso).push(reserva);
    });
    return Array.from(grupos.entries());
}

function atualizarEstadoControlesOrdenacao(alvo) {
    const config = configuracaoOrdenacao[alvo];
    if (!config) {
        return;
    }

    const campoAtivo = String(config.campo || "");
    document
        .querySelectorAll(`.booking-sort-field[data-sort-target="${alvo}"]`)
        .forEach((btn) => {
            btn.classList.toggle("is-active", btn.dataset.sortField === campoAtivo);
        });

    const btnOrdem = document.querySelector(`.booking-sort-order[data-sort-target="${alvo}"]`);
    if (btnOrdem) {
        btnOrdem.innerText = config.direcao === "desc" ? "Último → 1º" : "1º → último";
    }

    const btnGrupo = document.querySelector(`.booking-sort-group[data-sort-target="${alvo}"]`);
    if (btnGrupo) {
        btnGrupo.classList.toggle("is-active", Boolean(config.agruparPorRecurso));
        btnGrupo.innerText = config.agruparPorRecurso ? "Agrupado por recurso" : "Agrupar por recurso";
    }
}

function atualizarListaPorOrdenacao(alvo) {
    if (alvo === "dia") {
        renderReservasDia();
        return;
    }
    if (alvo === "minhas") {
        renderMinhasReservas();
    }
}

function registrarControlesOrdenacao() {
    document.querySelectorAll(".booking-sort-field").forEach((btn) => {
        btn.addEventListener("click", () => {
            const alvo = btn.dataset.sortTarget;
            const campo = btn.dataset.sortField;
            if (!configuracaoOrdenacao[alvo] || !campo) {
                return;
            }
            configuracaoOrdenacao[alvo].campo = campo;
            salvarPreferenciasOrdenacao();
            atualizarEstadoControlesOrdenacao(alvo);
            atualizarListaPorOrdenacao(alvo);
        });
    });

    document.querySelectorAll(".booking-sort-order").forEach((btn) => {
        btn.addEventListener("click", () => {
            const alvo = btn.dataset.sortTarget;
            if (!configuracaoOrdenacao[alvo]) {
                return;
            }
            configuracaoOrdenacao[alvo].direcao =
                configuracaoOrdenacao[alvo].direcao === "asc" ? "desc" : "asc";
            salvarPreferenciasOrdenacao();
            atualizarEstadoControlesOrdenacao(alvo);
            atualizarListaPorOrdenacao(alvo);
        });
    });

    document.querySelectorAll(".booking-sort-group").forEach((btn) => {
        btn.addEventListener("click", () => {
            const alvo = btn.dataset.sortTarget;
            if (!configuracaoOrdenacao[alvo]) {
                return;
            }
            configuracaoOrdenacao[alvo].agruparPorRecurso = !configuracaoOrdenacao[alvo].agruparPorRecurso;
            salvarPreferenciasOrdenacao();
            atualizarEstadoControlesOrdenacao(alvo);
            atualizarListaPorOrdenacao(alvo);
        });
    });

    atualizarEstadoControlesOrdenacao("dia");
    atualizarEstadoControlesOrdenacao("minhas");
}

async function carregarUsuario() {
    const res = await fetchComAuth("/me", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar usuário.");
    }

    usuarioAtual = await res.json();
    el("agendamentoUsuario").innerText = `${usuarioAtual.nome} (${usuarioAtual.perfil})`;
}

async function carregarRecursos() {
    const res = await fetchComAuth("/agendamento/recursos", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar os recursos.");
    }

    recursos = await res.json();
    const select = el("recursoSelect");
    select.innerHTML = "";

    recursos.forEach((recurso) => {
        const option = document.createElement("option");
        option.value = recurso.id;
        option.innerText = `${recurso.nome} (${recurso.tipo})`;
        select.appendChild(option);
    });
}

function preencherSelectTurmas() {
    const select = el("turmaReserva");
    select.innerHTML = "";

    if (turmas.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Nenhuma turma ativa cadastrada";
        option.selected = true;
        select.appendChild(option);
        return;
    }

    turmas.forEach((turma) => {
        const option = document.createElement("option");
        option.value = turma.nome;
        option.innerText = `${turma.nome}`;
        select.appendChild(option);
    });
}

function atualizarSelectAulasPorTurma(nomeTurma, faixaSelecionada = null) {
    const select = el("aulaReserva");
    const turma = obterTurmaPorNome(nomeTurma);

    select.innerHTML = "";
    if (!turma || !turma.turno_valido || Number(turma.aulas) <= 0) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Configure o turno da turma no painel admin";
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        return;
    }

    const turnoTurma = String(turma.turno || "").trim().toUpperCase();
    const maxAulas = Number(turma.aulas);
    const faixasDisponiveis = [];
    for (let aula = 1; aula <= maxAulas; aula++) {
        const faixa = faixaGlobalPorTurnoEAula(turnoTurma, aula);
        if (faixa > 0) {
            faixasDisponiveis.push(faixa);
        }
    }

    const faixasMatutino = faixasDisponiveis.filter((faixa) => faixa <= MAX_AULAS_EXIBICAO);
    const faixasVespertino = faixasDisponiveis.filter((faixa) => faixa > MAX_AULAS_EXIBICAO);

    const adicionarSeparadorTurno = (rotulo) => {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = `----- ${rotulo} -----`;
        option.disabled = true;
        select.appendChild(option);
    };

    const adicionarOpcaoFaixa = (faixa) => {
        const option = document.createElement("option");
        option.value = String(faixa);
        option.innerText = `${aulaLabel(aulaExibicaoPorFaixa(faixa))}`;
        select.appendChild(option);
    };

    if (faixasMatutino.length > 0) {
        adicionarSeparadorTurno("Matutino");
        faixasMatutino.forEach(adicionarOpcaoFaixa);
    }

    if (faixasVespertino.length > 0) {
        adicionarSeparadorTurno("Vespertino");
        faixasVespertino.forEach(adicionarOpcaoFaixa);
    }

    select.disabled = false;
    const faixaEscolhida = Number(faixaSelecionada || 0);
    if (faixaEscolhida > 0 && faixasDisponiveis.includes(faixaEscolhida)) {
        select.value = String(faixaEscolhida);
    } else {
        select.value = faixasDisponiveis.length > 0 ? String(faixasDisponiveis[0]) : "";
    }
}

async function carregarOpcoesAgendamento() {
    try {
        const res = await fetchComAuth("/agendamento/opcoes", { headers });
        if (!res.ok) {
            throw new Error("Falha ao carregar opções de agendamento.");
        }

        const data = await res.json();
        turnos = Array.isArray(data.turnos) && data.turnos.length > 0
            ? data.turnos
            : OPCAO_TURNOS_FALLBACK;

        turmas = Array.isArray(data.turmas)
            ? data.turmas
                .map((turma) => {
                    const nome = String(turma?.nome || "").trim();
                    const turno = String(turma?.turno || "").trim().toUpperCase();
                    const turnoApi = turnos.find((item) => item.id === turno);
                    const aulasApi = Number(turma?.aulas || 0);
                    const aulasTurno = turnoApi ? Number(turnoApi.aulas) : 0;
                    const aulas = aulasApi > 0 ? aulasApi : aulasTurno;
                    const turnoValido = Boolean(turma?.turno_valido ?? turnoApi);

                    return {
                        nome,
                        turno,
                        turno_nome: String(turma?.turno_nome || (turnoApi ? turnoApi.nome : "Turno não configurado")),
                        aulas,
                        turno_valido: turnoValido,
                        quantidade_estudantes: Number(turma?.quantidade_estudantes || 0)
                    };
                })
                .filter((turma) => Boolean(turma.nome))
            : [];
    } catch (err) {
        turnos = OPCAO_TURNOS_FALLBACK;
        turmas = [];
    }

    preencherSelectTurmas();
    const turmaInicial = el("turmaReserva").value || (turmas[0] ? turmas[0].nome : "");
    atualizarSelectAulasPorTurma(turmaInicial);
}

function obterPeriodoMes() {
    const ano = mesAtual.getFullYear();
    const mes = mesAtual.getMonth();
    const inicio = new Date(ano, mes, 1);
    const fim = new Date(ano, mes + 1, 0);
    return {
        inicio: paraIso(inicio),
        fim: paraIso(fim)
    };
}

async function carregarReservasMes() {
    const periodo = obterPeriodoMes();
    const url = `/agendamento/reservas?data_inicio=${periodo.inicio}&data_fim=${periodo.fim}`;
    const res = await fetchComAuth(url, { headers });

    if (!res.ok) {
        throw new Error("Não foi possível carregar os agendamentos.");
    }

    reservasMes = await res.json();
}

function renderCalendario() {
    const ano = mesAtual.getFullYear();
    const mes = mesAtual.getMonth();
    el("mesAtual").innerText = `${nomesMeses[mes]} ${ano}`;

    const grid = el("calendarioGrid");
    grid.innerHTML = "";

    nomesDiasSemana.forEach((dia) => {
        const celula = document.createElement("div");
        celula.className = "calendar-weekday";
        celula.innerText = dia;
        grid.appendChild(celula);
    });

    const primeiroDiaSemana = new Date(ano, mes, 1).getDay();
    const totalDias = new Date(ano, mes + 1, 0).getDate();

    for (let i = 0; i < primeiroDiaSemana; i++) {
        const vazio = document.createElement("div");
        vazio.className = "calendar-empty";
        grid.appendChild(vazio);
    }

    const hojeIso = paraIso(new Date());

    for (let dia = 1; dia <= totalDias; dia++) {
        const dataIso = paraIso(new Date(ano, mes, dia));
        const reservasDia = reservasMes.filter((item) => item.data === dataIso);

        const btnDia = document.createElement("button");
        btnDia.type = "button";
        btnDia.className = "calendar-day";
        if (dataIso === dataSelecionada) btnDia.classList.add("is-selected");
        if (dataIso === hojeIso) btnDia.classList.add("is-today");

        const numero = document.createElement("span");
        numero.className = "calendar-number";
        numero.innerText = String(dia);

        const resumo = document.createElement("small");
        resumo.className = "calendar-count";
        resumo.innerText = reservasDia.length > 0
            ? `${reservasDia.length} reserva(s)`
            : "Livre";

        btnDia.appendChild(numero);
        btnDia.appendChild(resumo);
        btnDia.addEventListener("click", () => {
            dataSelecionada = dataIso;
            el("dataReserva").value = dataIso;
            renderCalendario();
            renderReservasDia();
        });

        grid.appendChild(btnDia);
    }
}

function criarItemReserva(
    reserva,
    {
        permitirCancelar = false,
        exibirProfessor = true,
        exibirData = false
    } = {}
) {
    const li = document.createElement("li");
    li.className = "booking-item";

    const faixa = faixaGlobalReserva(reserva);
    const aulaExibicao = aulaExibicaoPorFaixa(faixa);
    const titulo = document.createElement("p");
    titulo.innerText = `${reserva.recurso_nome} | ${nomeTurno(reserva.turno)} | ${aulaLabel(aulaExibicao || reserva.aula)} (faixa ${faixa || "?"})`;

    const professor = document.createElement("p");
    professor.className = "booking-professor";
    professor.innerText = `Professor(a): ${reserva.professor_nome || "Não informado"}`;

    const detalheTurma = document.createElement("p");
    detalheTurma.className = "booking-detail";
    const turmaTexto = reserva.turma || "Não informada";
    detalheTurma.innerText = `Turma: ${turmaTexto}`;

    li.appendChild(titulo);
    if (exibirProfessor) {
        li.appendChild(professor);
    }
    li.appendChild(detalheTurma);

    if (exibirData) {
        const detalheData = document.createElement("p");
        detalheData.className = "booking-detail";
        detalheData.innerText = `Data: ${paraDataBr(reserva.data)}`;
        li.appendChild(detalheData);
    }

    if (permitirCancelar) {
        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarReserva(reserva.id));
        li.appendChild(btnCancelar);
    }

    return li;
}

function renderListaReservasComConfig(
    listaEl,
    reservasBase,
    configOrdenacao,
    opcoesItem,
    textoVazio
) {
    listaEl.innerHTML = "";

    if (!Array.isArray(reservasBase) || reservasBase.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = textoVazio;
        listaEl.appendChild(vazio);
        return;
    }

    const reservasOrdenadas = ordenarReservas(reservasBase, configOrdenacao);
    const agruparPorRecurso = Boolean(configOrdenacao?.agruparPorRecurso);

    if (!agruparPorRecurso) {
        reservasOrdenadas.forEach((reserva) => {
            listaEl.appendChild(criarItemReserva(reserva, opcoesItem(reserva)));
        });
        return;
    }

    const grupos = agruparReservasPorRecurso(reservasOrdenadas);
    grupos.forEach(([nomeRecurso, reservasGrupo]) => {
        const tituloGrupo = document.createElement("li");
        tituloGrupo.className = "booking-group-heading";
        tituloGrupo.innerText = `${nomeRecurso} (${reservasGrupo.length})`;
        listaEl.appendChild(tituloGrupo);

        reservasGrupo.forEach((reserva) => {
            listaEl.appendChild(criarItemReserva(reserva, opcoesItem(reserva)));
        });
    });
}

function renderReservasDia() {
    el("tituloDia").innerText = `Reservas de ${paraDataBr(dataSelecionada)}`;

    const lista = el("listaReservasDia");
    const reservasDia = reservasMes
        .filter((item) => item.data === dataSelecionada);

    renderListaReservasComConfig(
        lista,
        reservasDia,
        configuracaoOrdenacao.dia,
        (reserva) => {
            return {
                permitirCancelar: reservaPodeSerCancelada(reserva),
                exibirProfessor: true,
                exibirData: false
            };
        },
        "Sem reservas nessa data."
    );
}

function renderMinhasReservas() {
    const lista = el("listaMinhasReservas");
    const hojeIso = obterHojeIso();
    const minhas = reservasMes
        .filter((item) => usuarioAtual && item.usuario_id === usuarioAtual.id && item.data >= hojeIso);

    renderListaReservasComConfig(
        lista,
        minhas,
        configuracaoOrdenacao.minhas,
        (reserva) => ({
            permitirCancelar: reservaPodeSerCancelada(reserva),
            exibirProfessor: false,
            exibirData: true
        }),
        "Você não tem reservas neste mês."
    );
}

async function atualizarTelaAgendamento() {
    await carregarReservasMes();
    renderCalendario();
    renderReservasDia();
    renderMinhasReservas();
}

async function cancelarReserva(idReserva) {
    const res = await fetchComAuth(`/agendamento/reservas/${idReserva}/cancelar`, {
        method: "POST",
        headers
    });

    const data = await res.json();
    if (!res.ok) {
        setMensagem(data.detail || "Não foi possível cancelar.", "erro");
        return;
    }

    setMensagem("Agendamento cancelado com sucesso.");
    await atualizarTelaAgendamento();
}

async function agendarRecurso() {
    if (turmas.length === 0) {
        setMensagem("Não há turmas ativas cadastradas. Procure a coordenação.", "erro");
        return;
    }

    const recursoId = Number(el("recursoSelect").value);
    const data = el("dataReserva").value;
    const turmaNome = el("turmaReserva").value;
    const faixaSelecionada = Number(el("aulaReserva").value);
    const observacao = el("observacaoReserva").value.trim();

    const turma = obterTurmaPorNome(turmaNome);
    if (!turma || !turma.turno_valido || Number(turma.aulas) <= 0) {
        setMensagem("A turma selecionada está sem turno válido. Atualize no painel admin.", "erro");
        return;
    }

    if (!recursoId || !data || !faixaSelecionada || !turmaNome) {
        setMensagem("Preencha recurso, data, turma e aula.", "erro");
        return;
    }

    const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixaSelecionada);
    if (!Number.isInteger(aulaTurno) || aulaTurno < 1 || aulaTurno > Number(turma.aulas)) {
        setMensagem("A faixa escolhida é inválida para o turno da turma.", "erro");
        return;
    }

    const res = await fetchComAuth("/agendamento/reservas", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            recurso_id: recursoId,
            data,
            aula: String(aulaTurno),
            turma: turmaNome,
            observacao
        })
    });

    const body = await res.json();
    if (!res.ok) {
        setMensagem(body.detail || "Não foi possível agendar.", "erro");
        return;
    }

    setMensagem("Recurso agendado com sucesso.");
    dataSelecionada = data;
    el("observacaoReserva").value = "";

    if (
        mesAtual.getFullYear() !== Number(data.slice(0, 4)) ||
        mesAtual.getMonth() !== Number(data.slice(5, 7)) - 1
    ) {
        mesAtual = new Date(Number(data.slice(0, 4)), Number(data.slice(5, 7)) - 1, 1);
    }

    await atualizarTelaAgendamento();
}

function registrarEventos() {
    const btnVoltarServicos = el("btnVoltarServicos");
    const btnIrAgendamento = el("btnIrAgendamento");
    const btnSair = el("btnSair");

    if (btnVoltarServicos) {
        btnVoltarServicos.addEventListener("click", () => {
            window.location.href = "/servicos";
        });
    }

    if (btnIrAgendamento) {
        btnIrAgendamento.addEventListener("click", () => {
            window.location.href = "/agendamento";
        });
    }

    if (btnSair) {
        btnSair.addEventListener("click", () => {
            encerrarSessao();
        });
    }

    el("btnMesAnterior").addEventListener("click", async () => {
        mesAtual = new Date(mesAtual.getFullYear(), mesAtual.getMonth() - 1, 1);
        await atualizarTelaAgendamento();
    });

    el("btnMesProximo").addEventListener("click", async () => {
        mesAtual = new Date(mesAtual.getFullYear(), mesAtual.getMonth() + 1, 1);
        await atualizarTelaAgendamento();
    });

    el("btnMesHoje").addEventListener("click", async () => {
        const hoje = new Date();
        mesAtual = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        dataSelecionada = paraIso(hoje);
        el("dataReserva").value = dataSelecionada;
        await atualizarTelaAgendamento();
    });

    el("dataReserva").addEventListener("change", () => {
        if (!el("dataReserva").value) return;
        dataSelecionada = el("dataReserva").value;
        renderCalendario();
        renderReservasDia();
    });

    el("turmaReserva").addEventListener("change", () => {
        atualizarSelectAulasPorTurma(el("turmaReserva").value);
    });

    registrarControlesOrdenacao();
    el("btnAgendar").addEventListener("click", agendarRecurso);
}

async function init() {
    try {
        dataSelecionada = paraIso(new Date());
        el("dataReserva").value = dataSelecionada;

        carregarPreferenciasOrdenacao();
        registrarEventos();
        await carregarUsuario();
        await carregarOpcoesAgendamento();
        await carregarRecursos();

        if (recursos.length === 0) {
            setMensagem("Nenhum recurso ativo cadastrado para agendamento.", "erro");
            return;
        }

        await atualizarTelaAgendamento();
    } catch (err) {
        setMensagem(err.message || "Erro ao carregar módulo de agendamento.", "erro");
    }
}

init();
