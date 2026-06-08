const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    encerrarSessao,
} = window.AppAuth;
const { fetchComAuth } = window.AppApi;
const { paraIso, paraDataBr } = window.AppFormat;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const headersJson = criarHeadersJsonAuth(token);

const nomesMeses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
];

const nomesDiasSemana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const nomesDiasSemanaAgenda = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

const OPCAO_TURNOS_FALLBACK = [
    { id: "INTEGRAL", nome: "Integral", aulas: 8 },
    { id: "MATUTINO", nome: "Matutino", aulas: 5 },
    { id: "VESPERTINO", nome: "Vespertino", aulas: 5 },
    { id: "VESPERTINO_EM", nome: "Vespertino", aulas: 6 }
];
const MAX_AULAS_EXIBICAO = 5;

const TURNO_OFFSET_FAIXA = {
    MATUTINO: 0,
    INTEGRAL: 0,
    VESPERTINO: 5,
    VESPERTINO_EM: 5
};
const TURNOS_GRADE_HORARIO = [
    { id: "MATUTINO", nome: "Matutino", aulas: 5, faixaInicial: 1 },
    { id: "VESPERTINO", nome: "Vespertino", aulas: 6, faixaInicial: 6 }
];

let usuarioAtual = null;
let recursos = [];
let turnos = [];
let turmas = [];
let reservasMes = [];
let professoresAgendamento = [];
let mesAtual = new Date();
let dataSelecionada = paraIso(new Date());
let semanaVisivelInicio = null;
const PREFERENCIAS_ORDENACAO_STORAGE_KEY = "agendamento_sort_preferences_v1";
const CAMPOS_ORDENACAO_VALIDOS = {
    dia: new Set(["aula", "turno", "recurso"]),
    minhas: new Set(["data", "aula", "turno", "recurso"])
};
const configuracaoOrdenacao = {
    dia: { campo: "aula", direcao: "asc", agruparPorRecurso: false },
    minhas: { campo: "data", direcao: "asc", agruparPorRecurso: false }
};
const configuracaoAgendaDia = {
    filtroRecursoId: 0,
    agruparPorRecurso: false
};
const DIAS_SEMANA_POR_WEEKDAY = [
    "DOMINGO",
    "SEGUNDA",
    "TERCA",
    "QUARTA",
    "QUINTA",
    "SEXTA",
    "SABADO"
];
const SCHEDULER_STEP_ENTER_CLASS = "is-step-enter";
const agendamentoWizard = {
    currentStep: 1,
    lastRenderedStep: null,
    submitting: false
};
const selecaoAulaAgendamento = {
    chave: "",
    data: "",
    turmaNome: "",
    turmaId: 0,
    disciplinaNome: "",
    professorId: 0,
    professorNome: "",
    professorEmail: "",
    turno: "",
    turnoNome: "",
    aulaNumero: 0,
    faixaGlobal: 0
};
const recursosSelecionadosAgendamento = new Set();
let aulasProfessorDia = [];

function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
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

    return faixa - MAX_AULAS_EXIBICAO;
}

function faixaGlobalPorTurnoEAula(turnoId, aulaTurno) {
    const turno = String(turnoId || "").trim().toUpperCase();
    const aula = Number(aulaTurno || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;

    if (!Number.isFinite(aula) || aula <= 0) {
        return 0;
    }

    let faixaGlobal = aula + offset;

    // No integral, a faixa 6 fica livre para não colidir com a 1ª do vespertino.
    if (turno === "INTEGRAL" && aula > 5) {
        faixaGlobal += 1;
    }

    return faixaGlobal;
}

function aulaTurnoPorFaixa(turnoId, faixaGlobal) {
    const turno = normalizarTurnoId(turnoId);
    const faixa = Number(faixaGlobal || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;

    if (!Number.isFinite(faixa) || faixa <= 0) {
        return 0;
    }

    if (turno === "INTEGRAL") {
        if (faixa >= 1 && faixa <= 5) {
            return faixa;
        }
        if (faixa >= 7) {
            return faixa - 1;
        }
        return 0;
    }

    return faixa - offset;
}

function aulaExibicaoPorTurnoEFaixa(turnoId, faixaGlobal) {
    const aulaTurno = aulaTurnoPorFaixa(turnoId, faixaGlobal);
    if (aulaTurno > 0) {
        return aulaTurno;
    }
    return aulaExibicaoPorFaixa(faixaGlobal);
}

function numeroAulaReserva(reserva) {
    const aulaDireta = Number(reserva?.aula || 0);
    if (Number.isInteger(aulaDireta) && aulaDireta > 0) {
        return aulaDireta;
    }

    const faixa = faixaGlobalReserva(reserva);
    return aulaExibicaoPorTurnoEFaixa(reserva?.turno, faixa);
}

function nomeTurno(turnoId) {
    const turnoNormalizado = normalizarTurnoId(turnoId);
    const turno = turnos.find((item) => normalizarTurnoId(item.id) === turnoNormalizado);
    if (turno) {
        return nomeTurnoExibicao(turno.id, turno.nome);
    }
    return nomeTurnoExibicao(turnoId);
}

function setMensagem(texto, tipo = "info") {
    const msg = el("msgAgendamento");
    if (!msg) {
        return;
    }
    msg.innerText = texto || "";
    msg.dataset.variant = texto ? tipo : "";
    msg.style.color = tipo === "erro" ? "#b42318" : "#0f766e";
}

function abrirPainelLateralAgendamento(drawerId) {
    const drawer = el(drawerId);
    if (!drawer) {
        return;
    }

    document.querySelectorAll(".scheduler-side-drawer.is-open").forEach((painelAberto) => {
        if (painelAberto.id !== drawerId) {
            painelAberto.classList.remove("is-open");
            painelAberto.setAttribute("aria-hidden", "true");
        }
    });

    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("scheduler-drawer-open");
}

function fecharPainelLateralAgendamento(drawerId = "") {
    const drawerIds = drawerId ? [drawerId] : Array.from(document.querySelectorAll(".scheduler-side-drawer")).map((item) => item.id);

    drawerIds.forEach((id) => {
        const drawer = el(id);
        if (!drawer) {
            return;
        }
        drawer.classList.remove("is-open");
        drawer.setAttribute("aria-hidden", "true");
    });

    if (!document.querySelector(".scheduler-side-drawer.is-open")) {
        document.body.classList.remove("scheduler-drawer-open");
    }
}

function obterProfessorAgendaAtivoId() {
    if (usuarioEhAdmin()) {
        return Number(el("professorAgendaFiltro")?.value || 0);
    }
    return Number(usuarioAtual?.id || 0);
}

function obterProfessorAgendaAtivo() {
    const professorId = obterProfessorAgendaAtivoId();
    if (professorId <= 0) {
        return null;
    }

    if (!usuarioEhAdmin() && usuarioAtual && Number(usuarioAtual.id) === professorId) {
        return {
            id: professorId,
            nome: String(usuarioAtual.nome || usuarioAtual.username || usuarioAtual.email || "Professor").trim(),
            email: String(usuarioAtual.email || "").trim()
        };
    }

    return professoresAgendamento.find((professor) => Number(professor.id) === professorId) || null;
}

function obterRecursosSelecionadosAgendamento() {
    const idsSelecionados = new Set(
        Array.from(recursosSelecionadosAgendamento).map((id) => Number(id || 0)).filter((id) => id > 0)
    );

    return recursos.filter((recurso) => idsSelecionados.has(Number(recurso.id)));
}

function formatarResumoRecursosSelecionados(listaRecursos = obterRecursosSelecionadosAgendamento()) {
    const nomes = (Array.isArray(listaRecursos) ? listaRecursos : [])
        .map((recurso) => `${recurso.nome} (${recurso.tipo})`);

    if (nomes.length === 0) {
        return "Aguardando seleção";
    }

    return nomes.join(", ");
}

function obterDiaSemanaApiPorData(dataIso) {
    const texto = String(dataIso || "").trim();
    if (!texto) {
        return "";
    }

    const [ano, mes, dia] = texto.split("-").map((parte) => Number(parte));
    if (!ano || !mes || !dia) {
        return "";
    }

    const data = new Date(ano, mes - 1, dia, 12, 0, 0);
    return DIAS_SEMANA_POR_WEEKDAY[data.getDay()] || "";
}

function criarDataLocalPorIso(dataIso) {
    const texto = String(dataIso || "").trim();
    if (!texto) {
        return null;
    }

    const [ano, mes, dia] = texto.split("-").map((parte) => Number(parte));
    if (!ano || !mes || !dia) {
        return null;
    }

    return new Date(ano, mes - 1, dia, 12, 0, 0);
}

function clonarDataLocal(dataRef) {
    const data = dataRef instanceof Date ? dataRef : new Date();
    return new Date(data.getFullYear(), data.getMonth(), data.getDate(), 12, 0, 0);
}

function somarDiasDataLocal(dataRef, dias) {
    const data = clonarDataLocal(dataRef);
    data.setDate(data.getDate() + Number(dias || 0));
    return data;
}

function deslocarMesDataLocal(dataRef, meses) {
    const base = clonarDataLocal(dataRef);
    const anoDestino = base.getFullYear();
    const mesDestino = base.getMonth() + Number(meses || 0);
    const ultimoDiaMesDestino = new Date(anoDestino, mesDestino + 1, 0, 12, 0, 0).getDate();
    const dia = Math.min(base.getDate(), ultimoDiaMesDestino);
    return new Date(anoDestino, mesDestino, dia, 12, 0, 0);
}

function obterInicioSemanaDataLocal(dataRef) {
    const data = clonarDataLocal(dataRef);
    const weekday = data.getDay();
    const deslocamento = weekday === 0 ? -6 : 1 - weekday;
    data.setDate(data.getDate() + deslocamento);
    return clonarDataLocal(data);
}

function sincronizarSemanaVisivelComDataSelecionada() {
    const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
    semanaVisivelInicio = obterInicioSemanaDataLocal(dataBase);
}

function formatarTituloSemana(dataInicio) {
    const inicio = clonarDataLocal(dataInicio);
    const fim = somarDiasDataLocal(inicio, 6);
    const mesmoMes = inicio.getMonth() === fim.getMonth() && inicio.getFullYear() === fim.getFullYear();
    const opcoesCurta = { day: "2-digit", month: "short" };

    if (mesmoMes) {
        const mesTexto = inicio.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
        return `${inicio.getDate()} a ${fim.getDate()} de ${mesTexto}`;
    }

    return `${inicio.toLocaleDateString("pt-BR", opcoesCurta)} a ${fim.toLocaleDateString("pt-BR", { ...opcoesCurta, year: "numeric" })}`;
}

function formatarDiaSemanaAgenda(dataRef) {
    const weekday = dataRef.getDay();
    const indice = weekday === 0 ? 6 : weekday - 1;
    return nomesDiasSemanaAgenda[indice] || "";
}

function chaveAulaAgendamento(item = {}) {
    return [
        String(item.data || dataSelecionada || ""),
        Number(item.professorId || item.professor_id || 0),
        String(item.turmaNome || item.turma_nome || "").trim().toLowerCase(),
        Number(item.faixaGlobal || item.faixa_global || 0),
        Number(item.aulaNumero || item.aula_numero || 0)
    ].join("|");
}

function obterResumoProfessorAulaSelecionada() {
    if (!selecaoAulaAgendamento.professorNome) {
        return "Professor aguardando definição.";
    }

    if (!selecaoAulaAgendamento.professorEmail) {
        return selecaoAulaAgendamento.professorNome;
    }

    return `${selecaoAulaAgendamento.professorNome} (${selecaoAulaAgendamento.professorEmail})`;
}

function obterTituloAulaSelecionada() {
    if (!selecaoAulaAgendamento.chave) {
        return "Nenhuma aula selecionada";
    }
    const disciplina = String(selecaoAulaAgendamento.disciplinaNome || "Aula planejada").trim();
    const aula = aulaLabel(selecaoAulaAgendamento.aulaNumero || 0);
    return `${disciplina} • ${aula}`;
}

function obterResumoAulaSelecionada() {
    if (!selecaoAulaAgendamento.chave) {
        return "Selecione uma aula disponível na coluna da esquerda para liberar o formulário.";
    }

    const partes = [
        paraDataBr(selecaoAulaAgendamento.data || dataSelecionada),
        selecaoAulaAgendamento.turmaNome,
        selecaoAulaAgendamento.turnoNome || nomeTurnoExibicao(selecaoAulaAgendamento.turno)
    ].filter(Boolean);

    if (selecaoAulaAgendamento.professorNome) {
        partes.push(selecaoAulaAgendamento.professorNome);
    }

    return partes.join(" | ");
}

function atualizarResumoAulaSelecionada() {
    const titulo = obterTituloAulaSelecionada();
    const resumo = obterResumoAulaSelecionada();

    if (el("tituloAulaSelecionada")) {
        el("tituloAulaSelecionada").innerText = titulo;
    }
    if (el("resumoAulaSelecionada")) {
        el("resumoAulaSelecionada").innerText = resumo;
    }
    if (el("tituloAulaSelecionadaDetalhes")) {
        el("tituloAulaSelecionadaDetalhes").innerText = titulo;
    }
    if (el("resumoAulaSelecionadaDetalhes")) {
        el("resumoAulaSelecionadaDetalhes").innerText = resumo;
    }
}

function obterReservasDaAulaSelecionada(item = selecaoAulaAgendamento) {
    const data = String(item?.data || dataSelecionada || "").trim();
    const faixaGlobal = Number(item?.faixaGlobal || item?.faixa_global || 0);

    if (!data || !faixaGlobal) {
        return [];
    }

    return (reservasMes || []).filter((reserva) => {
        return reserva.data === data
            && faixaGlobalReserva(reserva) === faixaGlobal;
    });
}

function obterRecursosDisponiveisParaSelecao(item = selecaoAulaAgendamento) {
    const recursosReservados = new Set(
        obterReservasDaAulaSelecionada(item).map((reserva) => Number(reserva.recurso_id || 0))
    );
    return recursos.filter((recurso) => !recursosReservados.has(Number(recurso.id)));
}

function alternarSelecaoRecursoAgendamento(recursoId) {
    const id = Number(recursoId || 0);
    if (!id) {
        return;
    }

    if (recursosSelecionadosAgendamento.has(id)) {
        recursosSelecionadosAgendamento.delete(id);
    } else {
        recursosSelecionadosAgendamento.add(id);
    }

    atualizarOpcoesRecursoPorSelecao();
    sincronizarWizardAgendamento();
}

function atualizarOpcoesRecursoPorSelecao() {
    const container = el("recursoButtons");
    const resumo = el("resumoDisponibilidadeRecursos");
    if (!container) {
        return;
    }

    const recursosDisponiveis = selecaoAulaAgendamento.chave
        ? obterRecursosDisponiveisParaSelecao()
        : [];
    const idsDisponiveis = new Set(recursosDisponiveis.map((recurso) => Number(recurso.id)));

    Array.from(recursosSelecionadosAgendamento).forEach((recursoId) => {
        if (!idsDisponiveis.has(Number(recursoId))) {
            recursosSelecionadosAgendamento.delete(Number(recursoId));
        }
    });

    container.innerHTML = "";

    if (!selecaoAulaAgendamento.chave) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-resource-empty";
        vazio.innerText = "Selecione uma aula primeiro.";
        container.appendChild(vazio);
    } else if (recursosDisponiveis.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-resource-empty";
        vazio.innerText = "Nenhum recurso disponível neste horário.";
        container.appendChild(vazio);
    } else {
        recursosDisponiveis.forEach((recurso) => {
            const selecionado = recursosSelecionadosAgendamento.has(Number(recurso.id));

            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "scheduler-resource-button";
            botao.setAttribute("aria-pressed", selecionado ? "true" : "false");
            if (selecionado) {
                botao.classList.add("is-selected");
            }

            const nome = document.createElement("strong");
            nome.innerText = recurso.nome;
            const tipo = document.createElement("span");
            tipo.innerText = recurso.tipo || "Recurso";

            botao.appendChild(nome);
            botao.appendChild(tipo);
            botao.addEventListener("click", () => alternarSelecaoRecursoAgendamento(recurso.id));
            container.appendChild(botao);
        });
    }

    if (resumo) {
        if (!selecaoAulaAgendamento.chave) {
            resumo.innerText = "Escolha uma aula para ver quais recursos ainda estão disponíveis.";
        } else if (recursosDisponiveis.length === 0) {
            resumo.innerText = "Todos os recursos já estão ocupados neste horário ou não há recurso ativo cadastrado.";
        } else if (recursosSelecionadosAgendamento.size === 0) {
            resumo.innerText = `${recursosDisponiveis.length} recurso(s) livre(s) neste horário. Você pode selecionar mais de um.`;
        } else {
            resumo.innerText = `${recursosSelecionadosAgendamento.size} recurso(s) selecionado(s) para o agrupamento.`;
        }
    }
}

function limparCamposFluxoAgendamento() {
    if (el("temaAulaReserva")) {
        el("temaAulaReserva").value = "";
    }
    if (el("observacaoReserva")) {
        el("observacaoReserva").value = "";
    }
}

function limparSelecaoAulaAgendamento({ manterFormulario = false } = {}) {
    recursosSelecionadosAgendamento.clear();
    Object.assign(selecaoAulaAgendamento, {
        chave: "",
        data: "",
        turmaNome: "",
        turmaId: 0,
        disciplinaNome: "",
        professorId: 0,
        professorNome: "",
        professorEmail: "",
        turno: "",
        turnoNome: "",
        aulaNumero: 0,
        faixaGlobal: 0
    });
    agendamentoWizard.currentStep = 1;
    if (!manterFormulario) {
        limparCamposFluxoAgendamento();
    }
    atualizarResumoAulaSelecionada();
    atualizarOpcoesRecursoPorSelecao();
}

function selecionarAulaParaAgendamento(item) {
    if (!item) {
        limparSelecaoAulaAgendamento();
        sincronizarWizardAgendamento();
        renderAgendaDiaAulas();
        return;
    }

    Object.assign(selecaoAulaAgendamento, {
        chave: chaveAulaAgendamento(item),
        data: String(item.data || dataSelecionada),
        turmaNome: String(item.turma_nome || item.turmaNome || "").trim(),
        turmaId: Number(item.turma_id || item.turmaId || 0),
        disciplinaNome: String(item.disciplina_nome || item.disciplinaNome || "").trim(),
        professorId: Number(item.professor_id || item.professorId || 0),
        professorNome: String(item.professor_nome || item.professorNome || "").trim(),
        professorEmail: String(item.professor_email || item.professorEmail || "").trim(),
        turno: String(item.turno || "").trim().toUpperCase(),
        turnoNome: String(item.turno_nome || item.turnoNome || "").trim(),
        aulaNumero: Number(item.aula_numero || item.aulaNumero || 0),
        faixaGlobal: Number(item.faixa_global || item.faixaGlobal || 0)
    });

    recursosSelecionadosAgendamento.clear();
    limparCamposFluxoAgendamento();
    agendamentoWizard.currentStep = 2;
    atualizarResumoAulaSelecionada();
    atualizarOpcoesRecursoPorSelecao();
    sincronizarWizardAgendamento({ scroll: true });
    renderAgendaDiaAulas();
}

function animarEtapaAgendamento(card) {
    if (!card) {
        return;
    }

    card.classList.remove(SCHEDULER_STEP_ENTER_CLASS);
    void card.offsetWidth;
    card.classList.add(SCHEDULER_STEP_ENTER_CLASS);
    card.addEventListener("animationend", () => {
        card.classList.remove(SCHEDULER_STEP_ENTER_CLASS);
    }, { once: true });
}

function rolarParaInicioAgendamento() {
    const anchor = el("schedulerWizardStartAnchor");
    if (!anchor) {
        return;
    }

    window.requestAnimationFrame(() => {
        anchor.scrollIntoView({
            behavior: "smooth",
            block: "start",
            inline: "nearest"
        });
    });
}

function obterEstadoWizardAgendamento() {
    const recursosSelecionados = obterRecursosSelecionadosAgendamento();
    const data = selecaoAulaAgendamento.data || dataSelecionada;
    const turmaNome = selecaoAulaAgendamento.turmaNome;
    const turma = obterTurmaPorNome(turmaNome);
    const temaAula = String(el("temaAulaReserva")?.value || "").trim();
    const observacao = String(el("observacaoReserva")?.value || "").trim();
    const possuiSelecao = Boolean(selecaoAulaAgendamento.chave);

    const turmaValida = Boolean(possuiSelecao && turma && turma.turno_valido && Number(turma.aulas) > 0);
    const aulaTurno = turmaValida && Number(selecaoAulaAgendamento.faixaGlobal || 0) > 0
        ? aulaTurnoPorFaixa(turma.turno, selecaoAulaAgendamento.faixaGlobal)
        : 0;
    const aulaValida = Number.isInteger(aulaTurno) && aulaTurno > 0;

    const etapaSelecaoConcluida = Boolean(possuiSelecao && data && turmaNome && turmaValida);
    const etapaRecursoLiberada = Boolean(etapaSelecaoConcluida && recursosSelecionados.length > 0 && aulaValida);
    const etapaDetalhesLiberada = Boolean(etapaRecursoLiberada && temaAula);
    const maxEtapa = !etapaSelecaoConcluida ? 1 : etapaDetalhesLiberada ? 4 : etapaRecursoLiberada ? 3 : 2;
    const etapaAtual = etapaSelecaoConcluida
        ? Math.min(Math.max(agendamentoWizard.currentStep || 2, 2), maxEtapa)
        : 1;

    return {
        hasSelection: possuiSelecao,
        selectionReady: etapaSelecaoConcluida,
        currentStep: etapaAtual,
        maxStep: maxEtapa,
        resourceStepReady: etapaRecursoLiberada,
        detailsStepReady: etapaDetalhesLiberada,
        canSubmit: etapaDetalhesLiberada && !agendamentoWizard.submitting,
        summary: {
            recurso: formatarResumoRecursosSelecionados(recursosSelecionados),
            data: data ? paraDataBr(data) : "Aguardando data",
            turma: turma
                ? `${turma.nome} | ${nomeTurnoExibicao(turma.turno, turma.turno_nome)}`
                : "Aguardando turma",
            disciplina: selecaoAulaAgendamento.disciplinaNome || "Aguardando disciplina",
            professor: obterResumoProfessorAulaSelecionada(),
            aula: aulaValida
                ? `${aulaLabel(aulaTurno)} | ${nomeTurnoExibicao(turma.turno, turma.turno_nome)}`
                : "Aguardando aula",
            tema: temaAula || "Aguardando tema",
            observacao: observacao || "Sem observação adicional."
        }
    };
}

function atualizarResumoWizardAgendamento(state) {
    const resumo = state?.summary || {};
    atualizarResumoAulaSelecionada();

    if (el("resumoAgendamentoRecurso")) {
        el("resumoAgendamentoRecurso").innerText = resumo.recurso || "Aguardando seleção";
    }
    if (el("resumoAgendamentoData")) {
        el("resumoAgendamentoData").innerText = resumo.data || "Aguardando data";
    }
    if (el("resumoAgendamentoTurma")) {
        el("resumoAgendamentoTurma").innerText = resumo.turma || "Aguardando turma";
    }
    if (el("resumoAgendamentoDisciplina")) {
        el("resumoAgendamentoDisciplina").innerText = resumo.disciplina || "Aguardando disciplina";
    }
    if (el("resumoAgendamentoProfessor")) {
        el("resumoAgendamentoProfessor").innerText = resumo.professor || "Aguardando professor";
    }
    if (el("resumoAgendamentoAula")) {
        el("resumoAgendamentoAula").innerText = resumo.aula || "Aguardando aula";
    }
    if (el("resumoAgendamentoTema")) {
        el("resumoAgendamentoTema").innerText = resumo.tema || "Aguardando tema";
    }
    if (el("resumoAgendamentoObservacao")) {
        el("resumoAgendamentoObservacao").innerText = resumo.observacao || "Sem observação adicional.";
    }
}

function atualizarStepperAgendamento(state) {
    [
        ["stepperAgendamentoAula", 1],
        ["stepperAgendamentoContexto", 2],
        ["stepperAgendamentoDetalhes", 3],
        ["stepperAgendamentoResumo", 4]
    ].forEach(([id, step]) => {
        const item = el(id);
        if (!item) {
            return;
        }

        const isCurrent = step === state.currentStep;
        const isReady = step < state.currentStep;
        const isLocked = step > state.maxStep;

        item.classList.toggle("is-current", isCurrent);
        item.classList.toggle("is-ready", isReady);
        item.classList.toggle("is-locked", isLocked);
    });
}

function renderEtapaAtualAgendamento(state) {
    const flow = el("schedulerWizardFlow");
    if (flow) {
        flow.hidden = !state?.hasSelection;
    }

    if (!state?.hasSelection) {
        document.documentElement.dataset.schedulerCurrentStep = "1";
        agendamentoWizard.lastRenderedStep = null;
        return;
    }

    const currentStep = Number(state.currentStep || 2);
    const cards = {
        2: el("etapaAgendamentoContexto"),
        3: el("etapaAgendamentoDetalhes"),
        4: el("etapaAgendamentoResumo")
    };

    Object.entries(cards).forEach(([step, card]) => {
        if (!card) {
            return;
        }

        const ativa = Number(step) === currentStep;
        card.hidden = !ativa;
        card.classList.toggle("print-step-card-active", ativa);
    });

    const cardAtivo = cards[currentStep];
    if (cardAtivo && agendamentoWizard.lastRenderedStep !== null && agendamentoWizard.lastRenderedStep !== currentStep) {
        animarEtapaAgendamento(cardAtivo);
    }

    document.documentElement.dataset.schedulerCurrentStep = String(currentStep);
    agendamentoWizard.lastRenderedStep = currentStep;
}

function atualizarAcoesWizardAgendamento(state) {
    const btnContinuarContexto = el("btnContinuarAgendamentoContexto");
    const btnContinuarDetalhes = el("btnContinuarAgendamentoDetalhes");
    const btnAgendar = el("btnAgendar");
    const btnTrocar = el("btnTrocarAulaSelecionada");
    const quantidadeRecursos = recursosSelecionadosAgendamento.size;

    if (btnContinuarContexto) {
        btnContinuarContexto.disabled = !state.resourceStepReady;
    }
    if (btnContinuarDetalhes) {
        btnContinuarDetalhes.disabled = !state.detailsStepReady;
    }
    if (btnAgendar) {
        btnAgendar.disabled = !state.canSubmit;
        if (agendamentoWizard.submitting) {
            btnAgendar.innerText = quantidadeRecursos > 1 ? "Confirmando reservas..." : "Confirmando reserva...";
        } else if (quantidadeRecursos > 1) {
            btnAgendar.innerText = `Confirmar reserva de ${quantidadeRecursos} recursos`;
        } else {
            btnAgendar.innerText = "Confirmar reserva";
        }
    }
    if (btnTrocar) {
        btnTrocar.disabled = !state.hasSelection;
    }
}

function sincronizarWizardAgendamento({ scroll = false } = {}) {
    const state = obterEstadoWizardAgendamento();
    if (!state) {
        return null;
    }

    agendamentoWizard.currentStep = state.currentStep;
    atualizarResumoWizardAgendamento(state);
    atualizarStepperAgendamento(state);
    renderEtapaAtualAgendamento(state);
    atualizarAcoesWizardAgendamento(state);

    if (scroll && state.hasSelection) {
        rolarParaInicioAgendamento();
    }

    return state;
}

function irParaEtapaAgendamento(step) {
    const etapaAtual = agendamentoWizard.currentStep || 1;
    agendamentoWizard.currentStep = step;
    sincronizarWizardAgendamento({ scroll: step > etapaAtual });
}

function definirEstadoEnvioAgendamento(ativo) {
    agendamentoWizard.submitting = Boolean(ativo);
    sincronizarWizardAgendamento();
}

function obterTurmaPorNome(nomeTurma) {
    const nome = String(nomeTurma || "").trim();
    return turmas.find((turma) => turma.nome === nome) || null;
}

function usuarioEhAdmin() {
    if (!usuarioAtual) {
        return false;
    }

    if (Boolean(usuarioAtual.eh_admin)) {
        return true;
    }

    const cargo = String(usuarioAtual.cargo || "").trim().toUpperCase();
    if (cargo === "ADMIN") {
        return true;
    }

    return String(usuarioAtual.perfil || "").trim().toLowerCase() === "admin";
}

function atualizarVisibilidadeProfessorReserva() {
    const grupo = el("grupoProfessorAgendaFiltro");
    if (!grupo) {
        return;
    }
    grupo.hidden = !usuarioEhAdmin();
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

    return usuarioEhAdmin() || reserva.usuario_id === usuarioAtual.id;
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
    const idTurno = normalizarTurnoId(turnoId);
    if (!idTurno) {
        return Number.MAX_SAFE_INTEGER;
    }

    const indice = turnos.findIndex((turno) => normalizarTurnoId(turno.id) === idTurno);
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

function renderBotoesFiltroAgendaDia() {
    const container = el("agendaDiaFiltroRecursos");
    if (!container) {
        return;
    }

    const recursoSelecionadoExiste = recursos.some(
        (recurso) => Number(recurso.id) === Number(configuracaoAgendaDia.filtroRecursoId)
    );
    if (!recursoSelecionadoExiste) {
        configuracaoAgendaDia.filtroRecursoId = 0;
    }

    const criarBotaoFiltro = (label, recursoId, ativo = false) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.innerText = label;
        btn.title = label;
        btn.classList.toggle("is-active", ativo);
        btn.addEventListener("click", () => {
            configuracaoAgendaDia.filtroRecursoId = Number(recursoId || 0);
            renderBotoesFiltroAgendaDia();
            renderAgendaDiaAulas();
        });
        return btn;
    };

    container.innerHTML = "";
    container.appendChild(
        criarBotaoFiltro(
            "Todos recursos",
            0,
            Number(configuracaoAgendaDia.filtroRecursoId) === 0
        )
    );

    const recursosOrdenados = [...recursos].sort((a, b) => compararTextoPtBr(a.nome, b.nome));
    recursosOrdenados.forEach((recurso) => {
        container.appendChild(
            criarBotaoFiltro(
                String(recurso.nome || "Recurso"),
                Number(recurso.id),
                Number(configuracaoAgendaDia.filtroRecursoId) === Number(recurso.id)
            )
        );
    });
}

function atualizarEstadoBotaoAgruparAgendaDia() {
    const btn = el("btnAgendaDiaAgruparRecurso");
    if (!btn) {
        return;
    }

    btn.classList.toggle("is-active", Boolean(configuracaoAgendaDia.agruparPorRecurso));
    btn.innerText = configuracaoAgendaDia.agruparPorRecurso
        ? "Agrupado por recurso"
        : "Agrupar por recurso";
}

function registrarControlesAgendaDia() {
    const btnAgrupar = el("btnAgendaDiaAgruparRecurso");
    if (btnAgrupar) {
        btnAgrupar.addEventListener("click", () => {
            configuracaoAgendaDia.agruparPorRecurso = !configuracaoAgendaDia.agruparPorRecurso;
            atualizarEstadoBotaoAgruparAgendaDia();
            renderAgendaDiaAulas();
        });
    }

    atualizarEstadoBotaoAgruparAgendaDia();
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
    atualizarVisibilidadeProfessorReserva();
    sincronizarWizardAgendamento();
}

async function carregarProfessoresAgendamentoAdmin() {
    const grupo = el("grupoProfessorAgendaFiltro");
    const select = el("professorAgendaFiltro");

    if (!grupo || !select) {
        return;
    }

    if (!usuarioEhAdmin()) {
        grupo.hidden = true;
        professoresAgendamento = [];
        select.innerHTML = "";
        sincronizarWizardAgendamento();
        return;
    }

    grupo.hidden = false;

    const res = await fetchComAuth("/agendamento/professores", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar os professores para agendamento.");
    }

    professoresAgendamento = await res.json();
    select.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.innerText = Array.isArray(professoresAgendamento) && professoresAgendamento.length > 0
        ? "Selecione um professor"
        : "Nenhum professor disponível";
    placeholder.selected = true;
    select.appendChild(placeholder);

    (Array.isArray(professoresAgendamento) ? professoresAgendamento : []).forEach((professor) => {
        const option = document.createElement("option");
        option.value = String(professor.id);
        option.innerText = `${professor.nome} (${professor.email})`;
        select.appendChild(option);
    });
    select.disabled = !Array.isArray(professoresAgendamento) || professoresAgendamento.length === 0;
    sincronizarWizardAgendamento();
}

async function carregarRecursos() {
    const res = await fetchComAuth("/agendamento/recursos", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar os recursos.");
    }

    recursos = await res.json();
    atualizarOpcoesRecursoPorSelecao();
    sincronizarWizardAgendamento();
}

function preencherSelectTurmas() {
    // A turma agora vem da aula escolhida na coluna esquerda.
    sincronizarWizardAgendamento();
}

function atualizarSelectAulasPorTurma(nomeTurma, faixaSelecionada = null) {
    void nomeTurma;
    void faixaSelecionada;
    // A aula agora vem do clique na lista de aulas do dia.
    sincronizarWizardAgendamento();
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

function preencherSelecaoAulaAgendamento(item) {
    if (!item) {
        return;
    }

    Object.assign(selecaoAulaAgendamento, {
        chave: chaveAulaAgendamento(item),
        data: String(item.data || dataSelecionada),
        turmaNome: String(item.turma_nome || item.turmaNome || "").trim(),
        turmaId: Number(item.turma_id || item.turmaId || 0),
        disciplinaNome: String(item.disciplina_nome || item.disciplinaNome || "").trim(),
        professorId: Number(item.professor_id || item.professorId || 0),
        professorNome: String(item.professor_nome || item.professorNome || "").trim(),
        professorEmail: String(item.professor_email || item.professorEmail || "").trim(),
        turno: String(item.turno || "").trim().toUpperCase(),
        turnoNome: String(item.turno_nome || item.turnoNome || "").trim(),
        aulaNumero: Number(item.aula_numero || item.aulaNumero || 0),
        faixaGlobal: Number(item.faixa_global || item.faixaGlobal || 0)
    });
}

function sincronizarSelecaoAulaComAgendaAtual() {
    if (!selecaoAulaAgendamento.chave) {
        atualizarResumoAulaSelecionada();
        atualizarOpcoesRecursoPorSelecao();
        return;
    }

    const aulaAtual = aulasProfessorDia.find(
        (item) => chaveAulaAgendamento(item) === selecaoAulaAgendamento.chave
    );

    if (!aulaAtual) {
        limparSelecaoAulaAgendamento();
        return;
    }

    preencherSelecaoAulaAgendamento(aulaAtual);
    atualizarResumoAulaSelecionada();
    atualizarOpcoesRecursoPorSelecao();
}

function renderEstadoAulasDia(texto) {
    const tabela = el("tabelaAgendaDia");
    if (!tabela) {
        return;
    }

    tabela.innerHTML = "";

    const tbody = document.createElement("tbody");
    const linha = document.createElement("tr");
    const celula = document.createElement("td");
    celula.colSpan = 2;
    celula.className = "weekly-table-empty";
    celula.innerText = texto;

    linha.appendChild(celula);
    tbody.appendChild(linha);
    tabela.appendChild(tbody);
}

async function carregarAulasProfessorDia() {
    const professor = obterProfessorAgendaAtivo();
    const diaSemana = obterDiaSemanaApiPorData(dataSelecionada);

    aulasProfessorDia = [];

    if (!professor) {
        limparSelecaoAulaAgendamento({ manterFormulario: true });
        return;
    }

    if (!["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"].includes(diaSemana)) {
        limparSelecaoAulaAgendamento({ manterFormulario: true });
        return;
    }

    const anoLetivo = Number(String(dataSelecionada || "").slice(0, 4));
    const params = new URLSearchParams({
        ano_letivo: String(anoLetivo),
        dia_semana: diaSemana,
        professor_id: String(professor.id)
    });

    const res = await fetchComAuth(`/horario-escolar/registros?${params.toString()}`, { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar as aulas do professor para esta data.");
    }

    const body = await res.json();
    aulasProfessorDia = Array.isArray(body.itens)
        ? body.itens
            .filter((item) => Number(item.professor_id || 0) === Number(professor.id))
            .map((item) => ({
                ...item,
                data: dataSelecionada
            }))
            .sort((a, b) => {
                const faixa = Number(a.faixa_global || 0) - Number(b.faixa_global || 0);
                if (faixa !== 0) {
                    return faixa;
                }
                return compararTextoPtBr(a.turma_nome, b.turma_nome);
            })
        : [];

    sincronizarSelecaoAulaComAgendaAtual();
}

function nomeTurnoExibicao(turnoId, nomeTurnoBase = "") {
    const turno = normalizarTurnoId(turnoId);
    const nomeBase = String(nomeTurnoBase || "").trim();

    if (turno === "VESPERTINO_EM") {
        return nomeBase ? `${nomeBase} E.M.` : "Vespertino E.M.";
    }

    if (nomeBase) {
        return nomeBase;
    }

    if (turno === "MATUTINO") {
        return "Matutino";
    }
    if (turno === "VESPERTINO") {
        return "Vespertino";
    }
    if (turno === "INTEGRAL") {
        return "Integral";
    }

    return turno || "Turno não informado";
}

function obterLinhasAulasGradeSemanal() {
    const linhas = [];

    TURNOS_GRADE_HORARIO.forEach((turno) => {
        for (let aula = 1; aula <= turno.aulas; aula++) {
            linhas.push({
                turnoId: turno.id,
                turnoNome: turno.nome,
                aula
            });
        }
    });

    return linhas;
}

function chaveCelulaAgendaDia(turnoId, aula) {
    return `${normalizarTurnoId(turnoId)}|${Number(aula || 0)}`;
}

function obterTurnoAulaPorFaixaGrade(faixaGlobal) {
    const faixa = Number(faixaGlobal || 0);
    if (!Number.isInteger(faixa) || faixa <= 0) {
        return null;
    }

    for (const turno of TURNOS_GRADE_HORARIO) {
        const faixaInicial = Number(turno.faixaInicial || 0);
        const faixaFinal = faixaInicial + Number(turno.aulas || 0) - 1;
        if (faixa >= faixaInicial && faixa <= faixaFinal) {
            return {
                turnoId: turno.id,
                aula: faixa - faixaInicial + 1
            };
        }
    }

    return null;
}

function obterTurnoAulaGradeReserva(reserva) {
    const porFaixa = obterTurnoAulaPorFaixaGrade(faixaGlobalReserva(reserva));
    if (porFaixa) {
        return porFaixa;
    }

    const turno = normalizarTurnoId(reserva?.turno);
    const aula = Number(reserva?.aula || 0);
    if (!Number.isInteger(aula) || aula <= 0) {
        return null;
    }

    if (turno === "MATUTINO" && aula <= 5) {
        return { turnoId: "MATUTINO", aula };
    }
    if ((turno === "VESPERTINO" || turno === "VESPERTINO_EM") && aula <= 6) {
        return { turnoId: "VESPERTINO", aula };
    }
    if (turno === "INTEGRAL") {
        if (aula <= 5) {
            return { turnoId: "MATUTINO", aula };
        }
        const aulaVespertino = aula - 4;
        if (aulaVespertino >= 1 && aulaVespertino <= 6) {
            return { turnoId: "VESPERTINO", aula: aulaVespertino };
        }
    }

    return null;
}

function mapearReservasDiaPorCelula() {
    const mapa = new Map();
    const filtroRecursoId = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    const reservasDia = (reservasMes || []).filter((item) => {
        if (item.data !== dataSelecionada) {
            return false;
        }
        if (filtroRecursoId > 0 && Number(item.recurso_id) !== filtroRecursoId) {
            return false;
        }
        return true;
    });

    reservasDia.forEach((reserva) => {
        const posicaoGrade = obterTurnoAulaGradeReserva(reserva);
        if (!posicaoGrade) {
            return;
        }

        const chave = chaveCelulaAgendaDia(posicaoGrade.turnoId, posicaoGrade.aula);
        if (!mapa.has(chave)) {
            mapa.set(chave, []);
        }
        mapa.get(chave).push(reserva);
    });

    mapa.forEach((listaReservas) => {
        listaReservas.sort((a, b) => compararReservas(a, b, "recurso"));
    });

    return mapa;
}

function mapearAulasProfessorDiaPorCelula() {
    const mapa = new Map();

    (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : []).forEach((aula) => {
        const posicaoGrade = obterTurnoAulaPorFaixaGrade(Number(aula.faixa_global || 0));
        if (!posicaoGrade) {
            return;
        }

        const chave = chaveCelulaAgendaDia(posicaoGrade.turnoId, posicaoGrade.aula);
        if (!mapa.has(chave)) {
            mapa.set(chave, []);
        }
        mapa.get(chave).push(aula);
    });

    mapa.forEach((listaAulas) => {
        listaAulas.sort((a, b) => compararTextoPtBr(a.turma_nome, b.turma_nome));
    });

    return mapa;
}

function obterProfessorCurtoReservaSemanal(reserva) {
    const nomeProfessor = String(reserva?.professor_nome || "").trim();
    return nomeProfessor ? nomeProfessor.split(" ")[0] : "Professor";
}

function obterChaveAgrupamentoReservaSemanal(reserva) {
    return [
        String(reserva?.data || "").trim(),
        String(faixaGlobalReserva(reserva) || ""),
        String(reserva?.usuario_id || reserva?.professor_nome || "").trim().toLowerCase(),
        String(reserva?.turma || "").trim().toLowerCase(),
        String(reserva?.tema_aula || "").trim().toLowerCase(),
        String(reserva?.observacao || "").trim().toLowerCase()
    ].join("|");
}

function agruparReservasSemanaisPorAula(reservas = []) {
    const grupos = new Map();

    reservas.forEach((reserva) => {
        const chave = obterChaveAgrupamentoReservaSemanal(reserva);
        if (!grupos.has(chave)) {
            grupos.set(chave, []);
        }
        grupos.get(chave).push(reserva);
    });

    return Array.from(grupos.values()).sort((grupoA, grupoB) => {
        const reservaA = grupoA[0] || {};
        const reservaB = grupoB[0] || {};

        return (
            compararTextoPtBr(String(reservaA.turma || ""), String(reservaB.turma || ""))
            || compararTextoPtBr(
                obterProfessorCurtoReservaSemanal(reservaA),
                obterProfessorCurtoReservaSemanal(reservaB)
            )
            || compararTextoPtBr(String(reservaA.tema_aula || ""), String(reservaB.tema_aula || ""))
        );
    });
}

function criarLinhaRecursoReservaSemanal(
    reserva,
    {
        permitirCancelar = false
    } = {}
) {
    const linha = document.createElement("div");
    linha.className = "weekly-group-resource-row";

    const recurso = document.createElement("p");
    recurso.className = "weekly-group-resource-name";
    recurso.innerText = reserva.recurso_nome || "Recurso não informado";
    linha.appendChild(recurso);

    if (permitirCancelar) {
        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.className = "weekly-chip-cancel-btn";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarReserva(reserva.id));
        linha.appendChild(btnCancelar);
    }

    return linha;
}

function criarCardGrupoReservaSemanal(grupoReservas = []) {
    const reservaPrincipal = grupoReservas[0];
    if (!reservaPrincipal) {
        return document.createElement("div");
    }

    const card = document.createElement("article");
    card.className = "weekly-booking-chip weekly-booking-group-card";

    const topo = document.createElement("div");
    topo.className = "weekly-chip-top weekly-booking-group-header";

    const contexto = document.createElement("p");
    contexto.className = "weekly-chip-meta weekly-booking-group-context";
    contexto.innerText = [
        String(reservaPrincipal.turma || "").trim() || "Turma não informada",
        obterProfessorCurtoReservaSemanal(reservaPrincipal)
    ].join(" | ");
    topo.appendChild(contexto);

    if (grupoReservas.length > 1) {
        const quantidade = document.createElement("span");
        quantidade.className = "weekly-booking-group-count";
        quantidade.innerText = `${grupoReservas.length} recursos`;
        topo.appendChild(quantidade);
    }

    card.appendChild(topo);

    const listaRecursos = document.createElement("div");
    listaRecursos.className = "weekly-booking-group-resources";
    grupoReservas.forEach((reserva) => {
        listaRecursos.appendChild(criarLinhaRecursoReservaSemanal(reserva, {
            permitirCancelar: reservaPodeSerCancelada(reserva)
        }));
    });
    card.appendChild(listaRecursos);

    const tema = String(reservaPrincipal.tema_aula || "").trim();
    if (tema) {
        const temaEl = document.createElement("p");
        temaEl.className = "weekly-chip-theme";
        temaEl.innerText = tema;
        card.appendChild(temaEl);
    }

    const observacao = String(reservaPrincipal.observacao || "").trim();
    if (observacao) {
        const observacaoEl = document.createElement("p");
        observacaoEl.className = "weekly-chip-meta weekly-booking-group-observation";
        observacaoEl.innerText = observacao;
        card.appendChild(observacaoEl);
    }

    return card;
}

function criarNotaAgendaDia(texto) {
    const nota = document.createElement("p");
    nota.className = "weekly-cell-empty scheduler-agenda-cell-note";
    nota.innerText = texto;
    return nota;
}

function criarCardAulaAgendaDia(aula, reservasHorario = []) {
    const card = document.createElement("article");
    card.className = "scheduler-agenda-class-card";

    const recursosDisponiveis = obterRecursosDisponiveisParaSelecao({
        data: aula.data,
        faixaGlobal: Number(aula.faixa_global || 0)
    });
    const selecionada = selecaoAulaAgendamento.chave
        && chaveAulaAgendamento(aula) === selecaoAulaAgendamento.chave;
    const podeSelecionar = recursosDisponiveis.length > 0;

    if (selecionada) {
        card.classList.add("is-selected");
    }
    if (podeSelecionar) {
        card.classList.add("is-clickable");
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.addEventListener("click", () => selecionarAulaParaAgendamento(aula));
        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selecionarAulaParaAgendamento(aula);
            }
        });
    }

    const topo = document.createElement("div");
    topo.className = "scheduler-agenda-class-top";

    const tituloWrap = document.createElement("div");
    const titulo = document.createElement("h4");
    titulo.innerText = String(aula.turma_nome || "").trim() || "Turma não informada";
    const meta = document.createElement("p");
    meta.className = "scheduler-agenda-class-meta";
    meta.innerText = [
        String(aula.disciplina_nome || "").trim() || "Disciplina não informada",
        aulaLabel(Number(aula.aula_numero || 0)),
        nomeTurnoExibicao(aula.turno, aula.turno_nome)
    ].filter(Boolean).join(" | ");
    tituloWrap.appendChild(titulo);
    tituloWrap.appendChild(meta);

    const status = document.createElement("span");
    status.className = "scheduler-agenda-class-status";
    if (selecionada) {
        status.dataset.variant = "selected";
        status.innerText = "Selecionada";
    } else if (podeSelecionar) {
        status.dataset.variant = "available";
        status.innerText = `${recursosDisponiveis.length} livre(s)`;
    } else {
        status.dataset.variant = "full";
        status.innerText = "Sem vaga";
    }

    topo.appendChild(tituloWrap);
    topo.appendChild(status);
    card.appendChild(topo);

    const disponibilidade = document.createElement("p");
    disponibilidade.className = "scheduler-agenda-class-availability";
    if (recursos.length === 0) {
        disponibilidade.innerText = "Nenhum recurso ativo cadastrado para agendamento.";
    } else if (recursosDisponiveis.length === 0) {
        disponibilidade.innerText = "Todos os recursos já estão ocupados neste horário.";
    } else if (reservasHorario.length === 0) {
        disponibilidade.innerText = `${recursosDisponiveis.length} recurso(s) livre(s) para esta aula.`;
    } else {
        disponibilidade.innerText = `${reservasHorario.length} recurso(s) já reservado(s) e ${recursosDisponiveis.length} livre(s) neste horário.`;
    }
    card.appendChild(disponibilidade);

    const acoes = document.createElement("div");
    acoes.className = "scheduler-agenda-class-actions";

    const btnSelecionar = document.createElement("button");
    btnSelecionar.type = "button";
    btnSelecionar.className = "btn-destaque";
    btnSelecionar.disabled = !podeSelecionar;
    btnSelecionar.innerText = selecionada ? "Aula selecionada" : "Selecionar aula";
    btnSelecionar.addEventListener("click", (event) => {
        event.stopPropagation();
        if (podeSelecionar) {
            selecionarAulaParaAgendamento(aula);
        }
    });
    acoes.appendChild(btnSelecionar);

    card.appendChild(acoes);
    return card;
}

function obterAulaPrincipalAgendamentoHorario(aulasCelula = []) {
    if (!Array.isArray(aulasCelula) || aulasCelula.length === 0) {
        return null;
    }

    if (selecaoAulaAgendamento.chave) {
        const aulaSelecionada = aulasCelula.find(
            (aula) => chaveAulaAgendamento(aula) === selecaoAulaAgendamento.chave
        );
        if (aulaSelecionada) {
            return aulaSelecionada;
        }
    }

    return aulasCelula[0] || null;
}

function criarAcaoAgendamentoAgendaDia({
    professor = null,
    aulasCelula = [],
    reservasCelula = []
} = {}) {
    const wrapper = document.createElement("div");
    wrapper.className = "scheduler-agenda-slot-action";

    const aulaPrincipal = obterAulaPrincipalAgendamentoHorario(aulasCelula);
    const recursosDisponiveis = aulaPrincipal
        ? obterRecursosDisponiveisParaSelecao({
            data: aulaPrincipal.data,
            faixaGlobal: Number(aulaPrincipal.faixa_global || 0)
        })
        : [];
    const selecionada = aulaPrincipal
        && selecaoAulaAgendamento.chave
        && chaveAulaAgendamento(aulaPrincipal) === selecaoAulaAgendamento.chave;

    const nota = document.createElement("p");
    nota.className = "scheduler-agenda-slot-action-note";

    let podeSelecionar = true;
    if (!professor) {
        nota.innerText = "Selecione um professor para habilitar o agendamento.";
        podeSelecionar = false;
    } else if (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0) {
        nota.innerText = "Sem aula deste professor nesta data.";
        podeSelecionar = false;
    } else if (!aulaPrincipal) {
        nota.innerText = "Sem aula neste horário.";
        podeSelecionar = false;
    } else if (recursos.length === 0) {
        nota.innerText = "Nenhum recurso ativo cadastrado para agendamento.";
        podeSelecionar = false;
    } else if (recursosDisponiveis.length === 0) {
        nota.innerText = "Todos os recursos já estão ocupados neste horário.";
        podeSelecionar = false;
    } else if (reservasCelula.length === 0) {
        nota.innerText = `${recursosDisponiveis.length} recurso(s) livre(s) para este horário.`;
    } else {
        nota.innerText = `${reservasCelula.length} recurso(s) já reservado(s) e ${recursosDisponiveis.length} livre(s).`;
    }
    wrapper.appendChild(nota);

    const acoes = document.createElement("div");
    acoes.className = "scheduler-agenda-slot-action-buttons";

    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "btn-destaque";
    botao.disabled = !podeSelecionar;
    botao.innerText = selecionada ? "Horário escolhido" : "Reservar neste horário";
    botao.addEventListener("click", () => {
        if (!podeSelecionar || !aulaPrincipal) {
            return;
        }
        selecionarAulaParaAgendamento(aulaPrincipal);
    });
    acoes.appendChild(botao);

    wrapper.appendChild(acoes);
    return wrapper;
}

function renderAgendaDiaAulas() {
    const tabela = el("tabelaAgendaDia");
    const subtitulo = el("subtituloAgendaDia");

    if (!tabela || !subtitulo) {
        return;
    }

    const professor = obterProfessorAgendaAtivo();
    const diaSemana = obterDiaSemanaApiPorData(dataSelecionada);
    const nomeProfessor = professor?.nome || (usuarioEhAdmin() ? "Selecione um professor" : "Professor");
    const subtituloPartes = [paraDataBr(dataSelecionada), nomeProfessor];
    if (professor && (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0)) {
        subtituloPartes.push("sem aulas registradas");
    }
    subtitulo.innerText = subtituloPartes.join(" | ");

    if (!["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"].includes(diaSemana)) {
        renderEstadoAulasDia("A agenda por aula está disponível apenas para dias letivos.");
        return;
    }

    const reservasPorCelula = mapearReservasDiaPorCelula();
    const aulasPorCelula = mapearAulasProfessorDiaPorCelula();

    tabela.innerHTML = "";

    const thead = document.createElement("thead");
    const cabecalho = document.createElement("tr");
    [
        "Aula",
        "Recursos agendados"
    ].forEach((titulo) => {
        const th = document.createElement("th");
        th.scope = "col";
        th.innerText = titulo;
        cabecalho.appendChild(th);
    });
    thead.appendChild(cabecalho);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    let turnoAtual = "";

    obterLinhasAulasGradeSemanal().forEach((linhaGrade) => {
        if (linhaGrade.turnoId !== turnoAtual) {
            turnoAtual = linhaGrade.turnoId;
            const linhaTurno = document.createElement("tr");
            linhaTurno.className = "weekly-turno-row";
            const thTurno = document.createElement("th");
            thTurno.colSpan = 2;
            thTurno.scope = "colgroup";
            thTurno.innerText = linhaGrade.turnoNome;
            linhaTurno.appendChild(thTurno);
            tbody.appendChild(linhaTurno);
        }

        const chave = chaveCelulaAgendaDia(linhaGrade.turnoId, linhaGrade.aula);
        const aulasCelula = aulasPorCelula.get(chave) || [];
        const reservasCelula = reservasPorCelula.get(chave) || [];

        const tr = document.createElement("tr");

        const label = document.createElement("th");
        label.scope = "row";
        label.className = "weekly-aula-label";
        label.innerText = aulaLabel(linhaGrade.aula);
        tr.appendChild(label);

        const celulaRecursos = document.createElement("td");
        celulaRecursos.className = "weekly-aula-slot scheduler-agenda-resources-cell";

        const stackReservas = document.createElement("div");
        stackReservas.className = "weekly-cell-stack scheduler-agenda-resources-stack";

        if (reservasCelula.length === 0) {
            stackReservas.appendChild(criarNotaAgendaDia("Nenhum recurso agendado neste horário."));
        } else {
            agruparReservasSemanaisPorAula(reservasCelula).forEach((grupoReservas) => {
                stackReservas.appendChild(criarCardGrupoReservaSemanal(grupoReservas));
            });
        }
        stackReservas.appendChild(criarAcaoAgendamentoAgendaDia({
            professor,
            aulasCelula,
            reservasCelula
        }));

        celulaRecursos.appendChild(stackReservas);
        tr.appendChild(celulaRecursos);
        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);
}

async function selecionarDataAgendamento(dataIso, { fecharCalendarioAoFinal = false } = {}) {
    const dataTexto = String(dataIso || "").trim();
    if (!dataTexto) {
        return;
    }

    dataSelecionada = dataTexto;
    el("dataReserva").value = dataSelecionada;
    sincronizarSemanaVisivelComDataSelecionada();

    const anoSelecionado = Number(dataSelecionada.slice(0, 4));
    const mesSelecionado = Number(dataSelecionada.slice(5, 7)) - 1;
    const mudouMes =
        mesAtual.getFullYear() !== anoSelecionado ||
        mesAtual.getMonth() !== mesSelecionado;

    if (mudouMes) {
        mesAtual = new Date(anoSelecionado, mesSelecionado, 1);
        await carregarReservasMes();
    }

    await carregarAulasProfessorDia();
    renderSemanaAgendamento();
    renderCalendario();
    renderReservasDia();
    renderAgendaDiaAulas();
    renderMinhasReservas();
    sincronizarWizardAgendamento();

    if (fecharCalendarioAoFinal) {
        fecharPainelLateralAgendamento("painelCalendarioAgendamento");
    }
}

function renderSemanaAgendamento() {
    const titulo = el("tituloSemanaAtual");
    const lista = el("agendaSemanaDias");

    if (!titulo || !lista) {
        return;
    }

    if (!semanaVisivelInicio) {
        sincronizarSemanaVisivelComDataSelecionada();
    }

    titulo.innerText = formatarTituloSemana(semanaVisivelInicio);
    lista.innerHTML = "";

    const hojeIso = obterHojeIso();

    for (let indice = 0; indice < 7; indice++) {
        const dataDia = somarDiasDataLocal(semanaVisivelInicio, indice);
        const dataIso = paraIso(dataDia);
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "scheduler-week-day";

        if (dataIso === dataSelecionada) {
            botao.classList.add("is-selected");
        }
        if (dataIso === hojeIso) {
            botao.classList.add("is-today");
        }
        if (dataDia.getDay() === 0 || dataDia.getDay() === 6) {
            botao.classList.add("is-weekend");
        }

        const diaSemana = document.createElement("span");
        diaSemana.className = "scheduler-week-day-label";
        diaSemana.innerText = formatarDiaSemanaAgenda(dataDia);

        const numero = document.createElement("strong");
        numero.className = "scheduler-week-day-number";
        numero.innerText = dataDia.toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "2-digit"
        });

        const estado = document.createElement("small");
        estado.className = "scheduler-week-day-state";
        estado.innerText = dataIso === dataSelecionada
            ? "Selecionado"
            : dataIso === hojeIso
                ? "Hoje"
                : "Abrir";

        botao.appendChild(diaSemana);
        botao.appendChild(numero);
        botao.appendChild(estado);
        botao.addEventListener("click", async () => {
            try {
                await selecionarDataAgendamento(dataIso);
            } catch (err) {
                setMensagem(err.message || "Não foi possível carregar a data selecionada.", "erro");
            }
        });

        lista.appendChild(botao);
    }
}

function renderCalendario() {
    const ano = mesAtual.getFullYear();
    const mes = mesAtual.getMonth();
    if (el("mesAtual")) {
        el("mesAtual").innerText = `${nomesMeses[mes]} ${ano}`;
    }

    const grid = el("calendarioGrid");
    if (!grid) {
        return;
    }
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
            ? `.`
            : "Livre";

        btnDia.appendChild(numero);
        btnDia.appendChild(resumo);
        btnDia.addEventListener("click", async () => {
            try {
                await selecionarDataAgendamento(dataIso, { fecharCalendarioAoFinal: true });
            } catch (err) {
                setMensagem(err.message || "Não foi possível carregar a data selecionada.", "erro");
            }
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

    const aulaExibicao = numeroAulaReserva(reserva);
    const titulo = document.createElement("p");
    titulo.innerText = `${reserva.recurso_nome} | ${aulaLabel(aulaExibicao || reserva.aula)}`;

    const professor = document.createElement("p");
    professor.className = "booking-professor";
    professor.innerText = `Professor(a): ${reserva.professor_nome || "Não informado"}`;

    const detalheTurma = document.createElement("p");
    detalheTurma.className = "booking-detail";
    const turmaTexto = reserva.turma || "Não informada";
    detalheTurma.innerText = `Turma: ${turmaTexto}`;
    const periodoTexto = nomeTurno(reserva.turno) || "Turno não informado"; 
    detalheTurma.innerText += ` | ${periodoTexto}`;

    li.appendChild(titulo);
    if (exibirProfessor) {
        li.appendChild(professor);
    }
    li.appendChild(detalheTurma);

    const temaAula = String(reserva.tema_aula || "").trim();
    if (temaAula) {
        const detalheTema = document.createElement("p");
        detalheTema.className = "booking-theme";
        detalheTema.innerText = `Tema: ${temaAula}`;
        li.appendChild(detalheTema);
    }

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
    await carregarAulasProfessorDia();
    sincronizarSemanaVisivelComDataSelecionada();
    renderSemanaAgendamento();
    renderCalendario();
    renderReservasDia();
    renderAgendaDiaAulas();
    renderMinhasReservas();
    sincronizarWizardAgendamento();
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

    setMensagem("Reserva cancelada com sucesso.");
    await atualizarTelaAgendamento();
}

async function agendarRecurso() {
    if (turmas.length === 0) {
        setMensagem("Não há turmas ativas cadastradas. Procure a coordenação.", "erro");
        return;
    }

    if (!selecaoAulaAgendamento.chave) {
        setMensagem("Selecione uma aula do dia para iniciar o agendamento.", "erro");
        return;
    }

    const recursosSelecionados = obterRecursosSelecionadosAgendamento();
    const data = selecaoAulaAgendamento.data || el("dataReserva").value;
    const turmaNome = selecaoAulaAgendamento.turmaNome;
    const faixaSelecionada = Number(selecaoAulaAgendamento.faixaGlobal || 0);
    const temaAula = el("temaAulaReserva").value.trim();
    const professorIdSelecionado = obterProfessorAgendaAtivoId();
    const observacao = el("observacaoReserva").value.trim();

    const turma = obterTurmaPorNome(turmaNome);
    if (!turma || !turma.turno_valido || Number(turma.aulas) <= 0) {
        setMensagem("A turma selecionada está sem turno válido. Atualize no painel admin.", "erro");
        return;
    }

    if (recursosSelecionados.length === 0 || !data || !faixaSelecionada || !turmaNome || !temaAula) {
        setMensagem("Selecione a aula, ao menos um recurso e informe o tema da aula.", "erro");
        return;
    }

    if (usuarioEhAdmin() && !professorIdSelecionado) {
        setMensagem("Selecione o professor solicitante do agendamento.", "erro");
        return;
    }

    const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixaSelecionada);
    if (!Number.isInteger(aulaTurno) || aulaTurno < 1 || aulaTurno > Number(turma.aulas)) {
        setMensagem("A faixa escolhida é inválida para o turno da turma.", "erro");
        return;
    }

    const payloadBase = {
        data,
        aula: String(aulaTurno),
        turma: turmaNome,
        tema_aula: temaAula,
        observacao
    };
    if (usuarioEhAdmin()) {
        payloadBase.professor_id = professorIdSelecionado;
    }

    definirEstadoEnvioAgendamento(true);

    try {
        const sucessos = [];
        const falhas = [];

        for (const recurso of recursosSelecionados) {
            const payload = {
                ...payloadBase,
                recurso_id: Number(recurso.id)
            };

            const res = await fetchComAuth("/agendamento/reservas", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });

            const body = await res.json();
            if (!res.ok) {
                falhas.push({
                    recurso,
                    mensagem: body.detail || `Não foi possível agendar ${recurso.nome}.`
                });
                continue;
            }

            sucessos.push({ recurso, body });
        }

        if (sucessos.length === 0) {
            setMensagem(
                falhas[0]?.mensagem || "Não foi possível concluir o agendamento dos recursos selecionados.",
                "erro"
            );
            return;
        }

        dataSelecionada = data;
        sincronizarSemanaVisivelComDataSelecionada();

        if (
            mesAtual.getFullYear() !== Number(data.slice(0, 4)) ||
            mesAtual.getMonth() !== Number(data.slice(5, 7)) - 1
        ) {
            mesAtual = new Date(Number(data.slice(0, 4)), Number(data.slice(5, 7)) - 1, 1);
        }

        await atualizarTelaAgendamento();

        if (falhas.length === 0) {
            const mensagemSucesso = sucessos.length === 1
                ? "Reserva confirmada com sucesso."
                : `${sucessos.length} reservas confirmadas com sucesso.`;
            setMensagem(mensagemSucesso);
            limparSelecaoAulaAgendamento();
            renderAgendaDiaAulas();
            sincronizarWizardAgendamento();
            return;
        }

        agendamentoWizard.currentStep = 2;
        sincronizarWizardAgendamento();
        const detalheFalhas = falhas
            .slice(0, 2)
            .map((item) => `${item.recurso.nome}: ${item.mensagem}`)
            .join(" | ");
        const resumoFalhas = falhas.length > 2
            ? `${detalheFalhas} | +${falhas.length - 2} falha(s)`
            : detalheFalhas;
        setMensagem(
            `${sucessos.length} recurso(s) agendado(s), mas ${falhas.length} falharam. ${resumoFalhas}`,
            "erro"
        );
    } catch (err) {
        setMensagem(err.message || "Não foi possível concluir o agendamento.", "erro");
    } finally {
        definirEstadoEnvioAgendamento(false);
    }
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

    el("btnAbrirCalendarioGeralNavbar")?.addEventListener("click", () => {
        abrirPainelLateralAgendamento("painelCalendarioAgendamento");
    });
    el("btnAbrirMeusAgendamentosNavbar")?.addEventListener("click", () => {
        abrirPainelLateralAgendamento("painelMinhasReservasAgendamento");
    });
    el("btnFecharCalendarioGeral")?.addEventListener("click", () => {
        fecharPainelLateralAgendamento("painelCalendarioAgendamento");
    });
    el("btnFecharMinhasReservas")?.addEventListener("click", () => {
        fecharPainelLateralAgendamento("painelMinhasReservasAgendamento");
    });
    document.querySelectorAll("[data-close-scheduler-drawer='true']").forEach((elemento) => {
        elemento.addEventListener("click", () => {
            fecharPainelLateralAgendamento();
        });
    });

    el("btnMesAnterior").addEventListener("click", async () => {
        try {
            const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
            await selecionarDataAgendamento(paraIso(deslocarMesDataLocal(dataBase, -1)));
        } catch (err) {
            setMensagem(err.message || "Não foi possível atualizar o mês selecionado.", "erro");
        }
    });

    el("btnMesProximo").addEventListener("click", async () => {
        try {
            const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
            await selecionarDataAgendamento(paraIso(deslocarMesDataLocal(dataBase, 1)));
        } catch (err) {
            setMensagem(err.message || "Não foi possível atualizar o mês selecionado.", "erro");
        }
    });

    el("btnMesHoje").addEventListener("click", async () => {
        try {
            await selecionarDataAgendamento(paraIso(new Date()));
        } catch (err) {
            setMensagem(err.message || "Não foi possível carregar a agenda de hoje.", "erro");
        }
    });

    el("btnSemanaAnterior")?.addEventListener("click", async () => {
        try {
            const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
            await selecionarDataAgendamento(paraIso(somarDiasDataLocal(dataBase, -7)));
        } catch (err) {
            setMensagem(err.message || "Não foi possível navegar para a semana anterior.", "erro");
        }
    });
    el("btnSemanaProxima")?.addEventListener("click", async () => {
        try {
            const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
            await selecionarDataAgendamento(paraIso(somarDiasDataLocal(dataBase, 7)));
        } catch (err) {
            setMensagem(err.message || "Não foi possível navegar para a próxima semana.", "erro");
        }
    });
    el("btnSemanaHoje")?.addEventListener("click", async () => {
        try {
            await selecionarDataAgendamento(paraIso(new Date()));
        } catch (err) {
            setMensagem(err.message || "Não foi possível voltar para a semana atual.", "erro");
        }
    });

    el("dataReserva").addEventListener("change", async () => {
        if (!el("dataReserva").value) return;
        try {
            await selecionarDataAgendamento(el("dataReserva").value);
        } catch (err) {
            setMensagem(err.message || "Não foi possível carregar a data selecionada.", "erro");
        }
    });

    el("professorAgendaFiltro")?.addEventListener("change", async () => {
        limparSelecaoAulaAgendamento({ manterFormulario: true });
        try {
            await carregarAulasProfessorDia();
        } catch (err) {
            setMensagem(err.message || "Não foi possível carregar as aulas do professor.", "erro");
        }
        renderAgendaDiaAulas();
        sincronizarWizardAgendamento();
    });
    el("temaAulaReserva").addEventListener("input", () => sincronizarWizardAgendamento());
    el("observacaoReserva").addEventListener("input", () => sincronizarWizardAgendamento());
    el("btnTrocarAulaSelecionada").addEventListener("click", () => {
        limparSelecaoAulaAgendamento({ manterFormulario: true });
        renderAgendaDiaAulas();
        sincronizarWizardAgendamento({ scroll: true });
    });
    el("btnContinuarAgendamentoContexto").addEventListener("click", () => irParaEtapaAgendamento(3));
    el("btnVoltarAgendamentoDetalhes").addEventListener("click", () => irParaEtapaAgendamento(2));
    el("btnContinuarAgendamentoDetalhes").addEventListener("click", () => irParaEtapaAgendamento(4));
    el("btnVoltarAgendamentoResumo").addEventListener("click", () => irParaEtapaAgendamento(3));

    registrarControlesOrdenacao();
    el("btnAgendar").addEventListener("click", agendarRecurso);

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            fecharPainelLateralAgendamento();
        }
    });
}

async function init() {
    try {
        dataSelecionada = paraIso(new Date());
        el("dataReserva").value = dataSelecionada;
        sincronizarSemanaVisivelComDataSelecionada();

        carregarPreferenciasOrdenacao();
        registrarEventos();
        sincronizarWizardAgendamento();
        await carregarUsuario();
        await carregarProfessoresAgendamentoAdmin();
        await carregarOpcoesAgendamento();
        await carregarRecursos();

        if (recursos.length === 0) {
            setMensagem("Nenhum recurso ativo cadastrado para agendamento.", "erro");
            return;
        }

        await atualizarTelaAgendamento();
        sincronizarWizardAgendamento();
    } catch (err) {
        definirEstadoEnvioAgendamento(false);
        setMensagem(err.message || "Erro ao carregar módulo de agendamento.", "erro");
    }
}

init();
