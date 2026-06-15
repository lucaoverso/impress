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

let usuarioAtual = null;
let recursos = [];
let turnos = [];
let turmas = [];
let gradeAulas = [];
let aulasGlobais = [];
let reservasMes = [];
let professoresAgendamento = [];
let mesAtual = new Date();
let dataSelecionada = paraIso(new Date());
let semanaVisivelInicio = null;
let reservaDetalheAtual = null;
let reservaCancelamentoPendenteId = 0;
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
let elementoFocoAntesDrawer = null;
let elementoFocoAntesDialog = null;
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
const aulasAdicionaisAgendamento = new Set();
const detalhesAulasAgendamento = {};
let aulasProfessorDia = [];
const carrosselRecursosEtapaInicial = {
    mouseDown: false,
    dragging: false,
    startX: 0,
    startScrollLeft: 0,
    suppressClickUntil: 0
};

function textoPadraoDetalheReserva(valor, fallback = "-") {
    const texto = String(valor || "").trim();
    return texto || fallback;
}

function normalizarGrupoReservasDetalhe(reservaOuGrupo) {
    if (Array.isArray(reservaOuGrupo)) {
        return reservaOuGrupo.filter(Boolean);
    }
    return reservaOuGrupo ? [reservaOuGrupo] : [];
}

function formatarTituloRecursosGrupo(grupoReservas = []) {
    const nomes = Array.from(
        new Set(
            normalizarGrupoReservasDetalhe(grupoReservas)
                .map((reserva) => textoPadraoDetalheReserva(reserva.recurso_nome, "").trim())
                .filter(Boolean)
        )
    );

    return nomes.length > 0 ? nomes.join(", ") : "Recurso não informado";
}

function obterImagemCapaGrupoReservas(grupoReservas = []) {
    const reservasGrupo = normalizarGrupoReservasDetalhe(grupoReservas);
    for (const reserva of reservasGrupo) {
        const recursoId = Number(reserva?.recurso_id || 0);
        if (!recursoId) {
            continue;
        }

        const recurso = recursos.find((item) => Number(item?.id || 0) === recursoId);
        const imagemCapa = String(recurso?.imagem_capa || "").trim();
        if (imagemCapa) {
            return imagemCapa;
        }
    }

    return "";
}

function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
}

function itensVisuaisGradeAtivos() {
    return (Array.isArray(gradeAulas) ? gradeAulas : [])
        .filter((item) => Boolean(item?.ativo ?? true))
        .sort((a, b) => Number(a?.ordem_visual || 0) - Number(b?.ordem_visual || 0));
}

function aulasGlobaisAtivas() {
    return (Array.isArray(aulasGlobais) ? aulasGlobais : [])
        .filter((item) => Boolean(item?.ativo ?? true))
        .sort((a, b) => Number(a?.aula_numero || 0) - Number(b?.aula_numero || 0));
}

function obterAulaGlobalPorNumero(numeroAula) {
    const aula = Number(numeroAula || 0);
    return aulasGlobaisAtivas().find((item) => Number(item?.aula_numero || 0) === aula) || null;
}

function periodoAulaPorFaixa(faixaGlobal, turnoReserva = "") {
    const faixa = Number(faixaGlobal || 0);
    const aulaConfig = obterAulaGlobalPorNumero(faixa);
    const periodoConfigurado = String(aulaConfig?.periodo || "").trim().toUpperCase();
    if (periodoConfigurado === "MATUTINO" || periodoConfigurado === "VESPERTINO") {
        return periodoConfigurado;
    }

    const horarioInicio = String(aulaConfig?.horario_inicio || "").trim();
    const horaInicio = Number(horarioInicio.split(":", 1)[0]);
    if (horarioInicio && Number.isInteger(horaInicio)) {
        return horaInicio < 12 ? "MATUTINO" : "VESPERTINO";
    }

    if (faixa > 0) {
        return faixa <= MAX_AULAS_EXIBICAO ? "MATUTINO" : "VESPERTINO";
    }
    return normalizarTurnoId(turnoReserva) === "MATUTINO" ? "MATUTINO" : "VESPERTINO";
}

function nomePeriodoAgendamento(periodo) {
    return String(periodo || "").toUpperCase() === "MATUTINO" ? "Matutino" : "Vespertino";
}

function aulaLabel(aula) {
    const aulaConfig = obterAulaGlobalPorNumero(aula);
    if (aulaConfig?.label_curta) {
        return aulaConfig.label_curta;
    }
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
}

function abrirPainelLateralAgendamento(drawerId) {
    const drawer = el(drawerId);
    if (!drawer) {
        return;
    }

    const haviaDrawerAberto = Boolean(document.querySelector(".scheduler-side-drawer.is-open"));
    if (!haviaDrawerAberto) {
        elementoFocoAntesDrawer = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
    }

    document.querySelectorAll(".scheduler-side-drawer.is-open").forEach((painelAberto) => {
        if (painelAberto.id !== drawerId) {
            painelAberto.classList.remove("is-open");
            painelAberto.setAttribute("aria-hidden", "true");
            painelAberto.inert = true;
        }
    });

    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    drawer.inert = false;
    document.body.classList.add("scheduler-drawer-open");
    window.requestAnimationFrame(() => {
        drawer.querySelector(".scheduler-side-panel")?.focus();
    });
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
        drawer.inert = true;
    });

    if (!document.querySelector(".scheduler-side-drawer.is-open")) {
        document.body.classList.remove("scheduler-drawer-open");
        elementoFocoAntesDrawer?.focus();
        elementoFocoAntesDrawer = null;
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

function obterRecursoEmFocoAgenda() {
    const recursoId = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    if (recursoId <= 0) {
        return null;
    }
    return recursos.find((recurso) => Number(recurso.id) === recursoId) || null;
}

function agendaEtapaPermiteAgendamento() {
    return recursosSelecionadosAgendamento.size > 0;
}

function sincronizarFiltroRecursoAgendaComSelecao(recursoIdPreferencial = 0) {
    const idsSelecionados = Array.from(recursosSelecionadosAgendamento)
        .map((id) => Number(id || 0))
        .filter((id) => id > 0);

    if (idsSelecionados.length === 0) {
        configuracaoAgendaDia.filtroRecursoId = 0;
        return;
    }

    const preferencial = Number(recursoIdPreferencial || 0);
    if (preferencial > 0 && idsSelecionados.includes(preferencial)) {
        configuracaoAgendaDia.filtroRecursoId = preferencial;
        return;
    }

    const atual = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    if (atual > 0 && idsSelecionados.includes(atual)) {
        return;
    }

    configuracaoAgendaDia.filtroRecursoId = idsSelecionados[idsSelecionados.length - 1];
}

function filtrarReservasPorRecursoEmFoco(listaReservas = []) {
    const filtroRecursoId = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    if (filtroRecursoId <= 0) {
        return Array.isArray(listaReservas) ? listaReservas : [];
    }

    return (Array.isArray(listaReservas) ? listaReservas : []).filter(
        (reserva) => Number(reserva?.recurso_id || 0) === filtroRecursoId
    );
}

function obterResumoCapacidadeRecurso(recurso = {}) {
    const quantidadeItens = Math.max(Number(recurso?.quantidade_itens || 0), 0);
    if (quantidadeItens <= 0) {
        return "Capacidade nao informada";
    }
    return quantidadeItens === 1 ? "1 item disponivel" : `${quantidadeItens} itens disponiveis`;
}

function obterClasseIconeRecurso(recurso = {}) {
    const descricao = `${recurso?.tipo || ""} ${recurso?.nome || ""}`
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
    const iconesPorTermo = [
        [["projetor", "datashow", "data show"], "bi-projector-fill"],
        [["notebook", "laptop", "chromebook"], "bi-laptop-fill"],
        [["tablet"], "bi-tablet-fill"],
        [["audio", "som", "caixa de som", "alto-falante"], "bi-speaker-fill"],
        [["televisao", "tv", "monitor", "tela"], "bi-display-fill"],
        [["microfone"], "bi-mic-fill"],
        [["camera", "webcam"], "bi-camera-video-fill"],
        [["impressora"], "bi-printer-fill"],
        [["laboratorio", "maker", "robotica"], "bi-wrench-adjustable-circle-fill"]
    ];
    const correspondencia = iconesPorTermo.find(([termos]) => (
        termos.some((termo) => descricao.includes(termo))
    ));
    return correspondencia?.[1] || "bi-collection-fill";
}

function registrarCarrosselRecursosEtapaInicial() {
    const container = el("recursoCardsEtapaInicial");
    if (!container || container.dataset.dragScrollReady === "true") {
        return;
    }

    container.dataset.dragScrollReady = "true";

    const finalizarArraste = () => {
        if (!carrosselRecursosEtapaInicial.mouseDown) {
            return;
        }

        container.classList.remove("is-dragging");
        if (carrosselRecursosEtapaInicial.dragging) {
            carrosselRecursosEtapaInicial.suppressClickUntil = Date.now() + 180;
        }

        carrosselRecursosEtapaInicial.mouseDown = false;
        carrosselRecursosEtapaInicial.dragging = false;
    };

    container.addEventListener("mousedown", (event) => {
        if (event.button !== 0) {
            return;
        }

        carrosselRecursosEtapaInicial.mouseDown = true;
        carrosselRecursosEtapaInicial.dragging = false;
        carrosselRecursosEtapaInicial.startX = event.clientX;
        carrosselRecursosEtapaInicial.startScrollLeft = container.scrollLeft;
    });

    window.addEventListener("mousemove", (event) => {
        if (!carrosselRecursosEtapaInicial.mouseDown) {
            return;
        }

        const deslocamento = event.clientX - carrosselRecursosEtapaInicial.startX;
        if (!carrosselRecursosEtapaInicial.dragging && Math.abs(deslocamento) > 6) {
            carrosselRecursosEtapaInicial.dragging = true;
            container.classList.add("is-dragging");
        }

        if (!carrosselRecursosEtapaInicial.dragging) {
            return;
        }

        event.preventDefault();
        container.scrollLeft = carrosselRecursosEtapaInicial.startScrollLeft - deslocamento;
    });

    window.addEventListener("mouseup", finalizarArraste);
    window.addEventListener("blur", finalizarArraste);
    container.addEventListener("dragstart", (event) => event.preventDefault());
    container.addEventListener("click", (event) => {
        if (Date.now() > carrosselRecursosEtapaInicial.suppressClickUntil) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        carrosselRecursosEtapaInicial.suppressClickUntil = 0;
    }, true);
}

function renderVisaoGeralAgendamentosDia() {
    const container = el("schedulerDayOverviewList");
    const dataResumo = el("schedulerDayOverviewDate");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (dataResumo) {
        dataResumo.innerText = paraDataBr(dataSelecionada);
    }

    const reservasDia = (Array.isArray(reservasMes) ? reservasMes : [])
        .filter((reserva) => reserva.data === dataSelecionada)
        .sort((a, b) => {
            const diferencaTurno = ordemTurno(a.turno) - ordemTurno(b.turno);
            if (diferencaTurno !== 0) {
                return diferencaTurno;
            }
            return numeroAulaReserva(a) - numeroAulaReserva(b);
        });

    if (reservasDia.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-day-overview-empty";
        vazio.innerText = "Nenhum recurso agendado neste dia.";
        container.appendChild(vazio);
        return;
    }

    const grupos = new Map([
        ["MATUTINO", []],
        ["VESPERTINO", []]
    ]);
    reservasDia.forEach((reserva) => {
        const periodo = periodoAulaPorFaixa(faixaGlobalReserva(reserva), reserva.turno);
        grupos.get(periodo).push(reserva);
    });

    grupos.forEach((reservasPeriodo, periodo) => {
        if (reservasPeriodo.length === 0) {
            return;
        }

        const grupo = document.createElement("section");
        grupo.className = "scheduler-day-overview-shift";

        const titulo = document.createElement("h4");
        titulo.innerText = nomePeriodoAgendamento(periodo);
        grupo.appendChild(titulo);

        const lista = document.createElement("div");
        lista.className = "scheduler-day-overview-rows";

        reservasPeriodo.forEach((reserva) => {
            const linha = document.createElement("div");
            linha.className = "scheduler-day-overview-row";

            const recurso = document.createElement("strong");
            recurso.innerText = textoPadraoDetalheReserva(
                reserva.recurso_nome,
                "Recurso não informado"
            );

            const professor = document.createElement("span");
            professor.innerText = textoPadraoDetalheReserva(
                reserva.professor_nome,
                "Responsável não informado"
            );

            const copy = document.createElement("div");
            copy.className = "scheduler-day-overview-copy";
            copy.appendChild(recurso);
            copy.appendChild(professor);

            const aula = document.createElement("span");
            aula.className = "scheduler-day-overview-lesson";
            aula.innerText = aulaLabel(numeroAulaReserva(reserva));

            linha.appendChild(copy);
            linha.appendChild(aula);
            lista.appendChild(linha);
        });

        grupo.appendChild(lista);
        container.appendChild(grupo);
    });
}

function renderRecursosEtapaInicial() {
    const container = el("recursoCardsEtapaInicial");
    const resumo = el("resumoRecursosEtapaInicial");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    renderVisaoGeralAgendamentosDia();

    if (!Array.isArray(recursos) || recursos.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-resource-empty";
        vazio.innerText = "Nenhum recurso ativo cadastrado para agendamento.";
        container.appendChild(vazio);
        if (resumo) {
            resumo.innerText = "Procure a coordenação para cadastrar um recurso.";
        }
        registrarCarrosselRecursosEtapaInicial();
        return;
    }

    recursos.forEach((recurso) => {
        const selecionado = recursosSelecionadosAgendamento.has(Number(recurso.id));
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "scheduler-resource-stage-button";
        botao.setAttribute("aria-pressed", selecionado ? "true" : "false");
        if (selecionado) {
            botao.classList.add("is-selected");
        }

        const iconWrap = document.createElement("span");
        iconWrap.className = "scheduler-resource-stage-icon";
        iconWrap.setAttribute("aria-hidden", "true");

        const icon = document.createElement("i");
        icon.className = `bi ${obterClasseIconeRecurso(recurso)}`;
        iconWrap.appendChild(icon);
        botao.appendChild(iconWrap);

        const copy = document.createElement("div");
        copy.className = "scheduler-resource-stage-copy";

        const kicker = document.createElement("p");
        kicker.className = "scheduler-resource-stage-kicker";
        kicker.innerText = textoPadraoDetalheReserva(recurso?.tipo, "Recurso");

        const titulo = document.createElement("strong");
        titulo.className = "scheduler-resource-stage-title";
        titulo.innerText = textoPadraoDetalheReserva(recurso?.nome, "Recurso sem nome");

       

        const capacidade = document.createElement("p");
        capacidade.className = "scheduler-resource-stage-capacity";
        capacidade.innerText = obterResumoCapacidadeRecurso(recurso);

        copy.appendChild(kicker);
        copy.appendChild(titulo);
        copy.appendChild(capacidade);
        botao.appendChild(copy);

        botao.addEventListener("click", () => alternarSelecaoRecursoAgendamento(recurso.id));
        container.appendChild(botao);
    });

    if (!resumo) {
        registrarCarrosselRecursosEtapaInicial();
        return;
    }

    registrarCarrosselRecursosEtapaInicial();

    if (recursosSelecionadosAgendamento.size === 0) {
        resumo.innerText = "Escolha um recurso para consultar sua agenda por aula.";
        return;
    }

    const resumoRecursos = formatarResumoRecursosSelecionados();
    resumo.innerText = `Recurso selecionado: ${resumoRecursos}.`;
}

function atualizarEtapaPrimariaAgendamento(state = null) {
    const estado = state || obterEstadoWizardAgendamento();
    const etapaRecursos = el("etapaAgendamentoRecursos");
    const etapaAula = el("schedulerLessonStage");
    const etapaRepeticao = el("etapaAgendamentoRepeticao");

    renderRecursosEtapaInicial();

    if (etapaRecursos) {
        etapaRecursos.hidden = estado?.currentStep !== 1;
    }
    if (etapaAula) {
        etapaAula.hidden = estado?.currentStep !== 2;
    }
    if (etapaRepeticao) {
        etapaRepeticao.hidden = !estado?.selectionReady || estado?.currentStep !== 3;
    }
}

function atualizarContextoRecursoAgendamento(state) {
    const recurso = obterRecursosSelecionadosAgendamento()[0] || null;
    const mobileCover = el("schedulerMobileResourceCover");
    const mobileName = el("schedulerMobileResourceName");
    const mobileAvailability = el("schedulerMobileResourceAvailability");
    const imagem = String(recurso?.imagem_capa || "").trim();
    const tituloEtapa = el("schedulerLessonStageTitle");
    const copyEtapa = el("schedulerLessonStageCopy");
    if (mobileCover) {
        mobileCover.style.backgroundImage = imagem ? `url("${imagem}")` : "";
        mobileCover.classList.toggle("has-image", Boolean(imagem));
    }
    if (mobileName) {
        const dataLocal = criarDataLocalPorIso(dataSelecionada);
        const diaSemana = dataLocal ? formatarDiaSemanaAgenda(dataLocal) : "";
        mobileName.innerText = [paraDataBr(dataSelecionada), diaSemana].filter(Boolean).join(" · ");
    }
    if (mobileAvailability) {
        const aulasDisponiveis = (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : [])
            .filter((item) => (
                aulaSuportaRecursosSelecionados(item, recurso ? [recurso] : [])
                && (
                    usuarioEhAdmin()
                    || Number(item.professor_id || 0) === Number(usuarioAtual?.id || 0)
                )
            ))
            .length;
        mobileAvailability.innerText = aulasDisponiveis === 1
            ? "1 aula disponível"
            : `${aulasDisponiveis} aulas disponíveis`;
    }
    if (tituloEtapa) {
        tituloEtapa.innerText = recurso?.nome || "Escolha as aulas";
    }
    if (copyEtapa) {
        const total = obterAulasSelecionadasAgendamento().length;
        copyEtapa.innerText = total > 0
            ? `${total} aula(s) selecionada(s). Marque quantas precisar.`
            : "Marque todas as aulas em que deseja utilizar este recurso.";
    }
}

function rolarParaEtapaAulaAgendamento() {
    const etapaAula = el("schedulerLessonStage");
    if (!etapaAula || etapaAula.hidden) {
        return;
    }

    window.requestAnimationFrame(() => {
        etapaAula.scrollIntoView({
            behavior: "smooth",
            block: "start",
            inline: "nearest"
        });
    });
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
    const tituloCompactoMobile = window.innerWidth <= 640;

    if (mesmoMes) {
        if (tituloCompactoMobile) {
            const mesTextoCurto = inicio.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "");
            return `${inicio.getDate()} a ${fim.getDate()} ${mesTextoCurto} ${inicio.getFullYear()}`;
        }
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
        return "Selecione uma aula disponivel na etapa 2 para liberar o formulario.";
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

function ordenarAulasAgendamento(aulas = []) {
    return [...aulas].sort((a, b) => {
        const faixaA = Number(a?.faixa_global || a?.faixaGlobal || 0);
        const faixaB = Number(b?.faixa_global || b?.faixaGlobal || 0);
        if (faixaA !== faixaB) {
            return faixaA - faixaB;
        }

        return compararTextoPtBr(
            textoPadraoDetalheReserva(a?.turma_nome || a?.turmaNome, ""),
            textoPadraoDetalheReserva(b?.turma_nome || b?.turmaNome, "")
        );
    });
}

function obterTituloAulaAgendamento(aula) {
    const numero = Number(aula?.aula_numero || aula?.aulaNumero || 0);
    const disciplina = textoPadraoDetalheReserva(aula?.disciplina_nome || aula?.disciplinaNome, "Aula planejada");
    return `${disciplina} • ${aulaLabel(numero)}`;
}

function obterResumoCurtoAulaAgendamento(aula) {
    return [
        textoPadraoDetalheReserva(aula?.turma_nome || aula?.turmaNome, "Turma não informada"),
        textoPadraoDetalheReserva(aula?.turno_nome || aula?.turnoNome || nomeTurnoExibicao(aula?.turno), "Turno não informado")
    ].join(" | ");
}

function obterAulasSelecionadasAgendamento() {
    return ordenarAulasAgendamento(
        (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : [])
            .filter((aula) => aulasAdicionaisAgendamento.has(chaveAulaAgendamento(aula)))
    );
}

function obterDetalhesAulaAgendamento(chave) {
    if (!detalhesAulasAgendamento[chave]) {
        detalhesAulasAgendamento[chave] = { tema: "", observacao: "" };
    }
    return detalhesAulasAgendamento[chave];
}

function atualizarResumoAulaSelecionada() {
    const titulo = obterTituloAulaSelecionada();
    const resumo = obterResumoAulaSelecionada();
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    const tituloDetalhes = aulasSelecionadas.length > 1
        ? `${aulasSelecionadas.length} aulas selecionadas`
        : titulo;
    const resumoDetalhes = aulasSelecionadas.length > 1
        ? aulasSelecionadas.map((aula) => `${obterTituloAulaAgendamento(aula)} | ${obterResumoCurtoAulaAgendamento(aula)}`).join(" | ")
        : resumo;

    if (el("tituloAulaSelecionada")) {
        el("tituloAulaSelecionada").innerText = titulo;
    }
    if (el("resumoAulaSelecionada")) {
        el("resumoAulaSelecionada").innerText = resumo;
    }
    if (el("tituloAulaSelecionadaRepeticao")) {
        el("tituloAulaSelecionadaRepeticao").innerText = titulo;
    }
    if (el("resumoAulaSelecionadaRepeticao")) {
        el("resumoAulaSelecionadaRepeticao").innerText = resumo;
    }
    if (el("tituloAulaSelecionadaDetalhes")) {
        el("tituloAulaSelecionadaDetalhes").innerText = tituloDetalhes;
    }
    if (el("resumoAulaSelecionadaDetalhes")) {
        el("resumoAulaSelecionadaDetalhes").innerText = resumoDetalhes;
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

function obterVagasRestantesRecurso(recurso, item = selecaoAulaAgendamento) {
    const recursoId = Number(recurso?.id || 0);
    const capacidade = Math.max(Number(recurso?.quantidade_itens || 1), 1);
    const reservasAtivas = obterReservasDaAulaSelecionada(item).filter(
        (reserva) => Number(reserva?.recurso_id || 0) === recursoId
    ).length;
    return Math.max(capacidade - reservasAtivas, 0);
}

function obterRecursosDisponiveisParaSelecao(item = selecaoAulaAgendamento) {
    return recursos.filter((recurso) => obterVagasRestantesRecurso(recurso, item) > 0);
}

function aulaSuportaRecursosSelecionados(item, recursosSelecionados = obterRecursosSelecionadosAgendamento()) {
    if (!item || !Array.isArray(recursosSelecionados) || recursosSelecionados.length === 0) {
        return false;
    }

    const recursosDisponiveis = new Set(
        obterRecursosDisponiveisParaSelecao(item).map((recurso) => Number(recurso.id || 0))
    );
    return recursosSelecionados.every((recurso) => recursosDisponiveis.has(Number(recurso.id || 0)));
}

function obterEstadoCompatibilidadeAulaAgendamento(item) {
    const recursosSelecionados = obterRecursosSelecionadosAgendamento();
    const recursosDisponiveis = item ? obterRecursosDisponiveisParaSelecao(item) : [];
    const idsDisponiveis = new Set(recursosDisponiveis.map((recurso) => Number(recurso.id || 0)));
    const recursosSelecionadosDisponiveis = recursosSelecionados.filter(
        (recurso) => idsDisponiveis.has(Number(recurso.id || 0))
    );

    return {
        recursosSelecionados,
        recursosDisponiveis,
        totalSelecionados: recursosSelecionados.length,
        selecionadosDisponiveis: recursosSelecionadosDisponiveis.length,
        suportaTodos: recursosSelecionados.length > 0
            && recursosSelecionadosDisponiveis.length === recursosSelecionados.length
    };
}

function alternarSelecaoRecursoAgendamento(recursoId) {
    const id = Number(recursoId || 0);
    if (!id) {
        return;
    }

    recursosSelecionadosAgendamento.clear();
    recursosSelecionadosAgendamento.add(id);
    limparSelecaoAulaAgendamento({ manterFormulario: false, limparRecursos: false });
    agendamentoWizard.currentStep = 2;
    sincronizarFiltroRecursoAgendaComSelecao(id);
    renderRecursosEtapaInicial();
    atualizarOpcoesRecursoPorSelecao();
    renderCalendario();
    renderReservasDia();
    renderAgendaDiaAulas();
    sincronizarWizardAgendamento({ scroll: true });
}

function atualizarOpcoesRecursoPorSelecao() {
    const container = el("recursoButtons");
    const resumo = el("resumoDisponibilidadeRecursos");

    const recursosDisponiveis = selecaoAulaAgendamento.chave
        ? obterRecursosDisponiveisParaSelecao()
        : [];
    if (selecaoAulaAgendamento.chave) {
        const idsDisponiveis = new Set(recursosDisponiveis.map((recurso) => Number(recurso.id)));

        Array.from(recursosSelecionadosAgendamento).forEach((recursoId) => {
            if (!idsDisponiveis.has(Number(recursoId))) {
                recursosSelecionadosAgendamento.delete(Number(recursoId));
            }
        });
    }

    if (container) {
        container.innerHTML = "";

        if (!selecaoAulaAgendamento.chave) {
            const vazio = document.createElement("p");
            vazio.className = "scheduler-resource-empty";
            vazio.innerText = "Selecione uma aula compativel na etapa 2.";
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
    }

    if (resumo) {
        if (!selecaoAulaAgendamento.chave) {
            resumo.innerText = "Selecione uma aula na etapa 2 para revisar a disponibilidade final dos recursos.";
        } else if (recursosDisponiveis.length === 0) {
            resumo.innerText = "Todos os recursos já estão ocupados neste horário ou não há recurso ativo cadastrado.";
        } else if (recursosSelecionadosAgendamento.size === 0) {
            resumo.innerText = `${recursosDisponiveis.length} recurso(s) livre(s) neste horário. Você pode selecionar mais de um.`;
        } else {
            resumo.innerText = `${recursosSelecionadosAgendamento.size} recurso(s) selecionado(s) para o agrupamento.`;
        }
    }

    renderAulasAdicionaisAgendamento();
    renderCamposDetalhesAulasAgendamento();
}

function alternarAulaAdicionalAgendamento(recursoId) {
    const id = Number(recursoId || 0);
    if (!id || id === Number(configuracaoAgendaDia.filtroRecursoId || 0)) {
        return;
    }

    if (recursosSelecionadosAgendamento.has(id)) {
        recursosSelecionadosAgendamento.delete(id);
    } else {
        recursosSelecionadosAgendamento.add(id);
    }

    renderAulasAdicionaisAgendamento();
    sincronizarWizardAgendamento();
}

function sincronizarRecursosAdicionaisComAulas() {
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    const recursoPrincipalId = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    Array.from(recursosSelecionadosAgendamento).forEach((recursoId) => {
        const id = Number(recursoId || 0);
        if (!id || id === recursoPrincipalId) {
            return;
        }
        const compativel = aulasSelecionadas.every((aula) => (
            obterRecursosDisponiveisParaSelecao(aula)
                .some((recurso) => Number(recurso.id) === id)
        ));
        if (!compativel) {
            recursosSelecionadosAgendamento.delete(id);
        }
    });
}

function renderAulasAdicionaisAgendamento() {
    const container = el("aulasAdicionaisAgendamento");
    const resumo = el("resumoAulasAdicionaisAgendamento");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    sincronizarRecursosAdicionaisComAulas();
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    const recursoPrincipalId = Number(configuracaoAgendaDia.filtroRecursoId || 0);
    const recursosCompativeis = recursos.filter((recurso) => {
        const recursoId = Number(recurso.id || 0);
        if (!recursoId || recursoId === recursoPrincipalId) {
            return false;
        }
        return aulasSelecionadas.every((aula) => (
            obterRecursosDisponiveisParaSelecao(aula)
                .some((item) => Number(item.id) === recursoId)
        ));
    });

    if (aulasSelecionadas.length === 0 || !recursoPrincipalId) {
        if (resumo) {
            resumo.innerText = "Selecione as aulas antes de adicionar outros recursos.";
        }
        return;
    }

    if (recursosCompativeis.length === 0) {
        if (resumo) {
            resumo.innerText = "Não há outro recurso livre em todas as aulas selecionadas.";
        }
        return;
    }

    recursosCompativeis.forEach((recurso) => {
        const recursoId = Number(recurso.id);
        const selecionada = recursosSelecionadosAgendamento.has(recursoId);

        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "scheduler-extra-lesson-option";
        botao.setAttribute("aria-pressed", selecionada ? "true" : "false");
        if (selecionada) {
            botao.classList.add("is-selected");
        }

        const imagem = document.createElement("span");
        imagem.className = "scheduler-extra-resource-cover";
        const imagemCapa = String(recurso.imagem_capa || "").trim();
        if (imagemCapa) {
            imagem.style.backgroundImage = `url("${imagemCapa}")`;
            imagem.classList.add("has-image");
        }

        const titulo = document.createElement("strong");
        titulo.innerText = textoPadraoDetalheReserva(recurso.nome, "Recurso");
        titulo.className = "scheduler-extra-lesson-title";

        const turmaInfo = document.createElement("span");
        turmaInfo.className = "scheduler-extra-lesson-class";
        turmaInfo.innerText = textoPadraoDetalheReserva(recurso.tipo, "Equipamento");

        const meta = document.createElement("span");
        meta.className = "scheduler-extra-lesson-meta";
        meta.innerText = obterResumoCapacidadeRecurso(recurso);

        const copy = document.createElement("span");
        copy.className = "scheduler-extra-resource-copy";
        copy.appendChild(titulo);
        copy.appendChild(turmaInfo);
        copy.appendChild(meta);
        botao.appendChild(imagem);
        botao.appendChild(copy);
        botao.addEventListener("click", () => alternarAulaAdicionalAgendamento(recursoId));
        container.appendChild(botao);
    });

    if (resumo) {
        const adicionais = Math.max(recursosSelecionadosAgendamento.size - 1, 0);
        resumo.innerText = adicionais > 0
            ? `${adicionais} recurso(s) adicional(is) selecionado(s).`
            : "Você pode seguir apenas com o recurso principal.";
    }
}

function renderCamposDetalhesAulasAgendamento() {
    const container = el("listaDetalhesAulasAgendamento");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();

    aulasSelecionadas.forEach((aula) => {
        const chave = chaveAulaAgendamento(aula);
        const detalhes = obterDetalhesAulaAgendamento(chave);

        const card = document.createElement("article");
        card.className = "scheduler-lesson-detail-card";

        const cabecalho = document.createElement("div");
        cabecalho.className = "scheduler-lesson-detail-header";

        const titulo = document.createElement("h3");
        titulo.innerText = obterTituloAulaAgendamento(aula);
        const meta = document.createElement("p");
        meta.className = "print-file-hint";
        meta.innerText = obterResumoCurtoAulaAgendamento(aula);

        cabecalho.appendChild(titulo);
        cabecalho.appendChild(meta);

        const grupoTema = document.createElement("article");
        grupoTema.className = "print-field-group";
        const labelTema = document.createElement("label");
        labelTema.setAttribute("for", `temaAulaReserva-${chave}`);
        labelTema.innerText = "Tema da aula";
        const inputTema = document.createElement("input");
        inputTema.id = `temaAulaReserva-${chave}`;
        inputTema.type = "text";
        inputTema.maxLength = 160;
        inputTema.required = true;
        inputTema.placeholder = "Ex.: Revisão de frações e lista de exercícios";
        inputTema.value = detalhes.tema || "";
        inputTema.addEventListener("input", () => {
            obterDetalhesAulaAgendamento(chave).tema = inputTema.value;
            sincronizarWizardAgendamento();
        });
        grupoTema.appendChild(labelTema);
        grupoTema.appendChild(inputTema);

        const grupoObs = document.createElement("article");
        grupoObs.className = "print-field-group";
        const labelObs = document.createElement("label");
        labelObs.setAttribute("for", `observacaoReserva-${chave}`);
        labelObs.innerText = "Observação";
        const inputObs = document.createElement("textarea");
        inputObs.id = `observacaoReserva-${chave}`;
        inputObs.rows = 3;
        inputObs.placeholder = "Se precisar deixar algum site aberto ou algum preparo específico, descreva aqui.";
        inputObs.value = detalhes.observacao || "";
        inputObs.addEventListener("input", () => {
            obterDetalhesAulaAgendamento(chave).observacao = inputObs.value;
            sincronizarWizardAgendamento();
        });
        grupoObs.appendChild(labelObs);
        grupoObs.appendChild(inputObs);

        card.appendChild(cabecalho);
        card.appendChild(grupoTema);
        card.appendChild(grupoObs);
        container.appendChild(card);
    });
}

function limparCamposFluxoAgendamento() {
    aulasAdicionaisAgendamento.clear();
    Object.keys(detalhesAulasAgendamento).forEach((chave) => {
        delete detalhesAulasAgendamento[chave];
    });
    const listaDetalhes = el("listaDetalhesAulasAgendamento");
    if (listaDetalhes) {
        listaDetalhes.innerHTML = "";
    }
}

function limparSelecaoAulaAgendamento({ manterFormulario = false, limparRecursos = false } = {}) {
    if (limparRecursos) {
        recursosSelecionadosAgendamento.clear();
    }
    sincronizarFiltroRecursoAgendaComSelecao();
    aulasAdicionaisAgendamento.clear();
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
    agendamentoWizard.currentStep = recursosSelecionadosAgendamento.size > 0 ? 2 : 1;
    if (!manterFormulario) {
        limparCamposFluxoAgendamento();
    }
    renderRecursosEtapaInicial();
    atualizarResumoAulaSelecionada();
    atualizarOpcoesRecursoPorSelecao();
    renderAulasAdicionaisAgendamento();
    renderCamposDetalhesAulasAgendamento();
}

function selecionarAulaParaAgendamento(item) {
    if (!item) {
        limparSelecaoAulaAgendamento({ limparRecursos: false });
        sincronizarWizardAgendamento();
        renderAgendaDiaAulas();
        return;
    }

    const chave = chaveAulaAgendamento(item);
    if (aulasAdicionaisAgendamento.has(chave)) {
        aulasAdicionaisAgendamento.delete(chave);
    } else {
        aulasAdicionaisAgendamento.clear();
        aulasAdicionaisAgendamento.add(chave);
    }

    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    const aulaReferencia = aulasSelecionadas[0] || null;
    if (aulaReferencia) {
        preencherSelecaoAulaAgendamento(aulaReferencia);
    } else {
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
    }

    agendamentoWizard.currentStep = 2;
    atualizarResumoAulaSelecionada();
    renderAulasAdicionaisAgendamento();
    renderCamposDetalhesAulasAgendamento();
    sincronizarWizardAgendamento();
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
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    const possuiSelecao = aulasSelecionadas.length > 0;
    const etapaRecursosConcluida = recursosSelecionados.length > 0;

    const aulasValidas = aulasSelecionadas.every((aula) => {
        const turmaAula = obterTurmaPorNome(aula.turma_nome || aula.turmaNome);
        const aulaNumero = Number(aula.aula_numero || aula.aulaNumero || 0);
        return Boolean(
            turmaAula
            && turmaAula.turno_valido
            && aulaNumero > 0
            && aulaNumero <= Number(turmaAula.aulas || 0)
        );
    });

    const etapaSelecaoConcluida = Boolean(possuiSelecao && data && aulasValidas);
    const detalhesAulas = aulasSelecionadas.map((aula) => {
        const chave = chaveAulaAgendamento(aula);
        const detalhes = obterDetalhesAulaAgendamento(chave);
        return {
            ...aula,
            chave,
            tema: String(detalhes.tema || "").trim(),
            observacao: String(detalhes.observacao || "").trim()
        };
    });
    const etapaDetalhesLiberada = Boolean(
        etapaSelecaoConcluida
        && detalhesAulas.length > 0
        && detalhesAulas.every((aula) => aula.tema)
    );
    let maxEtapa = 1;
    if (etapaRecursosConcluida) {
        maxEtapa = 2;
    }
    if (etapaSelecaoConcluida && etapaRecursosConcluida) {
        maxEtapa = etapaDetalhesLiberada ? 4 : 3;
    }

    const etapaAtual = Math.min(
        Math.max(Number(agendamentoWizard.currentStep || 1), 1),
        maxEtapa
    );

    return {
        hasResources: etapaRecursosConcluida,
        lessonStageVisible: true,
        hasSelection: possuiSelecao,
        selectionReady: etapaSelecaoConcluida,
        currentStep: etapaAtual,
        maxStep: maxEtapa,
        resourceStepReady: etapaRecursosConcluida,
        repeatStepReady: etapaSelecaoConcluida && etapaRecursosConcluida,
        detailsStepReady: etapaDetalhesLiberada,
        canSubmit: etapaDetalhesLiberada && !agendamentoWizard.submitting,
        selectedLessons: detalhesAulas,
        summary: {
            recurso: formatarResumoRecursosSelecionados(recursosSelecionados),
            data: data ? paraDataBr(data) : "Aguardando data",
            turma: possuiSelecao
                ? Array.from(new Set(
                    aulasSelecionadas.map((aula) => aula.turma_nome || aula.turmaNome)
                )).filter(Boolean).join(", ")
                : "Aguardando turmas",
            disciplina: selecaoAulaAgendamento.disciplinaNome || "Aguardando disciplina",
            professor: possuiSelecao
                ? Array.from(new Set(
                    aulasSelecionadas.map((aula) => aula.professor_nome || aula.professorNome)
                )).filter(Boolean).join(", ")
                : "Aguardando professor",
            aula: possuiSelecao
                ? `${aulasSelecionadas.length} aula(s) selecionada(s)`
                : "Aguardando aulas",
            aulasQuantidade: detalhesAulas.length > 0
                ? `${detalhesAulas.length} aula(s) com os mesmos recursos`
                : "Aguardando seleção",
            aulas: detalhesAulas
        }
    };
}

function atualizarResumoWizardAgendamento(state) {
    const resumo = state?.summary || {};
    atualizarResumoAulaSelecionada();

    if (el("resumoAgendamentoRecurso")) {
        el("resumoAgendamentoRecurso").innerText = resumo.recurso || "Aguardando seleção";
    }
    if (el("resumoAgendamentoTurma")) {
        el("resumoAgendamentoTurma").innerText = resumo.turma || "Aguardando turma";
    }
    if (el("resumoAgendamentoProfessor")) {
        el("resumoAgendamentoProfessor").innerText = resumo.professor || "Aguardando professor";
    }
    if (el("resumoAgendamentoAulasQuantidade")) {
        el("resumoAgendamentoAulasQuantidade").innerText = resumo.aulasQuantidade || "Aguardando seleção";
    }

    const listaAulas = el("resumoAgendamentoAulasLista");
    if (listaAulas) {
        listaAulas.innerHTML = "";
        const aulas = Array.isArray(resumo.aulas) ? resumo.aulas : [];
        aulas.forEach((aula) => {
            const card = document.createElement("article");
            card.className = "scheduler-summary-lesson-card";

            const titulo = document.createElement("h4");
            titulo.innerText = obterTituloAulaAgendamento(aula);
            const meta = document.createElement("p");
            meta.innerText = obterResumoCurtoAulaAgendamento(aula);
            const tema = document.createElement("p");
            tema.innerText = `Tema: ${aula.tema || "Aguardando tema"}`;

            card.appendChild(titulo);
            card.appendChild(meta);
            card.appendChild(tema);

            if (aula.observacao) {
                const observacao = document.createElement("p");
                observacao.innerText = `Observação: ${aula.observacao}`;
                card.appendChild(observacao);
            }

            listaAulas.appendChild(card);
        });
    }
}

function atualizarStepperAgendamento(state) {
    [
        ["stepperAgendamentoRecursos", 1],
        ["stepperAgendamentoAula", 2],
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
        if (isCurrent) {
            item.setAttribute("aria-current", "step");
        } else {
            item.removeAttribute("aria-current");
        }
    });
}

function renderEtapaAtualAgendamento(state) {
    atualizarEtapaPrimariaAgendamento(state);

    const flow = el("schedulerWizardFlow");
    if (flow) {
        flow.hidden = state?.currentStep < 3;
    }

    const currentStep = Number(state.currentStep || 1);
    const cards = {
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
    const btnContinuarRepeticao = el("btnContinuarAgendamentoRepeticao");
    const btnContinuarDetalhes = el("btnContinuarAgendamentoDetalhes");
    const btnAgendar = el("btnAgendar");
    const quantidadeRecursos = recursosSelecionadosAgendamento.size;
    const quantidadeAulas = obterAulasSelecionadasAgendamento().length || 1;
    const quantidadeReservas = quantidadeRecursos * quantidadeAulas;

    if (btnContinuarRepeticao) {
        btnContinuarRepeticao.disabled = !state.repeatStepReady;
    }
    if (btnContinuarDetalhes) {
        btnContinuarDetalhes.disabled = !state.detailsStepReady;
    }
    if (btnAgendar) {
        btnAgendar.disabled = !state.canSubmit;
        if (agendamentoWizard.submitting) {
            btnAgendar.innerText = quantidadeReservas > 1 ? "Confirmando reservas..." : "Confirmando reserva...";
        } else if (quantidadeReservas > 1) {
            btnAgendar.innerText = `Confirmar ${quantidadeReservas} reservas`;
        } else {
            btnAgendar.innerText = "Confirmar reserva";
        }
    }
}

function sincronizarWizardAgendamento({ scroll = false } = {}) {
    const state = obterEstadoWizardAgendamento();
    if (!state) {
        return null;
    }

    agendamentoWizard.currentStep = state.currentStep;
    atualizarResumoWizardAgendamento(state);
    atualizarContextoRecursoAgendamento(state);
    atualizarStepperAgendamento(state);
    renderEtapaAtualAgendamento(state);
    atualizarAcoesWizardAgendamento(state);

    if (scroll) {
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
    grupo.hidden = true;
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

    grupo.hidden = true;

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
        option.innerText = `${professor.nome}`;
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
    sincronizarFiltroRecursoAgendaComSelecao();
    renderRecursosEtapaInicial();
    atualizarOpcoesRecursoPorSelecao();
    renderAgendaDiaAulas();
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
        gradeAulas = Array.isArray(data.grade_aulas) ? data.grade_aulas : [];
        aulasGlobais = Array.isArray(data.aulas_globais) ? data.aulas_globais : [];

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
                        quantidade_estudantes: Number(turma?.quantidade_estudantes || 0),
                        aula_inicial: Number(turma?.aula_inicial || 0),
                        aula_final: Number(turma?.aula_final || 0),
                        aulas_disponiveis: Array.isArray(turma?.aulas_disponiveis)
                            ? turma.aulas_disponiveis
                            : []
                    };
                })
                .filter((turma) => Boolean(turma.nome))
            : [];
    } catch (err) {
        turnos = OPCAO_TURNOS_FALLBACK;
        gradeAulas = [];
        aulasGlobais = [];
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
    const aulasPorChave = new Map(
        (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : [])
            .map((aula) => [chaveAulaAgendamento(aula), aula])
    );
    Array.from(aulasAdicionaisAgendamento).forEach((chave) => {
        if (!aulasPorChave.has(chave)) {
            aulasAdicionaisAgendamento.delete(chave);
        }
    });

    const aulasSelecionadas = obterAulasSelecionadasAgendamento();
    if (aulasSelecionadas.length === 0) {
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
        atualizarResumoAulaSelecionada();
        atualizarOpcoesRecursoPorSelecao();
        return;
    }

    preencherSelecaoAulaAgendamento(aulasSelecionadas[0]);
    atualizarResumoAulaSelecionada();
    atualizarOpcoesRecursoPorSelecao();
}

function renderEstadoAulasDia(texto) {
    const lista = el("agendaDiaLista");
    if (!lista) {
        return;
    }

    lista.innerHTML = "";

    const estado = document.createElement("div");
    estado.className = "weekly-table-empty";
    estado.innerText = texto;
    lista.appendChild(estado);
}

async function carregarAulasProfessorDia() {
    const diaSemana = obterDiaSemanaApiPorData(dataSelecionada);
    const professorId = obterProfessorAgendaAtivoId();

    aulasProfessorDia = [];

    if (!["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"].includes(diaSemana)) {
        limparSelecaoAulaAgendamento({ manterFormulario: true, limparRecursos: false });
        return;
    }
    if (professorId <= 0) {
        limparSelecaoAulaAgendamento({ manterFormulario: true, limparRecursos: false });
        return;
    }

    const anoLetivo = Number(String(dataSelecionada || "").slice(0, 4));
    const params = new URLSearchParams({
        ano_letivo: String(anoLetivo),
        dia_semana: diaSemana,
        professor_id: String(professorId)
    });

    const res = await fetchComAuth(`/horario-escolar/registros?${params.toString()}`, { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar as aulas desta data.");
    }

    const body = await res.json();
    aulasProfessorDia = Array.isArray(body.itens)
        ? body.itens
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
    return itensVisuaisGradeAtivos();
}

function chaveCelulaAgendaDia(aula) {
    return String(Number(aula || 0));
}

function obterTurnoAulaPorFaixaGrade(faixaGlobal) {
    const faixa = Number(faixaGlobal || 0);
    if (!Number.isInteger(faixa) || faixa <= 0) {
        return null;
    }
    const aulaConfig = obterAulaGlobalPorNumero(faixa);
    if (!aulaConfig) {
        return null;
    }
    return {
        aula: Number(aulaConfig.aula_numero || 0),
        label: String(aulaConfig.label || aulaConfig.label_curta || "")
    };
}

function obterTurnoAulaGradeReserva(reserva) {
    const porFaixa = obterTurnoAulaPorFaixaGrade(faixaGlobalReserva(reserva));
    if (porFaixa) {
        return porFaixa;
    }

    const aula = Number(reserva?.aula || 0);
    if (!Number.isInteger(aula) || aula <= 0) {
        return null;
    }
    return { aula };
}

function mapearReservasDiaPorCelula() {
    const mapa = new Map();
    const filtroRecursoId = agendamentoWizard.currentStep === 1
        ? 0
        : Number(configuracaoAgendaDia.filtroRecursoId || 0);
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

        const chave = chaveCelulaAgendaDia(posicaoGrade.aula);
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

        const chave = chaveCelulaAgendaDia(posicaoGrade.aula);
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
    const selecionada = Boolean(
        aulaPrincipal
        && aulasAdicionaisAgendamento.has(chaveAulaAgendamento(aulaPrincipal))
    );

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
    obterLinhasAulasGradeSemanal().forEach((linhaGrade) => {
        if (String(linhaGrade?.tipo || "").toUpperCase() === "INTERVALO") {
            const linhaIntervalo = document.createElement("tr");
            linhaIntervalo.className = "weekly-turno-row";
            const thIntervalo = document.createElement("th");
            thIntervalo.colSpan = 2;
            thIntervalo.scope = "colgroup";
            thIntervalo.innerText = linhaGrade.label || linhaGrade.nome || "Intervalo";
            linhaIntervalo.appendChild(thIntervalo);
            tbody.appendChild(linhaIntervalo);
            return;
        }

        const aulaNumero = Number(linhaGrade.aula_numero || linhaGrade.aula || 0);
        const chave = chaveCelulaAgendaDia(aulaNumero);
        const aulasCelula = aulasPorCelula.get(chave) || [];
        const reservasCelula = reservasPorCelula.get(chave) || [];

        const tr = document.createElement("tr");

        const label = document.createElement("th");
        label.scope = "row";
        label.className = "weekly-aula-label";
        label.innerText = linhaGrade.label || aulaLabel(aulaNumero);
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

function abrirDetalhesReserva(reservaOuGrupo) {
    const grupoReservas = normalizarGrupoReservasDetalhe(reservaOuGrupo);
    const reserva = grupoReservas[0];

    if (!reserva) {
        return;
    }

    reservaDetalheAtual = {
        grupo: grupoReservas,
        principal: reserva
    };
    reservaCancelamentoPendenteId = 0;

    el("detalheReservaRecurso") && (el("detalheReservaRecurso").innerText = formatarTituloRecursosGrupo(grupoReservas));
    el("detalheReservaData") && (el("detalheReservaData").innerText = textoPadraoDetalheReserva(paraDataBr(reserva.data)));
    el("detalheReservaAula") && (el("detalheReservaAula").innerText = textoPadraoDetalheReserva(aulaLabel(numeroAulaReserva(reserva))));
    el("detalheReservaTurma") && (el("detalheReservaTurma").innerText = textoPadraoDetalheReserva(reserva.turma, "Turma não informada"));
    el("detalheReservaProfessor") && (el("detalheReservaProfessor").innerText = textoPadraoDetalheReserva(reserva.professor_nome, "Professor não informado"));
    el("detalheReservaTema") && (el("detalheReservaTema").innerText = textoPadraoDetalheReserva(reserva.tema_aula, "Tema não informado"));
    el("detalheReservaObservacao") && (el("detalheReservaObservacao").innerText = textoPadraoDetalheReserva(reserva.observacao, "Sem observação."));
    el("detalheReservaCriadoPor") && (el("detalheReservaCriadoPor").innerText = textoPadraoDetalheReserva(reserva.professor_nome, "Não informado"));
    el("detalheReservaStatus") && (el("detalheReservaStatus").innerText = String(reserva.status || "ATIVO").trim().toUpperCase() === "CANCELADO" ? "Cancelado" : "Ativo");

    const btnCancelar = el("btnAbrirConfirmacaoCancelamento");
    const algumCancelavel = grupoReservas.some((item) => reservaPodeSerCancelada(item));
    if (btnCancelar) {
        btnCancelar.hidden = true;
        btnCancelar.disabled = true;
        btnCancelar.dataset.reservaId = "";
    }

    const listaRecursos = el("detalheReservaRecursosLista");
    const secaoRecursos = el("detalheReservaRecursosSecao");
    if (listaRecursos && secaoRecursos) {
        listaRecursos.innerHTML = "";

        grupoReservas.forEach((item) => {
            const card = document.createElement("article");
            card.className = "scheduler-booking-resource-detail-card";

            const topo = document.createElement("div");
            topo.className = "scheduler-booking-resource-detail-top";

            const titulo = document.createElement("p");
            titulo.className = "scheduler-booking-resource-detail-title";
            titulo.innerText = textoPadraoDetalheReserva(item.recurso_nome, "Recurso não informado");
            topo.appendChild(titulo);

            const meta = document.createElement("p");
            meta.className = "scheduler-booking-resource-detail-meta";
            meta.innerText = `${nomeTurno(item.turno) || "Turno não informado"} | ${aulaLabel(numeroAulaReserva(item))}`;

            card.appendChild(topo);
            card.appendChild(meta);

            if (reservaPodeSerCancelada(item)) {
                const acoes = document.createElement("div");
                acoes.className = "scheduler-booking-resource-detail-actions";

                const botaoCancelar = document.createElement("button");
                botaoCancelar.type = "button";
                botaoCancelar.className = "scheduler-danger-link";
                botaoCancelar.innerText = "Cancelar este recurso";
                botaoCancelar.addEventListener("click", () => abrirConfirmacaoCancelamentoReserva(item.id));
                acoes.appendChild(botaoCancelar);

                card.appendChild(acoes);
            }

            listaRecursos.appendChild(card);
        });

        secaoRecursos.hidden = grupoReservas.length <= 1 && !algumCancelavel;
    }

    abrirPainelLateralAgendamento("painelDetalhesReservaAgendamento");
}

function abrirConfirmacaoCancelamentoReserva(reservaId) {
    const id = Number(reservaId || reservaDetalheAtual?.principal?.id || 0);
    if (!id) {
        return;
    }

    reservaCancelamentoPendenteId = id;
    const dialog = el("dialogCancelarReservaAgendamento");
    if (!dialog) {
        return;
    }

    elementoFocoAntesDialog = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    dialog.hidden = false;
    document.body.classList.add("scheduler-dialog-open");
    window.requestAnimationFrame(() => {
        el("btnFecharConfirmacaoCancelamento")?.focus();
    });
}

function fecharConfirmacaoCancelamentoReserva() {
    reservaCancelamentoPendenteId = 0;
    const dialog = el("dialogCancelarReservaAgendamento");
    if (!dialog) {
        return;
    }

    dialog.hidden = true;
    document.body.classList.remove("scheduler-dialog-open");
    elementoFocoAntesDialog?.focus();
    elementoFocoAntesDialog = null;
}

function manterFocoEmCamada(event, container) {
    if (event.key !== "Tab" || !container) {
        return;
    }

    const elementos = Array.from(container.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((item) => !item.hidden && item.getAttribute("aria-hidden") !== "true");

    if (elementos.length === 0) {
        event.preventDefault();
        container.focus();
        return;
    }

    const primeiro = elementos[0];
    const ultimo = elementos[elementos.length - 1];
    if (event.shiftKey && document.activeElement === primeiro) {
        event.preventDefault();
        ultimo.focus();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
        event.preventDefault();
        primeiro.focus();
    }
}

function criarTagStatusAgenda({
    selecionada = false,
    podeSelecionar = false,
    possuiReserva = false,
    possuiAula = false
} = {}) {
    const status = document.createElement("span");
    status.className = "scheduler-availability-badge";

    if (selecionada) {
        status.dataset.variant = "selected";
        status.innerText = "Selecionado";
    } else if (!possuiAula) {
        status.dataset.variant = "muted";
        status.innerText = "Sem aula";
    } else if (!podeSelecionar) {
        status.dataset.variant = "muted";
        status.innerText = possuiReserva ? "Ocupado" : "Indisponível";
    } else {
        status.dataset.variant = "available";
        status.innerText = "✓ Livre";
    }

    return status;
}

function criarBotaoReservarAgenda(aulaPrincipal, { selecionada = false, podeSelecionar = false } = {}) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "print-secondary-btn scheduler-outline-action";
    botao.disabled = !podeSelecionar;
    botao.innerText = selecionada ? "Aula selecionada" : "Escolher aula";
    botao.addEventListener("click", () => {
        if (!podeSelecionar || !aulaPrincipal) {
            return;
        }
        selecionarAulaParaAgendamento(aulaPrincipal);
    });
    return botao;
}

function criarObservacaoAgendaCompacta(texto) {
    const nota = document.createElement("p");
    nota.className = "scheduler-slot-helper-text";
    nota.innerText = texto;
    return nota;
}

function criarCardReservaAgendaDia(reservaOuGrupo) {
    const grupoReservas = normalizarGrupoReservasDetalhe(reservaOuGrupo);
    const reserva = grupoReservas[0];
    if (!reserva) {
        return document.createElement("div");
    }

    const card = document.createElement("article");
    card.className = "scheduler-booking-card";

    const conteudoPrincipal = document.createElement("div");
    conteudoPrincipal.className = "scheduler-booking-card-content";

    const titulo = document.createElement("h4");
    titulo.className = "scheduler-booking-card-title";
    titulo.innerText = formatarTituloRecursosGrupo(grupoReservas);

    const contexto = document.createElement("p");
    contexto.className = "scheduler-booking-card-meta";
    contexto.innerText = [
        textoPadraoDetalheReserva(reserva.turma, "Turma não informada"),
        textoPadraoDetalheReserva(`${reserva.professor_nome.split(" ")[0]}`, "Professor não informado")
    ].join(" | ");

    conteudoPrincipal.appendChild(titulo);
    conteudoPrincipal.appendChild(contexto);

    card.appendChild(conteudoPrincipal);

    const acoes = document.createElement("div");
    acoes.className = "scheduler-booking-card-actions";

    const botaoDetalhes = document.createElement("button");
    botaoDetalhes.type = "button";
    botaoDetalhes.className = "print-secondary-btn scheduler-inline-details-btn";
    botaoDetalhes.innerText = "Ver detalhes";
    botaoDetalhes.addEventListener("click", () => abrirDetalhesReserva(grupoReservas));

    acoes.appendChild(botaoDetalhes);
    card.appendChild(acoes);

    return card;
}

function criarLinhaAgendaCompacta({
    professor = null,
    aulaPrincipal = null,
    reservasCelula = []
} = {}) {
    const linha = document.createElement("div");
    linha.className = "scheduler-slot-compact-line";

    const compatibilidade = aulaPrincipal
        ? obterEstadoCompatibilidadeAulaAgendamento({
            data: aulaPrincipal.data,
            faixaGlobal: Number(aulaPrincipal.faixa_global || 0)
        })
        : {
            recursosSelecionados: [],
            recursosDisponiveis: [],
            totalSelecionados: 0,
            selecionadosDisponiveis: 0,
            suportaTodos: false
        };
    const recursosDisponiveis = compatibilidade.recursosDisponiveis;
    const selecionada = Boolean(
        aulaPrincipal
        && aulasAdicionaisAgendamento.has(chaveAulaAgendamento(aulaPrincipal))
    );
    const possuiAula = Boolean(aulaPrincipal);
    const totalRecursosSelecionados = compatibilidade.totalSelecionados;
    let podeSelecionar = Boolean(
        professor
        && possuiAula
        && totalRecursosSelecionados > 0
        && compatibilidade.suportaTodos
    );
    let statusTexto = totalRecursosSelecionados > 1
        ? `${totalRecursosSelecionados} compativeis`
        : "Compativel";

    if (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0) {
        podeSelecionar = false;
    }

    if (!professor) {
        statusTexto = "Selecione um professor";
    } else if (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0) {
        statusTexto = "Sem aula registrada";
    } else if (!possuiAula) {
        statusTexto = "Sem aula registrada";
    } else if (totalRecursosSelecionados === 0) {
        statusTexto = "Escolha um recurso";
    } else if (!compatibilidade.suportaTodos) {
        statusTexto = compatibilidade.selecionadosDisponiveis > 0
            ? `${compatibilidade.selecionadosDisponiveis}/${totalRecursosSelecionados} disponiveis`
            : "Indisponivel";
    }

    const copy = document.createElement("div");
    copy.className = "scheduler-slot-compact-copy";

    if (aulaPrincipal) {
        const detalhesAula = document.createElement("div");
        detalhesAula.className = "scheduler-slot-class-details";

        const disciplina = document.createElement("span");
        disciplina.innerText = textoPadraoDetalheReserva(
            aulaPrincipal.disciplina_nome || aulaPrincipal.disciplinaNome,
            "Aula planejada"
        );

        const turma = document.createElement("span");
        turma.innerText = textoPadraoDetalheReserva(
            aulaPrincipal.turma_nome || aulaPrincipal.turmaNome,
            "Turma não informada"
        );

        detalhesAula.appendChild(disciplina);
        detalhesAula.appendChild(turma);
        copy.appendChild(detalhesAula);
    }

    if (!professor) {
        copy.appendChild(criarObservacaoAgendaCompacta("Selecione um professor para ver a agenda."));
    } else if (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0) {
        copy.appendChild(criarObservacaoAgendaCompacta("Sem aula."));
    } else if (!possuiAula) {
        copy.appendChild(criarObservacaoAgendaCompacta("Sem aula."));
    } else if (totalRecursosSelecionados === 0) {
        copy.appendChild(criarObservacaoAgendaCompacta("Escolha um recurso na etapa 1 para habilitar a aula."));
    } else if (!compatibilidade.suportaTodos) {
        copy.appendChild(criarObservacaoAgendaCompacta(
            `${compatibilidade.selecionadosDisponiveis} de ${totalRecursosSelecionados} recurso(s) escolhido(s) estao livres neste horario.`
        ));
    } else if (reservasCelula.length > 0) {
        copy.appendChild(criarObservacaoAgendaCompacta(
            `${totalRecursosSelecionados} recurso(s) escolhido(s) disponiveis e ${reservasCelula.length} reserva(s) ja registrada(s) neste horario.`
        ));
    } else {
        copy.appendChild(criarObservacaoAgendaCompacta(
            `${totalRecursosSelecionados} recurso(s) escolhido(s) disponiveis para esta aula.`
        ));
    }

    const statusCompacto = criarTagStatusAgenda({
        selecionada,
        podeSelecionar,
        possuiReserva: reservasCelula.length > 0,
        possuiAula
    });
    statusCompacto.innerText = selecionada ? "Selecionado" : statusTexto;
    copy.appendChild(statusCompacto);

    linha.appendChild(copy);
    linha.appendChild(criarBotaoReservarAgenda(aulaPrincipal, { selecionada, podeSelecionar }));

    return linha;
}

function criarLinhaAgendaDia({
    linhaGrade,
    aula: aulaPrincipal = null,
    reservasCelula = []
} = {}) {
    const linha = document.createElement("label");
    linha.className = "scheduler-lesson-option-row";
    const selecionada = Boolean(
        aulaPrincipal
        && aulasAdicionaisAgendamento.has(chaveAulaAgendamento(aulaPrincipal))
    );
    const professorLogadoId = Number(usuarioAtual?.id || 0);
    const professorAulaId = Number(aulaPrincipal?.professor_id || 0);
    const recursoPrincipal = recursos.find(
        (recurso) => Number(recurso.id) === Number(configuracaoAgendaDia.filtroRecursoId || 0)
    );
    const recursoDisponivel = aulaSuportaRecursosSelecionados(
        aulaPrincipal,
        recursoPrincipal ? [recursoPrincipal] : []
    );
    const podeSelecionar = Boolean(
        aulaPrincipal
        && recursoDisponivel
        && (usuarioEhAdmin() || (professorLogadoId > 0 && professorLogadoId === professorAulaId))
    );

    if (selecionada) {
        linha.classList.add("is-selected");
    }
    if (!podeSelecionar) {
        linha.classList.add("is-disabled");
    }

    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "aulasAgendamento";
    radio.className = "scheduler-lesson-radio";
    radio.checked = Boolean(selecionada);
    radio.disabled = !podeSelecionar;
    const aulaNumeroLinha = Number(linhaGrade.aula_numero || linhaGrade.aula || 0);
    const aulaRotuloLinha = String(
        linhaGrade.label_curta
        || linhaGrade.nome
        || aulaLabel(aulaNumeroLinha)
    );
    radio.setAttribute("aria-label", `${selecionada ? "Remover" : "Selecionar"} ${aulaRotuloLinha}`);
    radio.addEventListener("change", () => {
        if (aulaPrincipal) {
            selecionarAulaParaAgendamento(aulaPrincipal);
        }
    });

    const aula = document.createElement("strong");
    aula.className = "scheduler-lesson-list-period";
    aula.innerText = aulaRotuloLinha;

    const horarioInicio = String(linhaGrade?.horario_inicio || aulaPrincipal?.horario_inicio || "").trim();
    const horarioFim = String(linhaGrade?.horario_fim || aulaPrincipal?.horario_fim || "").trim();
    const horario = document.createElement("span");
    horario.className = "scheduler-lesson-list-time";
    horario.innerText = horarioInicio && horarioFim
        ? `${horarioInicio} - ${horarioFim}`
        : "Horário não informado";

    const turmaNome = textoPadraoDetalheReserva(
        aulaPrincipal?.turma_nome || aulaPrincipal?.turmaNome,
        "Turma não informada"
    );
    const disciplinaNome = textoPadraoDetalheReserva(
        aulaPrincipal?.disciplina_nome || aulaPrincipal?.disciplinaNome,
        "Aula planejada"
    );

    const disciplina = document.createElement("span");
    disciplina.className = "scheduler-lesson-list-subject";
    disciplina.innerText = disciplinaNome;

    const turma = document.createElement("span");
    turma.className = "scheduler-lesson-list-class";
    turma.innerText = turmaNome;

    linha.appendChild(radio);
    linha.appendChild(aula);
    linha.appendChild(horario);
    linha.appendChild(disciplina);
    linha.appendChild(turma);
    return linha;
}

function renderAgendaDiaAulas() {
    const lista = el("agendaDiaLista");
    const subtitulo = el("subtituloAgendaDia");

    if (!lista || !subtitulo) {
        return;
    }

    const diaSemana = obterDiaSemanaApiPorData(dataSelecionada);
    const professor = obterProfessorAgendaAtivo();
    const subtituloPartes = [
        paraDataBr(dataSelecionada),
        professor?.nome || "Selecione um professor"
    ];
    if (!Array.isArray(aulasProfessorDia) || aulasProfessorDia.length === 0) {
        subtituloPartes.push("sem aulas registradas");
    }
    subtitulo.innerText = subtituloPartes.join(" | ");

    if (!["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"].includes(diaSemana)) {
        renderEstadoAulasDia("A agenda por aula está disponível apenas para dias letivos.");
        return;
    }
    if (!professor) {
        renderEstadoAulasDia("Selecione um professor para visualizar as aulas do dia.");
        return;
    }

    const reservasPorCelula = mapearReservasDiaPorCelula();
    const aulasPorPeriodo = new Map([
        ["MATUTINO", []],
        ["VESPERTINO", []]
    ]);
    (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : []).forEach((aula) => {
        const periodo = periodoAulaPorFaixa(
            Number(aula.faixa_global || aula.aula_numero || 0),
            aula.turno
        );
        aulasPorPeriodo.get(periodo)?.push(aula);
    });
    lista.innerHTML = "";

    [["MATUTINO", 5], ["VESPERTINO", 6]].forEach(([periodo, limite]) => {
        const aulasPeriodo = (aulasPorPeriodo.get(periodo) || [])
            .sort((a, b) => Number(a.faixa_global || 0) - Number(b.faixa_global || 0))
            .slice(0, limite);
        if (aulasPeriodo.length === 0) {
            return;
        }

        const secao = document.createElement("section");
        secao.className = "scheduler-shift-section";

        const cabecalho = document.createElement("header");
        cabecalho.className = "scheduler-shift-header";

        const tituloSecao = document.createElement("h4");
        tituloSecao.innerText = nomePeriodoAgendamento(periodo);
        cabecalho.appendChild(tituloSecao);

        const colunas = document.createElement("div");
        colunas.className = "scheduler-lesson-list-columns";
        ["Aula", "Horário", "Disciplina", "Turma"].forEach((texto) => {
            const coluna = document.createElement("span");
            coluna.innerText = texto;
            colunas.appendChild(coluna);
        });
        cabecalho.appendChild(colunas);
        secao.appendChild(cabecalho);

        const corpoGrade = document.createElement("div");
        corpoGrade.className = "scheduler-shift-slots";

        aulasPeriodo.forEach((aula) => {
            const aulaNumero = Number(aula.faixa_global || aula.aula_numero || 0);
            const linhaGrade = obterAulaGlobalPorNumero(aulaNumero) || aula;
            const chave = chaveCelulaAgendaDia(aulaNumero);
            corpoGrade.appendChild(criarLinhaAgendaDia({
                linhaGrade,
                aula,
                reservasCelula: reservasPorCelula.get(chave) || []
            }));
        });
        secao.appendChild(corpoGrade);
        lista.appendChild(secao);
    });

    if (!lista.querySelector(".scheduler-lesson-option-row")) {
        renderEstadoAulasDia("Nenhuma aula registrada na data selecionada.");
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
    titulo.innerText = `${textoPadraoDetalheReserva(reserva.recurso_nome, "Recurso não informado")} | ${aulaLabel(aulaExibicao || reserva.aula)}`;
    li.appendChild(titulo);

    if (exibirProfessor) {
        const professor = document.createElement("p");
        professor.className = "booking-professor";
        professor.innerText = `Professor(a): ${textoPadraoDetalheReserva(reserva.professor_nome, "Não informado")}`;
        li.appendChild(professor);
    }

    const detalheTurma = document.createElement("p");
    detalheTurma.className = "booking-detail";
    detalheTurma.innerText = `Turma: ${textoPadraoDetalheReserva(reserva.turma, "Não informada")} | ${nomeTurno(reserva.turno) || "Turno não informado"}`;
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

    const acoes = document.createElement("div");
    acoes.className = "booking-item-actions";

    const btnDetalhes = document.createElement("button");
    btnDetalhes.type = "button";
    btnDetalhes.className = "print-secondary-btn booking-details-btn";
    btnDetalhes.innerText = "Ver detalhes";
    btnDetalhes.addEventListener("click", () => abrirDetalhesReserva(reserva));
    acoes.appendChild(btnDetalhes);

    if (permitirCancelar) {
        const nota = document.createElement("span");
        nota.className = "booking-item-action-note";
        nota.innerText = "Cancelamento disponível nos detalhes.";
        acoes.appendChild(nota);
    }

    li.appendChild(acoes);
    return li;
}

async function cancelarReserva(idReserva = 0) {
    const id = Number(idReserva || reservaCancelamentoPendenteId || 0);
    if (!id) {
        return;
    }

    const res = await fetchComAuth(`/agendamento/reservas/${id}/cancelar`, {
        method: "POST",
        headers
    });

    const data = await res.json();
    if (!res.ok) {
        setMensagem(data.detail || "Não foi possível cancelar.", "erro");
        return;
    }

    fecharConfirmacaoCancelamentoReserva();
    fecharPainelLateralAgendamento("painelDetalhesReservaAgendamento");
    reservaDetalheAtual = null;
    setMensagem("Reserva cancelada com sucesso.");
    await atualizarTelaAgendamento();
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
        botao.appendChild(diaSemana);
        botao.appendChild(numero);
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
        const reservasDia = filtrarReservasPorRecursoEmFoco(
            reservasMes.filter((item) => item.data === dataIso)
        );

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
    const recursoEmFoco = obterRecursoEmFocoAgenda();
    el("tituloDia").innerText = recursoEmFoco
        ? `Reservas de ${paraDataBr(dataSelecionada)} | ${textoPadraoDetalheReserva(recursoEmFoco.nome, "Recurso")}`
        : `Reservas de ${paraDataBr(dataSelecionada)}`;

    const lista = el("listaReservasDia");
    const reservasDia = filtrarReservasPorRecursoEmFoco(
        reservasMes.filter((item) => item.data === dataSelecionada)
    );

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
        recursoEmFoco
            ? `Sem reservas desse recurso em ${paraDataBr(dataSelecionada)}.`
            : "Sem reservas nessa data."
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
        setMensagem("Selecione ao menos uma aula para iniciar o agendamento.", "erro");
        return;
    }

    const recursosSelecionados = obterRecursosSelecionadosAgendamento();
    const data = selecaoAulaAgendamento.data || el("dataReserva").value;
    const professorIdSelecionado = Number(
        selecaoAulaAgendamento.professorId || obterProfessorAgendaAtivoId() || 0
    );
    const aulasSelecionadas = obterAulasSelecionadasAgendamento();

    if (recursosSelecionados.length === 0 || !data || aulasSelecionadas.length === 0) {
        setMensagem("Selecione as aulas, ao menos um recurso e preencha os detalhes do agendamento.", "erro");
        return;
    }

    if (usuarioEhAdmin() && !professorIdSelecionado) {
        setMensagem("Selecione o professor solicitante do agendamento.", "erro");
        return;
    }

    const aulasParaEnvio = [];
    for (const aula of aulasSelecionadas) {
        const chave = chaveAulaAgendamento(aula);
        const detalhes = obterDetalhesAulaAgendamento(chave);
        const temaAula = String(detalhes.tema || "").trim();
        const observacao = String(detalhes.observacao || "").trim();
        const turmaNome = String(aula.turma_nome || aula.turmaNome || selecaoAulaAgendamento.turmaNome || "").trim();
        const turma = obterTurmaPorNome(turmaNome);
        const aulaNumero = Number(aula.aula_numero || aula.aulaNumero || 0);

        if (!turma || !turma.turno_valido || Number(turma.aulas) <= 0) {
            setMensagem(`A turma ${turmaNome || "selecionada"} está sem turno válido. Atualize no painel admin.`, "erro");
            return;
        }

        if (!temaAula) {
            setMensagem(`Informe o tema da ${obterTituloAulaAgendamento(aula)}.`, "erro");
            return;
        }

        const aulasPermitidas = new Set(
            (Array.isArray(turma.aulas_disponiveis) ? turma.aulas_disponiveis : [])
                .map((item) => Number(item?.aula_numero || 0))
                .filter((numero) => numero > 0)
        );
        if (!Number.isInteger(aulaNumero) || aulaNumero < 1 || !aulasPermitidas.has(aulaNumero)) {
            setMensagem(`A aula ${obterTituloAulaAgendamento(aula)} está fora da janela configurada para a turma.`, "erro");
            return;
        }

        const payloadBase = {
            data,
            aula: String(aulaNumero),
            turma: turmaNome,
            tema_aula: temaAula,
            observacao
        };
        if (usuarioEhAdmin()) {
            payloadBase.professor_id = Number(
                aula.professor_id || aula.professorId || professorIdSelecionado
            );
        }

        aulasParaEnvio.push({
            aula,
            titulo: obterTituloAulaAgendamento(aula),
            payloadBase
        });
    }

    definirEstadoEnvioAgendamento(true);

    try {
        const sucessos = [];
        const falhas = [];

        for (const aulaItem of aulasParaEnvio) {
            for (const recurso of recursosSelecionados) {
                const payload = {
                    ...aulaItem.payloadBase,
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
                        aula: aulaItem.titulo,
                        mensagem: body.detail || `Não foi possível agendar ${recurso.nome}.`
                    });
                    continue;
                }

                sucessos.push({ recurso, aula: aulaItem.titulo, body });
            }
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
            limparSelecaoAulaAgendamento({ limparRecursos: true });
            renderAgendaDiaAulas();
            sincronizarWizardAgendamento();
            return;
        }

        agendamentoWizard.currentStep = 3;
        sincronizarWizardAgendamento();
        const detalheFalhas = falhas
            .slice(0, 2)
            .map((item) => `${item.aula} - ${item.recurso.nome}: ${item.mensagem}`)
            .join(" | ");
        const resumoFalhas = falhas.length > 2
            ? `${detalheFalhas} | +${falhas.length - 2} falha(s)`
            : detalheFalhas;
        setMensagem(
            `${sucessos.length} reserva(s) confirmada(s), mas ${falhas.length} falharam. ${resumoFalhas}`,
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
    el("btnAbrirCalendarioGeralPagina")?.addEventListener("click", () => {
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
    el("btnFecharDetalhesReserva")?.addEventListener("click", () => {
        fecharPainelLateralAgendamento("painelDetalhesReservaAgendamento");
    });
    document.querySelectorAll("[data-close-scheduler-drawer='true']").forEach((elemento) => {
        elemento.addEventListener("click", () => {
            fecharPainelLateralAgendamento();
        });
    });
    el("btnAbrirConfirmacaoCancelamento")?.addEventListener("click", () => {
        abrirConfirmacaoCancelamentoReserva(el("btnAbrirConfirmacaoCancelamento")?.dataset.reservaId);
    });
    el("btnFecharConfirmacaoCancelamento")?.addEventListener("click", () => {
        fecharConfirmacaoCancelamentoReserva();
    });
    el("btnConfirmarCancelamentoReserva")?.addEventListener("click", () => {
        cancelarReserva();
    });
    el("dialogCancelarReservaAgendamento")?.addEventListener("click", (event) => {
        if (event.target === el("dialogCancelarReservaAgendamento") || event.target === el("dialogCancelarReservaAgendamento")?.firstElementChild) {
            fecharConfirmacaoCancelamentoReserva();
        }
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
        limparSelecaoAulaAgendamento({ manterFormulario: true, limparRecursos: false });
        try {
            await carregarAulasProfessorDia();
        } catch (err) {
            setMensagem(err.message || "Não foi possível carregar as aulas do professor.", "erro");
        }
        renderAgendaDiaAulas();
        sincronizarWizardAgendamento();
    });
    el("btnVoltarAgendamentoRepeticao").addEventListener("click", () => {
        agendamentoWizard.currentStep = 1;
        sincronizarWizardAgendamento({ scroll: true });
    });
    el("btnContinuarAgendamentoRepeticao").addEventListener("click", () => {
        if (!selecaoAulaAgendamento.chave) {
            setMensagem("Selecione uma aula disponível para continuar.", "erro");
            return;
        }
        renderCamposDetalhesAulasAgendamento();
        irParaEtapaAgendamento(3);
    });
    el("btnVoltarAgendamentoDetalhes").addEventListener("click", () => irParaEtapaAgendamento(2));
    el("btnContinuarAgendamentoDetalhes").addEventListener("click", () => irParaEtapaAgendamento(4));
    el("btnVoltarAgendamentoResumo").addEventListener("click", () => irParaEtapaAgendamento(3));

    registrarControlesOrdenacao();
    el("btnAgendar").addEventListener("click", agendarRecurso);

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            const dialog = el("dialogCancelarReservaAgendamento");
            if (dialog && !dialog.hidden) {
                fecharConfirmacaoCancelamentoReserva();
                return;
            }
            fecharPainelLateralAgendamento();
            return;
        }

        const dialog = el("dialogCancelarReservaAgendamento");
        if (dialog && !dialog.hidden) {
            manterFocoEmCamada(event, dialog.querySelector("[role='dialog']"));
            return;
        }

        const drawerAberto = document.querySelector(".scheduler-side-drawer.is-open .scheduler-side-panel");
        manterFocoEmCamada(event, drawerAberto);
    });

    window.addEventListener("resize", () => {
        renderSemanaAgendamento();
    });
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
    titulo.innerText = `${textoPadraoDetalheReserva(reserva.recurso_nome, "Recurso não informado")} | ${aulaLabel(aulaExibicao || reserva.aula)}`;
    li.appendChild(titulo);

    if (exibirProfessor) {
        const professor = document.createElement("p");
        professor.className = "booking-professor";
        professor.innerText = `Professor(a): ${textoPadraoDetalheReserva(reserva.professor_nome, "Não informado")}`;
        li.appendChild(professor);
    }

    const detalheTurma = document.createElement("p");
    detalheTurma.className = "booking-detail";
    detalheTurma.innerText = `Turma: ${textoPadraoDetalheReserva(reserva.turma, "Não informada")} | ${nomeTurno(reserva.turno) || "Turno não informado"}`;
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

    const acoes = document.createElement("div");
    acoes.className = "booking-item-actions";

    const btnDetalhes = document.createElement("button");
    btnDetalhes.type = "button";
    btnDetalhes.className = "print-secondary-btn booking-details-btn";
    btnDetalhes.innerText = "Ver detalhes";
    btnDetalhes.addEventListener("click", () => abrirDetalhesReserva(reserva));
    acoes.appendChild(btnDetalhes);

    if (permitirCancelar) {
        const nota = document.createElement("span");
        nota.className = "booking-item-action-note";
        nota.innerText = "Cancelamento disponível nos detalhes.";
        acoes.appendChild(nota);
    }

    li.appendChild(acoes);
    return li;
}

async function cancelarReserva(idReserva = 0) {
    const id = Number(idReserva || reservaCancelamentoPendenteId || 0);
    if (!id) {
        return;
    }

    const res = await fetchComAuth(`/agendamento/reservas/${id}/cancelar`, {
        method: "POST",
        headers
    });

    const data = await res.json();
    if (!res.ok) {
        setMensagem(data.detail || "Não foi possível cancelar.", "erro");
        return;
    }

    fecharConfirmacaoCancelamentoReserva();
    fecharPainelLateralAgendamento("painelDetalhesReservaAgendamento");
    reservaDetalheAtual = null;
    setMensagem("Reserva cancelada com sucesso.");
    await atualizarTelaAgendamento();
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
