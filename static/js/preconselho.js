const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    encerrarSessao,
    modulosPermitidos,
    usuarioEhProfessor,
} = window.AppAuth;
const { fetchComAuth, obterMensagemErroResposta } = window.AppApi;
const { escaparHtml } = window.AppFormat;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const headersJson = criarHeadersJsonAuth(token);

const CATEGORIAS_MOTIVO = [
    { id: "avaliacao", nome: "Avaliação" },
    { id: "participacao", nome: "Participação" },
    { id: "comportamento", nome: "Comportamento" },
    { id: "frequencia", nome: "Frequência" },
    { id: "organizacao_estudo", nome: "Organização e estudo" },
    { id: "dificuldades_pedagogicas", nome: "Dificuldades pedagógicas" }
];
const TURNO_LABEL = {
    MATUTINO: "Matutino",
    VESPERTINO: "Vespertino",
    VESPERTINO_EM: "Vespertino E.M.",
    INTEGRAL: "Período integral"
};

let usuarioAtual = null;
let contextoAtual = null;
let abaAtiva = "";
let timerPreviewDocente = null;
let ultimoElementoFocadoModal = null;

const estadoDocente = {
    periodoId: null,
    combos: [],
    turmaId: null,
    disciplinaId: null,
    estudantes: [],
    registros: [],
    estudanteId: null
};

const estadoConsolidacao = {
    dados: null
};

const estadoRelatorio = {
    dados: null,
    turmasExpandidas: new Set()
};

function limparMensagem(id) {
    definirMensagem(id, "", false);
}

function definirMensagem(id, texto, erro = false) {
    const alvo = el(id);
    if (!alvo) {
        return;
    }

    alvo.textContent = texto || "";
    alvo.dataset.state = erro ? "erro" : "ok";
}

function criarEstadoVazio(mensagem) {
    return `<li class="pcpi-empty">${escaparHtml(mensagem)}</li>`;
}

function rotuloCategoria(categoria) {
    const item = CATEGORIAS_MOTIVO.find((entry) => entry.id === categoria);
    return item ? item.nome : String(categoria || "");
}

function rotuloNivelAtencao(nivel) {
    const niveis = Array.isArray(contextoAtual?.niveis_atencao) ? contextoAtual.niveis_atencao : [];
    const encontrado = niveis.find((item) => String(item.id || "") === String(nivel || ""));
    return encontrado ? String(encontrado.nome || encontrado.id) : "";
}

function statusPeriodoClasse(status) {
    return String(status || "").trim().toUpperCase() === "ABERTO" ? "status-aberto" : "status-fechado";
}

function rotuloStatusPeriodo(status) {
    return String(status || "").trim().toUpperCase() === "ABERTO" ? "Aberto" : "Fechado";
}

function nomeTurno(turno) {
    return TURNO_LABEL[turno] || turno || "Não informado";
}

function formatarDataBr(valor) {
    const texto = String(valor || "").trim();
    if (!texto || !texto.includes("-")) {
        return texto;
    }
    const [ano, mes, dia] = texto.split("-");
    if (!ano || !mes || !dia) {
        return texto;
    }
    return `${dia}/${mes}/${ano}`;
}

function rotuloPeriodo(periodo = {}) {
    return String(periodo.nome || "").trim() || `${Number(periodo.etapa || 0)}º Bimestre ${Number(periodo.ano_letivo || 0)}`;
}

function preencherSelect(select, itens, obterValor, obterRotulo, placeholder, opcoes = {}) {
    if (!select) {
        return;
    }

    const permitirVazio = opcoes.permitirVazio !== false;
    const valorVazio = Object.prototype.hasOwnProperty.call(opcoes, "valorVazio") ? opcoes.valorVazio : "";
    const valorSelecionado = Object.prototype.hasOwnProperty.call(opcoes, "valorSelecionado") ? String(opcoes.valorSelecionado ?? "") : String(select.value || "");

    select.innerHTML = "";

    if (permitirVazio) {
        const optionPlaceholder = document.createElement("option");
        optionPlaceholder.value = String(valorVazio);
        optionPlaceholder.textContent = placeholder;
        select.appendChild(optionPlaceholder);
    }

    (itens || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(obterValor(item));
        option.textContent = obterRotulo(item);
        select.appendChild(option);
    });

    if (Array.from(select.options).some((option) => option.value === valorSelecionado)) {
        select.value = valorSelecionado;
    } else if (select.options.length > 0) {
        select.selectedIndex = 0;
    }

    select.disabled = !Array.isArray(itens) || itens.length === 0;
}

function obterPrimeiroNome() {
    return String(usuarioAtual?.nome || "").trim().split(" ")[0] || "Usuário";
}

function obterPeriodos() {
    return Array.isArray(contextoAtual?.periodos) ? contextoAtual.periodos : [];
}

function obterMotivosContexto() {
    return Array.isArray(contextoAtual?.motivos) ? contextoAtual.motivos : [];
}

function periodoDocenteAtual() {
    return obterPeriodos().find((item) => Number(item.id) === Number(estadoDocente.periodoId)) || null;
}

function periodoTemRav(periodo = periodoDocenteAtual()) {
    return Boolean(periodo?.tem_rav);
}

function comboDocenteAtual() {
    return estadoDocente.combos.find((item) =>
        Number(item.turma_id) === Number(estadoDocente.turmaId) &&
        Number(item.disciplina_id) === Number(estadoDocente.disciplinaId)
    ) || null;
}

function estudanteDocenteAtual() {
    return estadoDocente.estudantes.find((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId)) || null;
}

function registroDocenteAtual() {
    return estadoDocente.registros.find((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId)) || null;
}

function resolverEstudanteParaFormulario(estudanteId) {
    const estudanteEncontrado = estadoDocente.estudantes.find((item) => Number(item.estudante_id) === Number(estudanteId));
    if (estudanteEncontrado) {
        return estudanteEncontrado;
    }

    const registro = estadoDocente.registros.find((item) => Number(item.estudante_id) === Number(estudanteId));
    if (!registro) {
        return null;
    }

    return {
        estudante_id: Number(registro.estudante_id),
        nome: String(registro.estudante_nome || ""),
        turma_id: Number(registro.turma_id || 0),
        turma_nome: String(registro.turma_nome || ""),
        sinalizado: true,
        registro_id: Number(registro.id || 0),
        nivel_atencao: String(registro.nivel_atencao || ""),
        observacao_professor: String(registro.observacao_professor || ""),
        texto_gerado: String(registro.texto_gerado || ""),
        motivo_ids: Array.isArray(registro.motivo_ids) ? registro.motivo_ids : [],
        motivos: Array.isArray(registro.motivos) ? registro.motivos : [],
        pos_preconselho_recuperado: typeof registro.pos_preconselho_recuperado === "boolean"
            ? registro.pos_preconselho_recuperado
            : null,
        pos_preconselho_motivo_ids: Array.isArray(registro.pos_preconselho_motivo_ids)
            ? registro.pos_preconselho_motivo_ids
            : [],
        pos_preconselho_motivos: Array.isArray(registro.pos_preconselho_motivos)
            ? registro.pos_preconselho_motivos
            : [],
        pos_preconselho_observacao: String(registro.pos_preconselho_observacao || ""),
        estudante_em_rav: Boolean(registro.estudante_em_rav)
    };
}

function obterMotivosSelecionadosDocente() {
    return Array.from(document.querySelectorAll(".preconselho-motivo-checkbox:checked"))
        .map((checkbox) => Number(checkbox.value || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0);
}

function aplicarSelecaoMotivosDocente(motivoIds = []) {
    const ids = new Set((motivoIds || []).map((item) => Number(item)));
    document.querySelectorAll(".preconselho-motivo-checkbox").forEach((checkbox) => {
        checkbox.checked = ids.has(Number(checkbox.value || 0));
    });
}

function definirStatusPosPreConselhoDocente(valor = "") {
    const status = valor === "sim" || valor === "nao" ? valor : "";
    el("preconselhoPosPreConselhoStatus").value = status;

    document.querySelectorAll(".preconselho-choice-btn").forEach((botao) => {
        const ativo = botao.dataset.valor === status;
        botao.classList.toggle("is-active", ativo);
        botao.setAttribute("aria-pressed", ativo ? "true" : "false");
    });

    if (status === "sim") {
        el("preconselhoPosPreConselhoAjuda").textContent =
            "O texto informará que o estudante foi recuperado pela recuperação paralela.";
        return;
    }
    if (status === "nao") {
        el("preconselhoPosPreConselhoAjuda").textContent =
            "O texto informará que o estudante manteve baixo rendimento após a recuperação paralela.";
        return;
    }
    el("preconselhoPosPreConselhoAjuda").textContent =
        "Use “Sim” quando houve recuperação e “Não” quando o estudante manteve baixo rendimento.";
}

function obterStatusPosPreConselhoDocente() {
    const valor = String(el("preconselhoPosPreConselhoStatus").value || "").trim().toLowerCase();
    if (valor === "sim") {
        return true;
    }
    if (valor === "nao") {
        return false;
    }
    return null;
}

function resumoPosPreConselho(item = {}) {
    const status = typeof item.pos_preconselho_recuperado === "boolean"
        ? item.pos_preconselho_recuperado
        : null;
    if (status === null) {
        return "";
    }

    const base = status
        ? "Recuperado pela recuperação paralela"
        : "Manteve baixo rendimento após a recuperação paralela";
    const observacao = String(item.pos_preconselho_observacao || "").trim();
    return observacao ? `${base}: ${observacao}` : base;
}

function atualizarStatusSinalizacaoDocente({ possuiEstudante = false, possuiRegistro = false } = {}) {
    if (!possuiEstudante) {
        el("preconselhoStatusSelecionadoTitulo").textContent = "Nenhum estudante em edição";
        el("preconselhoStatusSelecionadoTexto").textContent =
            "Quando você selecionar um estudante e salvar o formulário, a sinalização será aplicada automaticamente.";
        return;
    }

    if (possuiRegistro) {
        el("preconselhoStatusSelecionadoTitulo").textContent = "Estudante já sinalizado";
        el("preconselhoStatusSelecionadoTexto").textContent =
            "Ao salvar novamente, o parecer será atualizado. Para remover a sinalização desta seleção, use Excluir registro.";
        return;
    }

    el("preconselhoStatusSelecionadoTitulo").textContent = "Sinalização automática no salvamento";
    el("preconselhoStatusSelecionadoTexto").textContent =
        "Este estudante será sinalizado automaticamente assim que o registro for salvo nesta turma, disciplina e período.";
}

function atualizarVisibilidadeRavDocente() {
    const campo = el("preconselhoRavRegistroField");
    const checkbox = el("preconselhoEstudanteEmRav");
    const visivel = periodoTemRav();
    if (campo) {
        campo.hidden = !visivel;
    }
    if (!visivel && checkbox) {
        checkbox.checked = false;
    }
}

function modalRegistroDocenteAberto() {
    return Boolean(el("preconselhoModalEditor")) && !el("preconselhoModalEditor").hidden;
}

function resetarScrollModalRegistroDocente() {
    const modal = el("preconselhoModalEditor");
    const painel = el("preconselhoPainelEditor");
    const editor = painel?.querySelector(".preconselho-editor-scroll");

    [modal, painel, editor].forEach((container) => {
        if (!container) {
            return;
        }

        container.scrollTop = 0;
        if (typeof container.scrollTo === "function") {
            container.scrollTo({ top: 0, left: 0, behavior: "auto" });
        }
    });
}

function focarInicioModalRegistroDocente() {
    const painel = el("preconselhoPainelEditor");
    if (!painel || typeof painel.focus !== "function") {
        return;
    }

    try {
        painel.focus({ preventScroll: true });
    } catch (_erro) {
        painel.focus();
    }
}

function abrirModalRegistroDocente() {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return;
    }

    if (modal.hidden) {
        const focoAtual = document.activeElement;
        ultimoElementoFocadoModal = focoAtual && typeof focoAtual.focus === "function" ? focoAtual : null;
    }
    modal.hidden = false;
    document.body.classList.add("preconselho-modal-open");
    window.requestAnimationFrame(() => {
        resetarScrollModalRegistroDocente();
        focarInicioModalRegistroDocente();
    });
}

function fecharModalRegistroDocente({ limparFormulario = true, restaurarFoco = true } = {}) {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return;
    }

    modal.hidden = true;
    document.body.classList.remove("preconselho-modal-open");

    if (limparFormulario) {
        limparMensagem("msgPreconselhoRegistro");
        limparFormularioDocente();
    }

    if (restaurarFoco && ultimoElementoFocadoModal && typeof ultimoElementoFocadoModal.focus === "function") {
        ultimoElementoFocadoModal.focus();
    }
    ultimoElementoFocadoModal = null;
}

function abrirModalComEstudante(estudante) {
    if (!estudante) {
        return;
    }

    preencherFormularioComEstudante(estudante);
    abrirModalRegistroDocente();
}

function limparFormularioDocente() {
    estadoDocente.estudanteId = null;
    el("preconselhoRegistroAtualId").value = "";
    el("preconselhoEstudanteAtualId").value = "";
    el("preconselhoEstudanteSelecionadoNome").textContent = "Selecione um estudante para iniciar.";
    el("preconselhoEstudanteSelecionadoMeta").textContent = "Os dados do registro aparecerão aqui.";
    el("preconselhoSinalizarEstudante").checked = false;
    el("preconselhoNivelAtencao").value = "";
    el("preconselhoObservacaoProfessor").value = "";
    definirStatusPosPreConselhoDocente("");
    el("preconselhoObservacaoPosPreConselho").value = "";
    el("preconselhoEstudanteEmRav").checked = false;
    aplicarSelecaoMotivosDocente([]);
    el("preconselhoTextoPreview").value = "";
    el("preconselhoPreviewAjuda").textContent = "Selecione um estudante e marque os motivos para gerar a pré-visualização.";
    atualizarStatusSinalizacaoDocente();
    atualizarVisibilidadeRavDocente();
    atualizarEstadoFormularioDocente();
    renderizarEstudantesDocente();
}

function definirBotoesDocenteHabilitados() {
    const periodo = periodoDocenteAtual();
    const registro = registroDocenteAtual();
    const possuiEstudante = Number(estadoDocente.estudanteId || 0) > 0;
    const podeEditar = Boolean(periodo?.editavel);
    const camposHabilitados = possuiEstudante && podeEditar;

    el("preconselhoNivelAtencao").disabled = !camposHabilitados;
    el("preconselhoObservacaoProfessor").disabled = !camposHabilitados;
    el("preconselhoObservacaoPosPreConselho").disabled = !camposHabilitados;
    el("preconselhoEstudanteEmRav").disabled = !camposHabilitados || !periodoTemRav(periodo);
    document.querySelectorAll(".preconselho-motivo-checkbox").forEach((checkbox) => {
        checkbox.disabled = !camposHabilitados;
    });
    document.querySelectorAll(".preconselho-choice-btn").forEach((botao) => {
        botao.disabled = !camposHabilitados;
    });

    el("btnSalvarRegistroDocente").disabled = !possuiEstudante || !podeEditar;
    el("btnExcluirRegistroDocente").disabled = !registro || !podeEditar;

    if (!possuiEstudante) {
        el("preconselhoPreviewAjuda").textContent = "Selecione um estudante para preencher o formulário.";
        return;
    }
    if (!podeEditar) {
        el("preconselhoPreviewAjuda").textContent = "O período selecionado está fechado para edição do professor. Os dados permanecem disponíveis para consulta.";
        return;
    }
    if (obterMotivosSelecionadosDocente().length === 0) {
        el("preconselhoPreviewAjuda").textContent = "Selecione ao menos um motivo para gerar a pré-visualização.";
        return;
    }

    el("preconselhoPreviewAjuda").textContent =
        "O texto é atualizado automaticamente conforme os motivos e a observação selecionados.";
}

function atualizarEstadoFormularioDocente() {
    definirBotoesDocenteHabilitados();
}

function renderizarCabecalho() {
    const primeiroNome = obterPrimeiroNome();
    const possuiVisaoDocente = Boolean(contextoAtual?.professor_id);
    const possuiVisaoInstitucional = Boolean(contextoAtual?.pode_consolidar);
    let descricao = "visão institucional";
    if (possuiVisaoDocente && possuiVisaoInstitucional) {
        descricao = "registro docente e visão institucional";
    } else if (possuiVisaoDocente) {
        descricao = "registro docente";
    }
    el("preconselhoUsuario").textContent = `${primeiroNome} | ${descricao}`;
    el("btnIrAdmin").hidden = !Boolean(usuarioAtual?.eh_admin);
}

function renderizarAbasDisponiveis() {
    const mostrarDocente = Boolean(contextoAtual?.professor_id);
    const mostrarConsolidacao = Boolean(contextoAtual?.pode_consolidar);
    const mostrarRelatorio = Boolean(contextoAtual?.pode_relatorio);
    const mostrarConfiguracoes = Boolean(contextoAtual?.pode_configurar);

    el("tabBtnDocente").hidden = !mostrarDocente;
    el("tabBtnConsolidacao").hidden = !mostrarConsolidacao;
    el("tabBtnRelatorio").hidden = !mostrarRelatorio;
    el("tabBtnConfiguracoes").hidden = !mostrarConfiguracoes;

    const ordem = [
        { aba: "docente", visivel: mostrarDocente },
        { aba: "consolidacao", visivel: mostrarConsolidacao },
        { aba: "relatorio", visivel: mostrarRelatorio },
        { aba: "configuracoes", visivel: mostrarConfiguracoes }
    ].filter((item) => item.visivel);

    const proximaAba = ordem.find((item) => item.aba === abaAtiva) ? abaAtiva : (ordem[0]?.aba || "");
    ativarAba(proximaAba);
}

function ativarAba(aba) {
    abaAtiva = aba || "";

    document.querySelectorAll("[data-preconselho-tab-trigger]").forEach((botao) => {
        const ativa = botao.dataset.preconselhoTabTrigger === abaAtiva;
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
    });

    document.querySelectorAll("[data-preconselho-tab-panel]").forEach((painel) => {
        const ativo = painel.dataset.preconselhoTabPanel === abaAtiva;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

function renderizarSelectPeriodos() {
    const periodos = obterPeriodos();

    preencherSelect(
        el("preconselhoPeriodoDocente"),
        periodos,
        (item) => item.id,
        (item) => `${rotuloPeriodo(item)}${item.status === "ABERTO" ? " - aberto" : " - fechado"}`,
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: estadoDocente.periodoId || periodos[0]?.id || ""
        }
    );

    preencherSelect(
        el("preconselhoPeriodoConsolidacao"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoConsolidacao")?.value || periodos[0]?.id || ""
        }
    );

    preencherSelect(
        el("preconselhoPeriodoRelatorio"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoRelatorio")?.value || periodos[0]?.id || ""
        }
    );

    if (!estadoDocente.periodoId && periodos.length > 0) {
        const periodoAberto = periodos.find((item) => item.status === "ABERTO");
        estadoDocente.periodoId = Number(periodoAberto?.id || periodos[0].id);
        el("preconselhoPeriodoDocente").value = String(estadoDocente.periodoId);
    }
}

function renderizarSelectsConsolidacao() {
    preencherSelect(
        el("preconselhoProfessorConsolidacao"),
        Array.isArray(contextoAtual?.professores) ? contextoAtual.professores : [],
        (item) => item.id,
        (item) => item.label || item.nome,
        "Todos os professores",
        {
            valorSelecionado: el("preconselhoProfessorConsolidacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoTurmaConsolidacao"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaConsolidacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoDisciplinaConsolidacao"),
        Array.isArray(contextoAtual?.disciplinas) ? contextoAtual.disciplinas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as disciplinas",
        {
            valorSelecionado: el("preconselhoDisciplinaConsolidacao")?.value || ""
        }
    );
}

function renderizarSelectNivelAtencao() {
    preencherSelect(
        el("preconselhoNivelAtencao"),
        Array.isArray(contextoAtual?.niveis_atencao) ? contextoAtual.niveis_atencao : [],
        (item) => item.id,
        (item) => item.nome,
        "Não informado",
        {
            valorSelecionado: ""
        }
    );
}

function renderizarSelectCategoriasMotivo() {
    preencherSelect(
        el("preconselhoMotivoCategoria"),
        CATEGORIAS_MOTIVO,
        (item) => item.id,
        (item) => item.nome,
        "Selecione a categoria",
        {
            permitirVazio: false
        }
    );
}

function renderizarMotivosDocente() {
    const container = el("preconselhoMotivosDocente");
    if (!container) {
        return;
    }

    const selecionados = new Set(obterMotivosSelecionadosDocente());
    const motivos = obterMotivosContexto().filter((item) => Number(item.ativo ?? 1) === 1);

    if (motivos.length === 0) {
        container.innerHTML = '<p class="pcpi-hint">Nenhum motivo ativo cadastrado.</p>';
        return;
    }

    const grupos = CATEGORIAS_MOTIVO
        .map((categoria) => ({
            ...categoria,
            motivos: motivos.filter((item) => item.categoria === categoria.id)
        }))
        .filter((grupo) => grupo.motivos.length > 0);

    container.innerHTML = grupos.map((grupo) => `
        <section class="preconselho-motivo-group">
            <h3>${escaparHtml(grupo.nome)}</h3>
            <div class="preconselho-motivos">
                ${grupo.motivos.map((motivo) => `
                    <label class="preconselho-motivo-option">
                        <input class="preconselho-motivo-checkbox" type="checkbox" value="${Number(motivo.id)}" ${selecionados.has(Number(motivo.id)) ? "checked" : ""}>
                        <span>${escaparHtml(motivo.descricao || "")}</span>
                    </label>
                `).join("")}
            </div>
        </section>
    `).join("");
}

function renderizarResumoDocente() {
    const combos = Array.isArray(estadoDocente.combos) ? estadoDocente.combos : [];
    const totalCombos = combos.length;
    const totalSinalizados = combos.reduce((acc, item) => acc + Number(item.total_sinalizados || 0), 0);
    const totalPendentes = combos.reduce((acc, item) => acc + Number(item.total_pendentes || 0), 0);

    el("preconselhoResumoTotalTurmas").textContent = String(totalCombos);
    el("preconselhoResumoTotalSinalizados").textContent = String(totalSinalizados);
    el("preconselhoResumoTotalPendentes").textContent = String(totalPendentes);
}

function renderizarCombosDocente() {
    const container = el("listaMinhasTurmasDisciplinas");
    if (!container) {
        return;
    }

    if (!estadoDocente.periodoId) {
        container.innerHTML = '<p class="preconselho-empty-state">Selecione um período para carregar sua carga.</p>';
        return;
    }

    if (!Array.isArray(estadoDocente.combos) || estadoDocente.combos.length === 0) {
        container.innerHTML = '<p class="preconselho-empty-state">Nenhuma turma ou disciplina foi localizada para a sua carga neste período.</p>';
        return;
    }

    container.innerHTML = estadoDocente.combos.map((item) => {
        const ativo = Number(item.turma_id) === Number(estadoDocente.turmaId) && Number(item.disciplina_id) === Number(estadoDocente.disciplinaId);
        return `
            <button type="button" class="preconselho-selection-card ${ativo ? "is-active" : ""}"
                data-turma-id="${Number(item.turma_id)}"
                data-disciplina-id="${Number(item.disciplina_id)}">
                <strong>${escaparHtml(item.turma_nome || "")} • ${escaparHtml(item.disciplina_nome || "")}</strong>
                <span>${Number(item.total_estudantes || 0)} estudante(s)</span>
                <small>${Number(item.total_sinalizados || 0)} sinalizado(s)</small>
            </button>
        `;
    }).join("");
}

function renderizarEstudantesDocente() {
    const lista = el("listaEstudantesDocente");
    if (!lista) {
        return;
    }

    const combo = comboDocenteAtual();
    if (!combo) {
        lista.innerHTML = criarEstadoVazio("Escolha uma turma e disciplina para listar os estudantes.");
        el("preconselhoResumoEstudantesDocente").textContent = "A lista será carregada assim que uma combinação da carga for selecionada.";
        return;
    }

    if (!Array.isArray(estadoDocente.estudantes) || estadoDocente.estudantes.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum estudante encontrado para os filtros aplicados.");
        el("preconselhoResumoEstudantesDocente").textContent = `${combo.turma_nome} • ${combo.disciplina_nome}`;
        return;
    }

    lista.innerHTML = estadoDocente.estudantes.map((item) => {
        const selecionado = Number(item.estudante_id) === Number(estadoDocente.estudanteId);
        const nivel = rotuloNivelAtencao(item.nivel_atencao);
        const resumoPos = resumoPosPreConselho(item);
        return `
            <li class="pcpi-item ${item.sinalizado ? "pcpi-item-manual" : "pcpi-item-automatico"}">
                <button type="button" class="preconselho-list-button ${selecionado ? "is-active" : ""}" data-estudante-id="${Number(item.estudante_id)}">
                    <span class="preconselho-list-button-top">
                        <strong>${escaparHtml(item.nome || "")}</strong>
                        <span class="pcpi-tag-group">
                            <span class="pcpi-chip ${item.sinalizado ? "pcpi-chip-manual" : "pcpi-chip-automatico"}">${item.sinalizado ? "Sinalizado" : "Estudante Ok"}</span>
                        </span>
                    </span>
                    <span class="pcpi-item-note">${escaparHtml(
                        item.sinalizado
                            ? `${item.motivos.length} motivo(s) selecionado(s)`
                            + (nivel ? ` • Atenção ${nivel}` : "")
                            + (item.motivos.length
                                ? `\n${item.motivos.map((m) => `- ${escaparHtml(m.descricao || "")}`).join("\n")}`
                                : ""
                            )
                            + (resumoPos ? `\n${resumoPos}` : "")
                            : "Clique para abrir um relato.")}
                    </span>
                </button>
            </li>
        `;
    }).join("");

    const total = estadoDocente.estudantes.length;
    const totalSinalizados = estadoDocente.estudantes.filter((item) => item.sinalizado).length;
    el("preconselhoResumoEstudantesDocente").textContent =
        `${combo.turma_nome} • ${combo.disciplina_nome} • ${total} estudante(s), ${totalSinalizados} sinalizado(s).`;
}

function formatarMotivosRegistro(motivos = []) {
    return motivos.map((item) => String(item.descricao || "")).filter(Boolean).join(", ");
}

function formatarListaNatural(valores = []) {
    const itens = Array.from(new Set(
        (Array.isArray(valores) ? valores : [])
            .map((item) => String(item || "").trim())
            .filter(Boolean)
    ));

    if (itens.length === 0) {
        return "";
    }
    if (itens.length === 1) {
        return itens[0];
    }
    if (itens.length === 2) {
        return `${itens[0]} e ${itens[1]}`;
    }
    return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

function renderizarRegistrosDocente() {
    const lista = el("listaRegistrosDocente");
    if (!lista) {
        return;
    }

    const itens = Array.isArray(estadoDocente.registros) ? estadoDocente.registros : [];
    el("preconselhoResumoRegistrosDocente").textContent = `${itens.length} ${itens.length === 1 ? "registro" : "registros"}`;

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum registro salvo para a turma e disciplina selecionadas.");
        return;
    }

    lista.innerHTML = itens.map((item) => `
        <li class="pcpi-item pcpi-item-manual">
            <div class="pcpi-checkbox-row">
                <div class="pcpi-item-body">
                    <div class="pcpi-item-top">
                        <strong>${escaparHtml(item.estudante_nome || "")}</strong>
                        <div class="pcpi-tag-group">
                            ${item.nivel_atencao ? `<span class="pcpi-chip">${escaparHtml(rotuloNivelAtencao(item.nivel_atencao))}</span>` : ""}
                            ${item.estudante_em_rav ? '<span class="pcpi-chip pcpi-chip-automatico">RAV</span>' : ""}
                            <span class="pcpi-chip pcpi-chip-manual">Salvo</span>
                        </div>
                    </div>
                    <p class="pcpi-item-line">${escaparHtml(item.disciplina_nome || "")}</p>
                    <p class="pcpi-item-note">${escaparHtml(formatarMotivosRegistro(item.motivos || []))}</p>
                    ${resumoPosPreConselho(item) ? `<p class="pcpi-item-note">${escaparHtml(resumoPosPreConselho(item))}</p>` : ""}
                    ${item.texto_gerado ? `<p class="pcpi-item-note is-secondary">${escaparHtml(item.texto_gerado)}</p>` : ""}
                    <div class="preconselho-item-actions">
                        <button type="button" class="preconselho-btn-link" data-action="editar-registro" data-estudante-id="${Number(item.estudante_id)}">Editar</button>
                        ${item.editavel ? `<button type="button" class="preconselho-btn-link" data-action="excluir-registro" data-registro-id="${Number(item.id)}">Excluir</button>` : ""}
                    </div>
                </div>
            </div>
        </li>
    `).join("");
}

function preencherFormularioComEstudante(estudante) {
    if (!estudante) {
        limparFormularioDocente();
        return;
    }

    estadoDocente.estudanteId = Number(estudante.estudante_id);
    const registro = registroDocenteAtual();

    el("preconselhoRegistroAtualId").value = registro ? String(registro.id) : "";
    el("preconselhoEstudanteAtualId").value = String(estudante.estudante_id);
    el("preconselhoEstudanteSelecionadoNome").textContent = estudante.nome || "Estudante";
    el("preconselhoEstudanteSelecionadoMeta").textContent = estudante.sinalizado
        ? `${estudante.turma_nome || ""} • Registro já salvo para a seleção atual.`
        : `${estudante.turma_nome || ""} • Ainda não sinalizado neste período e disciplina.`;
    el("preconselhoSinalizarEstudante").checked = true;
    el("preconselhoNivelAtencao").value = String(estudante.nivel_atencao || "");
    el("preconselhoObservacaoProfessor").value = String(estudante.observacao_professor || "");
    definirStatusPosPreConselhoDocente(
        estudante.pos_preconselho_recuperado === true
            ? "sim"
            : estudante.pos_preconselho_recuperado === false
                ? "nao"
                : ""
    );
    el("preconselhoObservacaoPosPreConselho").value = String(estudante.pos_preconselho_observacao || "");
    el("preconselhoEstudanteEmRav").checked = periodoTemRav() && Boolean(estudante.estudante_em_rav);
    aplicarSelecaoMotivosDocente(estudante.motivo_ids || []);
    atualizarStatusSinalizacaoDocente({
        possuiEstudante: true,
        possuiRegistro: Boolean(estudante.sinalizado),
    });
    atualizarVisibilidadeRavDocente();

    renderizarEstudantesDocente();
    atualizarEstadoFormularioDocente();
    void atualizarPreviewDocente();
}

async function atualizarPreviewDocente() {
    const possuiEstudante = Number(estadoDocente.estudanteId || 0) > 0;
    const motivoIds = obterMotivosSelecionadosDocente();
    const estudante = resolverEstudanteParaFormulario(estadoDocente.estudanteId);
    const combo = comboDocenteAtual();

    if (!possuiEstudante) {
        el("preconselhoTextoPreview").value = "";
        atualizarEstadoFormularioDocente();
        return;
    }

    if (motivoIds.length === 0) {
        el("preconselhoTextoPreview").value = "";
        atualizarEstadoFormularioDocente();
        return;
    }

    try {
        const resposta = await fetchComAuth("/preconselho/texto/preview", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                motivo_ids: motivoIds,
                observacao_professor: String(el("preconselhoObservacaoProfessor").value || "").trim(),
                nivel_atencao: String(el("preconselhoNivelAtencao").value || "").trim() || null,
                pos_preconselho_recuperado: obterStatusPosPreConselhoDocente(),
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: String(el("preconselhoObservacaoPosPreConselho").value || "").trim(),
                estudante_em_rav: periodoTemRav() && Boolean(el("preconselhoEstudanteEmRav").checked),
                estudante_nome: String(estudante?.nome || "").trim(),
                disciplina_nome: String(combo?.disciplina_nome || "").trim()
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível gerar a pré-visualização."));
        }

        const dados = await resposta.json();
        el("preconselhoTextoPreview").value = String(dados?.texto || "");
        atualizarEstadoFormularioDocente();
    } catch (erro) {
        el("preconselhoTextoPreview").value = "";
        el("preconselhoPreviewAjuda").textContent = erro.message || "Não foi possível gerar a pré-visualização.";
    }
}

function agendarPreviewDocente() {
    if (timerPreviewDocente) {
        window.clearTimeout(timerPreviewDocente);
    }
    timerPreviewDocente = window.setTimeout(() => {
        void atualizarPreviewDocente();
    }, 250);
}

async function carregarCombosDocente() {
    if (!estadoDocente.periodoId) {
        estadoDocente.combos = [];
        renderizarResumoDocente();
        renderizarCombosDocente();
        return;
    }

    const resposta = await fetchComAuth(`/preconselho/minhas-turmas-disciplinas?periodo_id=${Number(estadoDocente.periodoId)}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar as turmas e disciplinas do professor."));
    }

    estadoDocente.combos = await resposta.json();
    const comboAtual = comboDocenteAtual();
    if (!comboAtual && estadoDocente.combos.length > 0) {
        estadoDocente.turmaId = Number(estadoDocente.combos[0].turma_id);
        estadoDocente.disciplinaId = Number(estadoDocente.combos[0].disciplina_id);
    } else if (estadoDocente.combos.length === 0) {
        estadoDocente.turmaId = null;
        estadoDocente.disciplinaId = null;
    }

    renderizarResumoDocente();
    renderizarCombosDocente();
}

async function carregarEstudantesDocente() {
    const combo = comboDocenteAtual();
    if (!combo || !estadoDocente.periodoId) {
        estadoDocente.estudantes = [];
        renderizarEstudantesDocente();
        return;
    }

    const params = new URLSearchParams({
        periodo_id: String(estadoDocente.periodoId),
        turma_id: String(combo.turma_id),
        disciplina_id: String(combo.disciplina_id),
        q: String(el("preconselhoBuscaEstudante").value || "").trim(),
        status: String(el("preconselhoStatusEstudante").value || "todos")
    });

    const resposta = await fetchComAuth(`/preconselho/estudantes?${params.toString()}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os estudantes."));
    }

    estadoDocente.estudantes = await resposta.json();
    if (!estadoDocente.estudantes.some((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId))) {
        estadoDocente.estudanteId = null;
    }
    renderizarEstudantesDocente();
}

async function carregarRegistrosDocente() {
    const combo = comboDocenteAtual();
    if (!combo || !estadoDocente.periodoId) {
        estadoDocente.registros = [];
        renderizarRegistrosDocente();
        return;
    }

    const params = new URLSearchParams({
        periodo_id: String(estadoDocente.periodoId),
        turma_id: String(combo.turma_id),
        disciplina_id: String(combo.disciplina_id)
    });

    const resposta = await fetchComAuth(`/preconselho/registros?${params.toString()}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os registros salvos."));
    }

    const dados = await resposta.json();
    estadoDocente.registros = Array.isArray(dados?.itens) ? dados.itens : [];
    renderizarRegistrosDocente();
}

async function carregarPainelDocente(estudanteIdParaReabrir = null) {
    limparMensagem("msgPreconselhoDocente");
    try {
        await carregarCombosDocente();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);

        if (estudanteIdParaReabrir) {
            const estudante = resolverEstudanteParaFormulario(estudanteIdParaReabrir);
            if (estudante) {
                preencherFormularioComEstudante(estudante);
            } else {
                limparFormularioDocente();
            }
        } else {
            limparFormularioDocente();
        }

        definirMensagem("msgPreconselhoDocente", "Painel docente atualizado.");
        return true;
    } catch (erro) {
        estadoDocente.combos = [];
        estadoDocente.estudantes = [];
        estadoDocente.registros = [];
        renderizarResumoDocente();
        renderizarCombosDocente();
        renderizarEstudantesDocente();
        renderizarRegistrosDocente();
        limparFormularioDocente();
        definirMensagem("msgPreconselhoDocente", erro.message || "Não foi possível carregar o painel docente.", true);
        return false;
    }
}

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

function renderizarTabelaPeriodos() {
    const tbody = el("tbodyPeriodosPreconselho");
    if (!tbody) {
        return;
    }

    const periodos = obterPeriodos();
    if (periodos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="booking-empty">Nenhum período cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = periodos.map((item) => `
        <tr>
            <td data-label="Período">
                <strong>${escaparHtml(rotuloPeriodo(item))}</strong>
                <div class="preconselho-table-meta">${Number(item.ano_letivo || 0)} • etapa ${Number(item.etapa || 0)}${item.tem_rav ? " • RAV" : ""}</div>
            </td>
            <td data-label="Status">
                <span class="status-chip ${statusPeriodoClasse(item.status)}">${escaparHtml(rotuloStatusPeriodo(item.status))}</span>
            </td>
            <td data-label="Datas">
                ${escaparHtml(formatarDataBr(item.data_inicio))} a ${escaparHtml(formatarDataBr(item.data_fim))}
            </td>
            <td data-label="Ações">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-periodo" data-periodo-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-periodo" data-periodo-id="${Number(item.id)}" data-status="${escaparHtml(item.status || "")}">
                        ${item.status === "ABERTO" ? "Fechar" : "Abrir"}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function renderizarTabelaMotivos() {
    const tbody = el("tbodyMotivosPreconselho");
    if (!tbody) {
        return;
    }

    const motivos = obterMotivosContexto();
    if (motivos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="booking-empty">Nenhum motivo cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = motivos.map((item) => `
        <tr>
            <td data-label="Categoria">
                <strong>${escaparHtml(rotuloCategoria(item.categoria))}</strong>
                <div class="preconselho-table-meta">${escaparHtml(item.codigo || "")}</div>
            </td>
            <td data-label="Descrição">
                ${escaparHtml(item.descricao || "")}
            </td>
            <td data-label="Status">
                <span class="status-chip ${Number(item.ativo ?? 1) === 1 ? "status-aberto" : "status-fechado"}">
                    ${Number(item.ativo ?? 1) === 1 ? "Ativo" : "Inativo"}
                </span>
            </td>
            <td data-label="Ações">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-motivo" data-motivo-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-motivo" data-motivo-id="${Number(item.id)}" data-ativo="${Number(item.ativo ?? 1)}">
                        ${Number(item.ativo ?? 1) === 1 ? "Inativar" : "Ativar"}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function limparFormularioPeriodo() {
    el("preconselhoPeriodoEdicaoId").value = "";
    el("preconselhoPeriodoNome").value = "";
    el("preconselhoPeriodoAnoLetivo").value = String(new Date().getFullYear());
    el("preconselhoPeriodoEtapa").value = "1";
    el("preconselhoPeriodoDataInicio").value = "";
    el("preconselhoPeriodoDataFim").value = "";
    el("preconselhoPeriodoStatusForm").value = "ABERTO";
    el("preconselhoPeriodoTemRav").checked = false;
}

function limparFormularioMotivo() {
    el("preconselhoMotivoEdicaoId").value = "";
    el("preconselhoMotivoCategoria").value = CATEGORIAS_MOTIVO[0].id;
    el("preconselhoMotivoCodigo").value = "";
    el("preconselhoMotivoCodigo").disabled = false;
    el("preconselhoMotivoDescricao").value = "";
    el("preconselhoMotivoOrdem").value = "0";
}

function carregarPeriodoNoFormulario(periodoId) {
    const periodo = obterPeriodos().find((item) => Number(item.id) === Number(periodoId));
    if (!periodo) {
        return;
    }

    el("preconselhoPeriodoEdicaoId").value = String(periodo.id);
    el("preconselhoPeriodoNome").value = String(periodo.nome || "");
    el("preconselhoPeriodoAnoLetivo").value = String(periodo.ano_letivo || "");
    el("preconselhoPeriodoEtapa").value = String(periodo.etapa || "1");
    el("preconselhoPeriodoDataInicio").value = String(periodo.data_inicio || "");
    el("preconselhoPeriodoDataFim").value = String(periodo.data_fim || "");
    el("preconselhoPeriodoStatusForm").value = String(periodo.status || "FECHADO");
    el("preconselhoPeriodoTemRav").checked = Boolean(periodo.tem_rav);
}

function carregarMotivoNoFormulario(motivoId) {
    const motivo = obterMotivosContexto().find((item) => Number(item.id) === Number(motivoId));
    if (!motivo) {
        return;
    }

    el("preconselhoMotivoEdicaoId").value = String(motivo.id);
    el("preconselhoMotivoCategoria").value = String(motivo.categoria || CATEGORIAS_MOTIVO[0].id);
    el("preconselhoMotivoCodigo").value = String(motivo.codigo || "");
    el("preconselhoMotivoCodigo").disabled = true;
    el("preconselhoMotivoDescricao").value = String(motivo.descricao || "");
    el("preconselhoMotivoOrdem").value = String(Number(motivo.ordem || 0));
}

async function recarregarPeriodos() {
    const resposta = await fetchComAuth("/preconselho/periodos", { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar os períodos."));
    }

    const periodos = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        periodos
    };
    renderizarSelectPeriodos();
    renderizarTabelaPeriodos();
}

async function recarregarMotivos() {
    const incluirInativos = Boolean(contextoAtual?.pode_configurar);
    const sufixo = incluirInativos ? "?incluir_inativos=true" : "";
    const resposta = await fetchComAuth(`/preconselho/motivos${sufixo}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar os motivos."));
    }

    const motivos = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        motivos
    };
    renderizarMotivosDocente();
    renderizarTabelaMotivos();
}

async function salvarPeriodo(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoPeriodo");

    const periodoId = Number(el("preconselhoPeriodoEdicaoId").value || 0);
    const payloadBase = {
        nome: String(el("preconselhoPeriodoNome").value || "").trim(),
        ano_letivo: Number(el("preconselhoPeriodoAnoLetivo").value || 0),
        etapa: Number(el("preconselhoPeriodoEtapa").value || 0),
        data_inicio: String(el("preconselhoPeriodoDataInicio").value || ""),
        data_fim: String(el("preconselhoPeriodoDataFim").value || ""),
        tem_rav: Boolean(el("preconselhoPeriodoTemRav").checked)
    };
    const statusDesejado = String(el("preconselhoPeriodoStatusForm").value || "ABERTO");

    try {
        let resposta;
        if (periodoId > 0) {
            resposta = await fetchComAuth(`/preconselho/periodos/${periodoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payloadBase)
            });
        } else {
            resposta = await fetchComAuth("/preconselho/periodos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify({
                    ...payloadBase,
                    status: statusDesejado
                })
            });
        }

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o período."));
        }

        const periodoSalvo = await resposta.json();
        if (periodoId > 0 && String(periodoSalvo.status || "") !== statusDesejado) {
            const respostaStatus = await fetchComAuth(`/preconselho/periodos/${periodoSalvo.id}/status`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({ status: statusDesejado })
            });
            if (!respostaStatus.ok) {
                throw new Error(await obterMensagemErroResposta(respostaStatus, "O período foi salvo, mas o status não foi atualizado."));
            }
        }

        await recarregarPeriodos();
        renderizarSelectsConsolidacao();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
        }
        limparFormularioPeriodo();
        definirMensagem("msgPreconselhoPeriodo", periodoId > 0 ? "Período atualizado com sucesso." : "Período criado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoPeriodo", erro.message || "Erro ao salvar o período.", true);
    }
}

async function alternarStatusPeriodo(periodoId, statusAtual) {
    limparMensagem("msgPreconselhoPeriodo");
    try {
        const resposta = await fetchComAuth(`/preconselho/periodos/${Number(periodoId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                status: String(statusAtual || "").toUpperCase() === "ABERTO" ? "FECHADO" : "ABERTO"
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar o status do período."));
        }

        await recarregarPeriodos();
        renderizarSelectsConsolidacao();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
        }
        definirMensagem("msgPreconselhoPeriodo", "Status do período atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoPeriodo", erro.message || "Erro ao atualizar o status do período.", true);
    }
}

async function salvarMotivo(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoMotivo");

    const motivoId = Number(el("preconselhoMotivoEdicaoId").value || 0);
    const payload = {
        categoria: String(el("preconselhoMotivoCategoria").value || ""),
        descricao: String(el("preconselhoMotivoDescricao").value || "").trim(),
        ordem: Number(el("preconselhoMotivoOrdem").value || 0)
    };

    try {
        let resposta;
        if (motivoId > 0) {
            resposta = await fetchComAuth(`/preconselho/motivos/${motivoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
        } else {
            resposta = await fetchComAuth("/preconselho/motivos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    codigo: String(el("preconselhoMotivoCodigo").value || "").trim()
                })
            });
        }

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o motivo."));
        }

        await recarregarMotivos();
        limparFormularioMotivo();
        definirMensagem("msgPreconselhoMotivo", motivoId > 0 ? "Motivo atualizado com sucesso." : "Motivo criado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoMotivo", erro.message || "Erro ao salvar o motivo.", true);
    }
}

async function alternarStatusMotivo(motivoId, ativoAtual) {
    limparMensagem("msgPreconselhoMotivo");
    try {
        const resposta = await fetchComAuth(`/preconselho/motivos/${Number(motivoId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                ativo: Number(ativoAtual) !== 1
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar o status do motivo."));
        }

        await recarregarMotivos();
        definirMensagem("msgPreconselhoMotivo", "Status do motivo atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoMotivo", erro.message || "Erro ao atualizar o status do motivo.", true);
    }
}

async function salvarRegistroDocente(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRegistro");

    const periodo = periodoDocenteAtual();
    const combo = comboDocenteAtual();
    const estudanteId = Number(estadoDocente.estudanteId || 0);
    const motivoIds = obterMotivosSelecionadosDocente();
    const observacao = String(el("preconselhoObservacaoProfessor").value || "").trim();
    const nivelAtencao = String(el("preconselhoNivelAtencao").value || "").trim() || null;
    const posPreConselhoRecuperado = obterStatusPosPreConselhoDocente();
    const posPreConselhoObservacao = String(el("preconselhoObservacaoPosPreConselho").value || "").trim();
    const estudanteEmRav = periodoTemRav(periodo) && Boolean(el("preconselhoEstudanteEmRav").checked);

    if (!periodo || !combo) {
        definirMensagem("msgPreconselhoRegistro", "Selecione um período e uma turma/disciplina antes de salvar.", true);
        return;
    }
    if (!estudanteId) {
        definirMensagem("msgPreconselhoRegistro", "Selecione um estudante para continuar.", true);
        return;
    }
    if (!periodo.editavel) {
        definirMensagem("msgPreconselhoRegistro", "O período selecionado está fechado para edição.", true);
        return;
    }

    try {
        if (motivoIds.length === 0) {
            definirMensagem("msgPreconselhoRegistro", "Selecione ao menos um motivo para salvar o registro.", true);
            return;
        }

        const resposta = await fetchComAuth("/preconselho/registros", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                periodo_id: Number(periodo.id),
                turma_id: Number(combo.turma_id),
                disciplina_id: Number(combo.disciplina_id),
                estudante_id: estudanteId,
                sinalizar: true,
                motivo_ids: motivoIds,
                observacao_professor: observacao,
                nivel_atencao: nivelAtencao,
                pos_preconselho_recuperado: posPreConselhoRecuperado,
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: posPreConselhoObservacao,
                estudante_em_rav: estudanteEmRav
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o registro."));
        }

        const salvo = await resposta.json();
        const painelAtualizado = await carregarPainelDocente(Number(salvo.estudante_id));
        if (!painelAtualizado) {
            definirMensagem("msgPreconselhoRegistro", "Registro salvo, mas o painel não foi recarregado corretamente.", true);
            return;
        }
        definirMensagem("msgPreconselhoDocente", `Registro de ${String(salvo.estudante_nome || "estudante")} salvo com sucesso.`);
        fecharModalRegistroDocente({ restaurarFoco: false });
    } catch (erro) {
        definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao salvar o registro.", true);
    }
}

async function excluirRegistroDocente(registroId) {
    const resposta = await fetchComAuth(`/preconselho/registros/${Number(registroId)}`, {
        method: "DELETE",
        headers
    });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível excluir o registro."));
    }
}

async function copiarTexto(idCampo, idMensagem, sucesso) {
    const campo = el(idCampo);
    const texto = String(campo?.value || "").trim();
    if (!texto) {
        definirMensagem(idMensagem, "Não há texto disponível para copiar.", true);
        return;
    }

    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(texto);
        } else {
            campo.select();
            document.execCommand("copy");
        }
        definirMensagem(idMensagem, sucesso);
    } catch (_erro) {
        definirMensagem(idMensagem, "Não foi possível copiar o texto.", true);
    }
}

async function carregarUsuario() {
    const resposta = await fetchComAuth("/me", { headers });
    if (!resposta.ok) {
        throw new Error("Não foi possível carregar o usuário.");
    }

    usuarioAtual = await resposta.json();
    if (!modulosPermitidos(usuarioAtual).has("preconselho")) {
        window.location.href = "/servicos";
        return;
    }

    renderizarCabecalho();
}

async function carregarContexto() {
    const resposta = await fetchComAuth("/preconselho/contexto", { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar o contexto do pré-conselho."));
    }

    contextoAtual = await resposta.json();

    renderizarCabecalho();
    renderizarAbasDisponiveis();
    renderizarSelectPeriodos();
    renderizarSelectsConsolidacao();
    renderizarSelectNivelAtencao();
    renderizarSelectCategoriasMotivo();
    renderizarMotivosDocente();
    definirStatusPosPreConselhoDocente("");
    renderizarTabelaPeriodos();
    renderizarTabelaMotivos();

    if (!el("preconselhoPeriodoConsolidacao").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoConsolidacao").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }
    if (!el("preconselhoPeriodoRelatorio").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoRelatorio").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }

    renderizarRelatorio();
}

async function carregarPainelInicial() {
    const tarefas = [];
    if (usuarioEhProfessor(usuarioAtual)) {
        tarefas.push(carregarPainelDocente());
    }
    if (contextoAtual?.pode_consolidar) {
        tarefas.push(carregarConsolidacao());
    }
    if (contextoAtual?.pode_relatorio) {
        tarefas.push(carregarRelatorio());
    }
    await Promise.all(tarefas);
}

function registrarEventos() {
    document.querySelectorAll("[data-preconselho-tab-trigger]").forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAba(botao.dataset.preconselhoTabTrigger || "");
        });
    });

    el("btnIrAdmin").addEventListener("click", () => {
        window.location.href = "/admin";
    });

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });

    el("formPreconselhoDocentePeriodo").addEventListener("submit", async (event) => {
        event.preventDefault();
        fecharModalRegistroDocente({ restaurarFoco: false });
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("preconselhoPeriodoDocente").addEventListener("change", async () => {
        fecharModalRegistroDocente({ restaurarFoco: false });
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("listaMinhasTurmasDisciplinas").addEventListener("click", async (event) => {
        const botao = event.target.closest("button[data-turma-id][data-disciplina-id]");
        if (!botao) {
            return;
        }
        estadoDocente.turmaId = Number(botao.dataset.turmaId || 0);
        estadoDocente.disciplinaId = Number(botao.dataset.disciplinaId || 0);
        fecharModalRegistroDocente({ restaurarFoco: false });
        renderizarCombosDocente();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
        limparFormularioDocente();
    });

    el("formFiltrosEstudantesDocente").addEventListener("submit", async (event) => {
        event.preventDefault();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
    });

    el("preconselhoBuscaEstudante").addEventListener("input", async () => {
        await carregarEstudantesDocente();
    });

    el("preconselhoStatusEstudante").addEventListener("change", async () => {
        await carregarEstudantesDocente();
    });

    el("listaEstudantesDocente").addEventListener("click", (event) => {
        const botao = event.target.closest("button[data-estudante-id]");
        if (!botao) {
            return;
        }
        const estudante = resolverEstudanteParaFormulario(botao.dataset.estudanteId || 0);
        abrirModalComEstudante(estudante);
    });

    el("listaRegistrosDocente").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-registro']");
        if (botaoEditar) {
            const estudante = resolverEstudanteParaFormulario(botaoEditar.dataset.estudanteId || 0);
            abrirModalComEstudante(estudante);
            return;
        }

        const botaoExcluir = event.target.closest("button[data-action='excluir-registro']");
        if (botaoExcluir) {
            const registro = estadoDocente.registros.find((item) => Number(item.id) === Number(botaoExcluir.dataset.registroId || 0));
            if (!registro) {
                return;
            }
            if (!window.confirm("Deseja realmente excluir este registro do pré-conselho?")) {
                return;
            }
            limparMensagem("msgPreconselhoRegistro");
            try {
                await excluirRegistroDocente(registro.id);
                const painelAtualizado = await carregarPainelDocente();
                if (!painelAtualizado) {
                    definirMensagem("msgPreconselhoRegistro", "Registro excluído, mas o painel não foi recarregado corretamente.", true);
                    return;
                }
                definirMensagem("msgPreconselhoDocente", "Registro excluído com sucesso.");
                fecharModalRegistroDocente({ restaurarFoco: false });
            } catch (erro) {
                definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao excluir o registro.", true);
            }
        }
    });

    el("formRegistroDocente").addEventListener("submit", salvarRegistroDocente);
    el("btnLimparRegistroDocente").addEventListener("click", () => {
        limparMensagem("msgPreconselhoRegistro");
        limparFormularioDocente();
    });
    el("btnExcluirRegistroDocente").addEventListener("click", async () => {
        const registro = registroDocenteAtual();
        if (!registro) {
            definirMensagem("msgPreconselhoRegistro", "Não há registro salvo para excluir.", true);
            return;
        }
        if (!window.confirm("Deseja realmente excluir este registro do pré-conselho?")) {
            return;
        }
        limparMensagem("msgPreconselhoRegistro");
        try {
            await excluirRegistroDocente(registro.id);
            const painelAtualizado = await carregarPainelDocente();
            if (!painelAtualizado) {
                definirMensagem("msgPreconselhoRegistro", "Registro excluído, mas o painel não foi recarregado corretamente.", true);
                return;
            }
            definirMensagem("msgPreconselhoDocente", "Registro excluído com sucesso.");
            fecharModalRegistroDocente({ restaurarFoco: false });
        } catch (erro) {
            definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao excluir o registro.", true);
        }
    });

    el("btnFecharModalRegistroDocente").addEventListener("click", () => {
        fecharModalRegistroDocente();
    });
    el("btnFecharModalRegistroDocenteRodape").addEventListener("click", () => {
        fecharModalRegistroDocente();
    });
    el("preconselhoModalEditor").addEventListener("click", (event) => {
        if (event.target === event.currentTarget) {
            fecharModalRegistroDocente();
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modalRegistroDocenteAberto()) {
            fecharModalRegistroDocente();
        }
    });

    el("preconselhoNivelAtencao").addEventListener("change", agendarPreviewDocente);
    el("preconselhoObservacaoProfessor").addEventListener("input", agendarPreviewDocente);
    el("preconselhoMotivosDocente").addEventListener("change", (event) => {
        if (!event.target.closest(".preconselho-motivo-checkbox")) {
            return;
        }
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    document.querySelectorAll(".preconselho-choice-btn").forEach((botao) => {
        botao.addEventListener("click", () => {
            const valorAtual = String(el("preconselhoPosPreConselhoStatus").value || "");
            const proximoValor = valorAtual === botao.dataset.valor ? "" : String(botao.dataset.valor || "");
            definirStatusPosPreConselhoDocente(proximoValor);
            atualizarEstadoFormularioDocente();
            agendarPreviewDocente();
        });
    });
    el("preconselhoObservacaoPosPreConselho").addEventListener("input", agendarPreviewDocente);
    el("preconselhoEstudanteEmRav").addEventListener("change", agendarPreviewDocente);
    el("preconselhoPosPreConselhoStatus").addEventListener("change", () => {
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });

    el("formConsolidacaoPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarConsolidacao();
    });
    el("preconselhoPeriodoConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoProfessorConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoTurmaConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoDisciplinaConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });

    el("btnCopiarTextoConsolidado").addEventListener("click", async () => {
        await copiarTexto("preconselhoTextoConsolidado", "msgPreconselhoConsolidacao", "Texto consolidado copiado.");
    });

    el("formRelatorioPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRelatorio();
    });
    el("preconselhoPeriodoRelatorio").addEventListener("change", async () => {
        await carregarRelatorio();
    });

    el("formPeriodoPreconselho").addEventListener("submit", salvarPeriodo);
    el("btnLimparPeriodoPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoPeriodo");
        limparFormularioPeriodo();
    });

    el("tbodyPeriodosPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-periodo']");
        if (botaoEditar) {
            carregarPeriodoNoFormulario(botaoEditar.dataset.periodoId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-periodo']");
        if (botaoStatus) {
            await alternarStatusPeriodo(botaoStatus.dataset.periodoId, botaoStatus.dataset.status);
        }
    });

    el("formMotivoPreconselho").addEventListener("submit", salvarMotivo);
    el("btnLimparMotivoPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoMotivo");
        limparFormularioMotivo();
    });

    el("tbodyMotivosPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-motivo']");
        if (botaoEditar) {
            carregarMotivoNoFormulario(botaoEditar.dataset.motivoId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-motivo']");
        if (botaoStatus) {
            await alternarStatusMotivo(botaoStatus.dataset.motivoId, botaoStatus.dataset.ativo);
        }
    });
}

async function iniciarModulo() {
    registrarEventos();
    limparFormularioPeriodo();
    limparFormularioMotivo();
    try {
        await carregarUsuario();
        await carregarContexto();
        await carregarPainelInicial();
    } catch (erro) {
        definirMensagem("msgPreconselhoDocente", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoConsolidacao", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoRelatorio", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
    }
}

iniciarModulo();
