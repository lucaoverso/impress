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
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    return aula > 0 ? aula + offset : 0;
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
        option.innerText = `${turma.nome} (${turma.turno_nome})`;
        select.appendChild(option);
    });
}

function atualizarSelectAulasPorTurma(nomeTurma, aulaSelecionada = null) {
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

    const maxAulas = Number(turma.aulas);
    for (let aula = 1; aula <= maxAulas; aula++) {
        const option = document.createElement("option");
        option.value = String(aula);
        option.innerText = `${aula}ª aula`;
        select.appendChild(option);
    }

    select.disabled = false;
    if (aulaSelecionada && Number(aulaSelecionada) >= 1 && Number(aulaSelecionada) <= maxAulas) {
        select.value = String(aulaSelecionada);
    } else {
        select.value = "1";
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

function criarItemReserva(reserva, permitirCancelar) {
    const li = document.createElement("li");
    li.className = "booking-item";

    const faixa = faixaGlobalReserva(reserva);
    const titulo = document.createElement("p");
    titulo.innerText = `Faixa ${faixa} | ${nomeTurno(reserva.turno)} | ${aulaLabel(reserva.aula)} | ${reserva.recurso_nome}`;

    const detalhe = document.createElement("p");
    detalhe.className = "booking-detail";
    const turmaTexto = reserva.turma || "Não informada";
    detalhe.innerText = `Turma: ${turmaTexto} | Professor: ${reserva.professor_nome}${reserva.observacao ? ` | ${reserva.observacao}` : ""}`;

    li.appendChild(titulo);
    li.appendChild(detalhe);

    if (permitirCancelar) {
        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarReserva(reserva.id));
        li.appendChild(btnCancelar);
    }

    return li;
}

function renderReservasDia() {
    el("tituloDia").innerText = `Reservas de ${paraDataBr(dataSelecionada)}`;

    const lista = el("listaReservasDia");
    lista.innerHTML = "";

    const reservasDia = reservasMes
        .filter((item) => item.data === dataSelecionada)
        .sort((a, b) => faixaGlobalReserva(a) - faixaGlobalReserva(b));

    if (reservasDia.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Sem reservas nessa data.";
        lista.appendChild(vazio);
        return;
    }

    reservasDia.forEach((reserva) => {
        const permitirCancelar = usuarioAtual &&
            (usuarioAtual.perfil === "admin" || reserva.usuario_id === usuarioAtual.id);
        lista.appendChild(criarItemReserva(reserva, permitirCancelar));
    });
}

function renderMinhasReservas() {
    const lista = el("listaMinhasReservas");
    lista.innerHTML = "";

    const hojeIso = paraIso(new Date());
    const minhas = reservasMes
        .filter((item) => usuarioAtual && item.usuario_id === usuarioAtual.id && item.data >= hojeIso)
        .sort((a, b) => {
            if (a.data !== b.data) return a.data.localeCompare(b.data);
            return faixaGlobalReserva(a) - faixaGlobalReserva(b);
        });

    if (minhas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Você não tem reservas neste mês.";
        lista.appendChild(vazio);
        return;
    }

    minhas.forEach((reserva) => {
        const li = document.createElement("li");
        li.className = "booking-item";

        const faixa = faixaGlobalReserva(reserva);
        const titulo = document.createElement("p");
        titulo.innerText = `${paraDataBr(reserva.data)} - Faixa ${faixa} - ${nomeTurno(reserva.turno)} - ${aulaLabel(reserva.aula)} - ${reserva.recurso_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turma: ${reserva.turma || "Não informada"}`;

        li.appendChild(titulo);
        li.appendChild(detalhe);

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarReserva(reserva.id));
        li.appendChild(btnCancelar);

        lista.appendChild(li);
    });
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
    const aula = el("aulaReserva").value;
    const observacao = el("observacaoReserva").value.trim();

    const turma = obterTurmaPorNome(turmaNome);
    if (!turma || !turma.turno_valido || Number(turma.aulas) <= 0) {
        setMensagem("A turma selecionada está sem turno válido. Atualize no painel admin.", "erro");
        return;
    }

    if (!recursoId || !data || !aula || !turmaNome) {
        setMensagem("Preencha recurso, data, turma e aula.", "erro");
        return;
    }

    const res = await fetchComAuth("/agendamento/reservas", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            recurso_id: recursoId,
            data,
            aula,
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

    el("btnAgendar").addEventListener("click", agendarRecurso);
}

async function init() {
    try {
        dataSelecionada = paraIso(new Date());
        el("dataReserva").value = dataSelecionada;

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
