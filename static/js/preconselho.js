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
let modalDocenteAlterado = false;
let modalDocenteSalvando = false;
let timerBuscaEstudante = null;
let buscaEstudanteController = null;
let buscaEstudanteSequencia = 0;

const estadoDocente = {
    modo: "registro",
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

const estadoPainelReavaliacao = {
    periodo: null,
    registros: [],
    estudantesExpandidos: new Set(),
    registroEmEdicaoId: null,
    resultadoEmEdicao: ""
};

const estadoRelatorio = {
    dados: null,
    turmasExpandidas: new Set()
};

const estadoRav = {
    dados: null
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
    alvo.setAttribute("role", erro ? "alert" : "status");
    alvo.setAttribute("aria-live", erro ? "assertive" : "polite");
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
    const valor = String(status || "").trim().toUpperCase();
    if (valor === "ABERTO") return "Aberto";
    if (valor === "EM_REAVALIACAO") return "Em reavaliação";
    return "Encerrado";
}

function periodoEmReavaliacao(periodo = periodoDocenteAtual()) {
    return String(periodo?.status || "").trim().toUpperCase() === "EM_REAVALIACAO";
}

function atualizarModoDocente() {
    estadoDocente.modo = periodoEmReavaliacao() ? "reavaliacao" : "registro";
    const emReavaliacao = estadoDocente.modo === "reavaliacao";
    const filtroStatus = el("preconselhoStatusEstudante");
    if (emReavaliacao) filtroStatus.value = "sinalizados";
    el("preconselhoStatusEstudanteField").hidden = emReavaliacao;
    el("formFiltrosEstudantesDocente").dataset.state = estadoDocente.modo;
    el("listaEstudantesDocente").dataset.state = estadoDocente.modo;
    el("preconselhoListaEstudantesTitulo").textContent = emReavaliacao
        ? "Estudantes para reavaliação"
        : "Lista de estudantes";
    el("preconselhoListaEstudantesDescricao").hidden = emReavaliacao;
    el("preconselhoListaEstudantesDescricao").textContent = emReavaliacao
        ? ""
        : "Busque por nome, filtre por situação e clique no estudante para abrir a janela de sinalização.";

    const modal = el("preconselhoModalEditor");
    modal.dataset.state = estadoDocente.modo;
    el("preconselhoModalEyebrow").textContent = emReavaliacao ? "Etapa de reavaliação" : "Registro individual";
    el("preconselhoModalTitulo").textContent = emReavaliacao ? "Reavaliar estudante" : "Parecer por estudante";
    el("preconselhoModalDescricao").hidden = emReavaliacao;
    el("preconselhoModalDescricao").textContent = emReavaliacao
        ? ""
        : "Preencha os relatos, selecione os motivos e salve para aplicar a sinalização do estudante.";
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

function obterHabilidadesRavContexto() {
    return Array.isArray(contextoAtual?.rav_habilidades) ? contextoAtual.rav_habilidades : [];
}

function obterHabilidadesRavPorDisciplina(disciplinaId, incluirInativas = false, periodoId = null, turmaId = null) {
    return obterHabilidadesRavContexto().filter((item) =>
        Number(item.disciplina_id || 0) === Number(disciplinaId || 0) &&
        (!periodoId || Number(item.periodo_id || 0) === Number(periodoId || 0)) &&
        (!turmaId || (Array.isArray(item.turma_ids) && item.turma_ids.map(Number).includes(Number(turmaId || 0)))) &&
        (incluirInativas || Number(item.ativo ?? 1) === 1)
    );
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
        estudante_em_rav: Boolean(registro.estudante_em_rav),
        rav_habilidade_ids: Array.isArray(registro.rav_habilidade_ids)
            ? registro.rav_habilidade_ids
            : [],
        rav_habilidades: Array.isArray(registro.rav_habilidades)
            ? registro.rav_habilidades
            : [],
        rav_acoes: String(registro.rav_acoes || "")
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

function obterHabilidadesRavSelecionadasDocente() {
    return Array.from(document.querySelectorAll("[data-rav-habilidade-selecionada-id]"))
        .map((item) => Number(item.dataset.ravHabilidadeSelecionadaId || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0);
}

function aplicarSelecaoHabilidadesRavDocente(habilidadeIds = []) {
    renderizarHabilidadesRavDocente(habilidadeIds);
}

function filtrarHabilidadesRavDocente(termo = "", limite = 12) {
    const combo = comboDocenteAtual();
    const termoLimpo = String(termo || "").trim().toLowerCase();
    const selecionados = new Set(obterHabilidadesRavSelecionadasDocente());
    const habilidades = obterHabilidadesRavPorDisciplina(
        combo?.disciplina_id,
        false,
        estadoDocente.periodoId,
        combo?.turma_id
    )
        .filter((item) => !selecionados.has(Number(item.id || 0)));

    const filtradas = termoLimpo
        ? habilidades.filter((item) =>
            String(`${item.codigo || ""} ${item.descricao || ""}`).toLowerCase().includes(termoLimpo)
        )
        : habilidades;
    return filtradas.slice(0, limite);
}

function ocultarSugestoesHabilidadesRav() {
    const sugestoes = el("preconselhoRavSugestoesHabilidades");
    if (!sugestoes) {
        return;
    }
    sugestoes.innerHTML = "";
    sugestoes.hidden = true;
}

function renderizarSugestoesHabilidadesRav(forcar = false) {
    const sugestoes = el("preconselhoRavSugestoesHabilidades");
    const input = el("preconselhoRavBuscaHabilidade");
    if (!sugestoes || !input) {
        return;
    }

    const termo = String(input.value || "").trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoesHabilidadesRav();
        return;
    }

    const itens = filtrarHabilidadesRavDocente(termo);
    sugestoes.innerHTML = "";
    if (itens.length === 0) {
        const vazio = document.createElement("div");
        vazio.className = "preconselho-rav-suggestion-empty";
        vazio.textContent = "Nenhuma habilidade encontrada para este periodo, turma e disciplina.";
        sugestoes.appendChild(vazio);
        sugestoes.hidden = false;
        return;
    }

    itens.forEach((habilidade) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "preconselho-rav-suggestion";
        botao.dataset.ravHabilidadeId = String(Number(habilidade.id || 0));
        botao.textContent = [habilidade.codigo, habilidade.descricao].filter(Boolean).join(" - ");
        botao.addEventListener("click", () => {
            const ids = obterHabilidadesRavSelecionadasDocente();
            const habilidadeId = Number(habilidade.id || 0);
            if (habilidadeId > 0 && !ids.includes(habilidadeId)) {
                aplicarSelecaoHabilidadesRavDocente([...ids, habilidadeId]);
            }
            input.value = "";
            ocultarSugestoesHabilidadesRav();
            atualizarEstadoFormularioDocente();
            agendarPreviewDocente();
            input.focus();
        });
        sugestoes.appendChild(botao);
    });
    sugestoes.hidden = false;
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
    const detalhes = el("preconselhoRavDetalhesField");
    const checkbox = el("preconselhoEstudanteEmRav");
    const visivel = periodoTemRav();
    if (campo) {
        campo.hidden = !visivel;
    }
    if (detalhes) {
        detalhes.hidden = !visivel || !Boolean(checkbox?.checked);
        if (detalhes.hidden) {
            ocultarSugestoesHabilidadesRav();
        }
    }
    if (!visivel && checkbox) {
        checkbox.checked = false;
        aplicarSelecaoHabilidadesRavDocente([]);
        if (el("preconselhoRavAcoes")) {
            el("preconselhoRavAcoes").value = "";
        }
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
    const controles = obterControlesFocaveisModal();
    const primeiroControle = controles.find((item) => item.closest("#formRegistroDocente")) || controles[0] || painel;
    if (!primeiroControle || typeof primeiroControle.focus !== "function") {
        return;
    }

    try {
        primeiroControle.focus({ preventScroll: true });
    } catch (_erro) {
        primeiroControle.focus();
    }
}

function obterControlesFocaveisModal() {
    const painel = el("preconselhoPainelEditor");
    if (!painel) return [];
    return Array.from(painel.querySelectorAll(
        'button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((item) => !item.hidden && item.getClientRects().length > 0);
}

function prenderFocoNoModal(event) {
    if (event.key !== "Tab" || !modalRegistroDocenteAberto()) return;
    const controles = obterControlesFocaveisModal();
    if (controles.length === 0) {
        event.preventDefault();
        el("preconselhoPainelEditor")?.focus();
        return;
    }
    const primeiro = controles[0];
    const ultimo = controles[controles.length - 1];
    if (!el("preconselhoPainelEditor")?.contains(document.activeElement)) {
        event.preventDefault();
        primeiro.focus();
    } else if (event.shiftKey && document.activeElement === primeiro) {
        event.preventDefault();
        ultimo.focus();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
        event.preventDefault();
        primeiro.focus();
    }
}

function definirEstadoSalvamentoModal(salvando) {
    modalDocenteSalvando = Boolean(salvando);
    el("preconselhoPainelEditor")?.setAttribute("aria-busy", salvando ? "true" : "false");
    const botaoRegistro = el("btnSalvarRegistroDocente");
    const botaoReavaliacao = el("btnSalvarReavaliacao");
    if (botaoRegistro) {
        botaoRegistro.textContent = salvando ? "Salvando..." : "Salvar registro";
        if (salvando) botaoRegistro.disabled = true;
    }
    if (botaoReavaliacao) {
        botaoReavaliacao.textContent = salvando ? "Salvando..." : "Salvar reavaliação";
        if (salvando) botaoReavaliacao.disabled = true;
    }
    if (!salvando) atualizarEstadoFormularioDocente();
}

function abrirModalRegistroDocente() {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return;
    }

    atualizarModoDocente();
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

function fecharModalRegistroDocente({ limparFormulario = true, restaurarFoco = true, forcar = false } = {}) {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return false;
    }
    if (modalDocenteSalvando && !forcar) {
        return false;
    }
    if (!forcar && modalDocenteAlterado && !window.confirm("Descartar as alterações não salvas?")) {
        return false;
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
    modalDocenteAlterado = false;
    return true;
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
    el("preconselhoEstudanteEmRav").checked = false;
    el("preconselhoRavBuscaHabilidade").value = "";
    el("preconselhoRavAcoes").value = "";
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => { radio.checked = false; });
    el("preconselhoObservacaoReavaliacao").value = "";
    el("preconselhoMotivosReavaliacao").innerHTML = "";
    aplicarSelecaoMotivosDocente([]);
    aplicarSelecaoHabilidadesRavDocente([]);
    renderizarHabilidadesRavDocente();
    el("preconselhoTextoPreview").value = "";
    el("preconselhoPreviewAjuda").textContent = "Selecione um estudante e marque os motivos para gerar a pré-visualização.";
    atualizarStatusSinalizacaoDocente();
    atualizarVisibilidadeRavDocente();
    atualizarEstadoFormularioDocente();
    renderizarEstudantesDocente();
    modalDocenteAlterado = false;
}

function definirBotoesDocenteHabilitados() {
    const periodo = periodoDocenteAtual();
    const registro = registroDocenteAtual();
    const possuiEstudante = Number(estadoDocente.estudanteId || 0) > 0;
    const podeEditar = Boolean(periodo?.editavel);
    const camposHabilitados = possuiEstudante && podeEditar;
    const podeReavaliar = possuiEstudante && Boolean(registro) && periodoEmReavaliacao(periodo);

    el("preconselhoNivelAtencao").disabled = !camposHabilitados;
    el("preconselhoObservacaoProfessor").disabled = !camposHabilitados;
    el("preconselhoEstudanteEmRav").disabled = !camposHabilitados || !periodoTemRav(periodo);
    el("preconselhoRavAcoes").disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    el("preconselhoRavBuscaHabilidade").disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    document.querySelectorAll(".preconselho-motivo-checkbox").forEach((checkbox) => {
        checkbox.disabled = !camposHabilitados;
    });
    document.querySelectorAll("[data-action='remover-habilidade-rav']").forEach((botao) => {
        botao.disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    });
    el("btnSalvarRegistroDocente").disabled = modalDocenteSalvando || !possuiEstudante || !podeEditar;
    el("btnExcluirRegistroDocente").disabled = !registro || !podeEditar;
    el("preconselhoReavaliacaoField").hidden = !periodoEmReavaliacao(periodo) || !registro;
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"], .preconselho-review-reason').forEach((campo) => {
        campo.disabled = !podeReavaliar;
    });
    el("preconselhoObservacaoReavaliacao").disabled = !podeReavaliar;
    el("btnSalvarReavaliacao").disabled = modalDocenteSalvando || !podeReavaliar;

    if (!possuiEstudante) {
        el("preconselhoPreviewAjuda").textContent = "Selecione um estudante para preencher o formulário.";
        return;
    }
    if (!podeEditar && !podeReavaliar) {
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

function renderizarMotivosReavaliacao() {
    const container = el("preconselhoMotivosReavaliacao");
    const resultado = document.querySelector('[name="preconselhoResultadoReavaliacao"]:checked')?.value || "";
    const registro = registroDocenteAtual();
    const catalogo = contextoAtual?.motivos_pos_preconselho?.[resultado] || [];
    const selecionados = new Set(registro?.pos_preconselho_motivo_ids || []);
    container.innerHTML = catalogo.length
        ? catalogo.map((motivo) => `<label><input class="preconselho-review-reason" type="checkbox" value="${escaparHtml(motivo.id || "")}" ${selecionados.has(String(motivo.id || "")) ? "checked" : ""}> <span>${escaparHtml(motivo.descricao || "")}</span></label>`).join("")
        : (resultado ? '<p class="pcpi-hint">Nenhum motivo disponível.</p>' : "");
    atualizarEstadoFormularioDocente();
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
    const mostrarRav = Boolean(contextoAtual?.pode_relatorio);
    const mostrarConfiguracoes = Boolean(contextoAtual?.pode_configurar);

    el("tabBtnDocente").hidden = !mostrarDocente;
    el("tabBtnConsolidacao").hidden = !mostrarConsolidacao;
    el("tabBtnReavaliacao").hidden = !mostrarConsolidacao;
    el("tabBtnRelatorio").hidden = !mostrarRelatorio;
    el("tabBtnRav").hidden = !mostrarRav;
    el("tabBtnConfiguracoes").hidden = !mostrarConfiguracoes;

    const ordem = [
        { aba: "docente", visivel: mostrarDocente },
        { aba: "consolidacao", visivel: mostrarConsolidacao },
        { aba: "reavaliacao", visivel: mostrarConsolidacao },
        { aba: "relatorio", visivel: mostrarRelatorio },
        { aba: "rav", visivel: mostrarRav },
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
        botao.tabIndex = ativa ? 0 : -1;
    });

    document.querySelectorAll("[data-preconselho-tab-panel]").forEach((painel) => {
        const ativo = painel.dataset.preconselhoTabPanel === abaAtiva;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

function renderizarSelectPeriodos() {
    const periodos = obterPeriodos();
    if (!estadoDocente.periodoId && periodos.length > 0) {
        const periodoReavaliacao = periodos.find(
            (item) => String(item.status || "").toUpperCase() === "EM_REAVALIACAO"
        );
        const periodoAberto = periodos.find(
            (item) => String(item.status || "").toUpperCase() === "ABERTO"
        );
        estadoDocente.periodoId = Number(periodoReavaliacao?.id || periodoAberto?.id || periodos[0].id);
    }

    preencherSelect(
        el("preconselhoPeriodoDocente"),
        periodos,
        (item) => item.id,
        (item) => `${rotuloPeriodo(item)} - ${rotuloStatusPeriodo(item.status).toLowerCase()}`,
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

    preencherSelect(
        el("preconselhoPeriodoRav"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um periodo",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoRav")?.value || periodos[0]?.id || ""
        }
    );

    if (estadoDocente.periodoId) {
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

    preencherSelect(
        el("preconselhoTurmaReavaliacao"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaReavaliacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoProfessorReavaliacao"),
        Array.isArray(contextoAtual?.professores) ? contextoAtual.professores : [],
        (item) => item.id,
        (item) => item.label || item.nome,
        "Todos os professores",
        {
            valorSelecionado: el("preconselhoProfessorReavaliacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoTurmaRav"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaRav")?.value || ""
        }
    );
}

function renderizarSelectDisciplinaHabilidadeRav() {
    preencherSelect(
        el("preconselhoRavHabilidadePeriodo"),
        obterPeriodos(),
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione o periodo",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoRavHabilidadePeriodo")?.value || obterPeriodos()[0]?.id || ""
        }
    );
    preencherSelect(
        el("preconselhoRavImportPeriodo"),
        obterPeriodos(),
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Periodo informado no JSON",
        {
            valorSelecionado: el("preconselhoRavImportPeriodo")?.value || ""
        }
    );
    preencherSelect(
        el("preconselhoRavHabilidadeDisciplina"),
        Array.isArray(contextoAtual?.disciplinas) ? contextoAtual.disciplinas : [],
        (item) => item.id,
        (item) => item.nome,
        "Selecione a disciplina",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoRavHabilidadeDisciplina")?.value || ""
        }
    );
    const selectTurmas = el("preconselhoRavHabilidadeTurmas");
    const selecionadas = new Set(Array.from(selectTurmas?.selectedOptions || []).map((option) => option.value));
    if (selectTurmas) {
        selectTurmas.innerHTML = "";
        (Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : []).forEach((turma) => {
            const option = document.createElement("option");
            option.value = String(turma.id);
            option.textContent = String(turma.nome || "");
            option.selected = selecionadas.has(option.value);
            selectTurmas.appendChild(option);
        });
        selectTurmas.disabled = selectTurmas.options.length === 0;
    }
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

function renderizarHabilidadesRavDocente(habilidadeIdsSelecionadas = null) {
    const container = el("preconselhoRavHabilidadesDocente");
    if (!container) {
        return;
    }

    const combo = comboDocenteAtual();
    const selecionados = new Set(
        Array.isArray(habilidadeIdsSelecionadas)
            ? habilidadeIdsSelecionadas.map((item) => Number(item))
            : obterHabilidadesRavSelecionadasDocente()
    );
    const habilidades = obterHabilidadesRavPorDisciplina(
        combo?.disciplina_id,
        false,
        estadoDocente.periodoId,
        combo?.turma_id
    );

    if (!combo) {
        container.innerHTML = '<p class="preconselho-rav-empty">Selecione uma turma e disciplina para buscar habilidades.</p>';
        ocultarSugestoesHabilidadesRav();
        return;
    }
    if (habilidades.length === 0) {
        container.innerHTML = '<p class="preconselho-rav-empty">Nenhuma habilidade ativa cadastrada para este periodo, turma e disciplina.</p>';
        ocultarSugestoesHabilidadesRav();
        return;
    }

    const itensSelecionados = habilidades.filter((habilidade) => selecionados.has(Number(habilidade.id || 0)));
    if (itensSelecionados.length === 0) {
        container.innerHTML = '<p class="preconselho-rav-empty">Nenhuma habilidade selecionada ainda.</p>';
        renderizarSugestoesHabilidadesRav(false);
        return;
    }

    container.innerHTML = itensSelecionados.map((habilidade) => `
        <article class="preconselho-rav-skill-card" data-rav-habilidade-selecionada-id="${Number(habilidade.id)}">
            <span>${escaparHtml([habilidade.codigo, habilidade.descricao].filter(Boolean).join(" - "))}</span>
            <button type="button" data-action="remover-habilidade-rav" data-habilidade-id="${Number(habilidade.id)}">Remover</button>
        </article>
    `).join("");
    renderizarSugestoesHabilidadesRav(false);
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
                aria-pressed="${ativo ? "true" : "false"}"
                data-turma-id="${Number(item.turma_id)}"
                data-disciplina-id="${Number(item.disciplina_id)}">
                <strong>${escaparHtml(item.turma_nome || "")} • ${escaparHtml(item.disciplina_nome || "")}</strong>
                <span>${Number(item.total_estudantes || 0)} estudante(s)</span>
                <small>${Number(item.total_sinalizados || 0)} sinalizado(s)</small>
            </button>
        `;
    }).join("");
}

function levarProfessorParaListaEstudantes() {
    const secao = el("preconselhoSecaoEstudantes");
    if (!secao || !window.matchMedia("(max-width: 980px)").matches) return;

    const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => {
        secao.scrollIntoView({
            behavior: reduzirMovimento ? "auto" : "smooth",
            block: "start"
        });
    });
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
        lista.innerHTML = criarEstadoVazio(
            estadoDocente.modo === "reavaliacao"
                ? "Nenhum estudante foi sinalizado nesta turma e disciplina."
                : "Nenhum estudante encontrado para os filtros aplicados."
        );
        el("preconselhoResumoEstudantesDocente").textContent = `${combo.turma_nome} • ${combo.disciplina_nome}`;
        return;
    }

    const trilho = lista.closest(".preconselho-rail-scroll");
    const scrollAnterior = trilho?.scrollTop || 0;
    lista.innerHTML = estadoDocente.estudantes.map((item) => {
        const selecionado = Number(item.estudante_id) === Number(estadoDocente.estudanteId);
        const nivel = rotuloNivelAtencao(item.nivel_atencao);
        const statusReavaliacao = item.pos_preconselho_recuperado === true
            ? "Recuperado"
            : (item.pos_preconselho_recuperado === false ? "Ficou para o conselho" : "Reavaliação pendente");
        const classeStatusReavaliacao = item.pos_preconselho_recuperado === true
            ? "pcpi-chip-status-recuperado"
            : (item.pos_preconselho_recuperado === false ? "pcpi-chip-status-conselho" : "pcpi-chip-status-pendente");
        const classeCardReavaliacao = estadoDocente.modo === "reavaliacao"
            ? (item.pos_preconselho_recuperado === true
                ? "preconselho-card-status-recuperado"
                : (item.pos_preconselho_recuperado === false
                    ? "preconselho-card-status-conselho"
                    : "preconselho-card-status-pendente"))
            : "";
        const descricaoItem = estadoDocente.modo === "reavaliacao"
            ? ""
            : (item.sinalizado
                ? `${item.motivos.length} motivo(s) selecionado(s)`
                    + (nivel ? ` • Atenção ${nivel}` : "")
                    + (item.motivos.length ? `\n${item.motivos.map((m) => `- ${m.descricao || ""}`).join("\n")}` : "")
                : "Clique para abrir um relato.");
        return `
            <li class="pcpi-item ${item.sinalizado ? "pcpi-item-manual" : "pcpi-item-automatico"} ${classeCardReavaliacao}">
                <button type="button" class="preconselho-list-button ${selecionado ? "is-active" : ""}" aria-pressed="${selecionado ? "true" : "false"}" data-estudante-id="${Number(item.estudante_id)}">
                    <span class="preconselho-list-button-top">
                        <strong>${escaparHtml(item.nome || "")}</strong>
                        <span class="pcpi-tag-group">
                            ${estadoDocente.modo === "registro" ? `<span class="pcpi-chip ${item.sinalizado ? "pcpi-chip-manual" : "pcpi-chip-automatico"}">${item.sinalizado ? "Sinalizado" : "Estudante Ok"}</span>` : ""}
                            ${periodoEmReavaliacao() && item.sinalizado ? `<span class="pcpi-chip ${classeStatusReavaliacao}">${escaparHtml(statusReavaliacao)}</span>` : ""}
                        </span>
                    </span>
                    ${descricaoItem ? `<span class="pcpi-item-note">${escaparHtml(descricaoItem)}</span>` : ""}
                </button>
            </li>
        `;
    }).join("");
    if (trilho) trilho.scrollTop = scrollAnterior;

    const total = estadoDocente.estudantes.length;
    const totalSinalizados = estadoDocente.estudantes.filter((item) => item.sinalizado).length;
    el("preconselhoResumoEstudantesDocente").textContent = estadoDocente.modo === "reavaliacao"
        ? `${combo.turma_nome} • ${combo.disciplina_nome} • ${total} estudante(s) para reavaliação.`
        : `${combo.turma_nome} • ${combo.disciplina_nome} • ${total} estudante(s), ${totalSinalizados} sinalizado(s).`;
}

function aplicarReavaliacaoNoEstado(registroAtualizado) {
    const registroAnterior = estadoDocente.registros.find(
        (item) => Number(item.id) === Number(registroAtualizado?.id)
    ) || {};
    const registro = {
        ...registroAnterior,
        ...registroAtualizado,
        motivo_ids: Array.isArray(registroAtualizado?.motivo_ids) ? registroAtualizado.motivo_ids : (registroAnterior.motivo_ids || []),
        motivos: Array.isArray(registroAtualizado?.motivos) ? registroAtualizado.motivos : (registroAnterior.motivos || []),
        pos_preconselho_motivo_ids: Array.isArray(registroAtualizado?.pos_preconselho_motivo_ids) ? registroAtualizado.pos_preconselho_motivo_ids : [],
        pos_preconselho_motivos: Array.isArray(registroAtualizado?.pos_preconselho_motivos) ? registroAtualizado.pos_preconselho_motivos : [],
    };
    estadoDocente.registros = estadoDocente.registros.map((item) =>
        Number(item.id) === Number(registro.id) ? registro : item
    );
    estadoDocente.estudantes = estadoDocente.estudantes.map((item) =>
        Number(item.estudante_id) === Number(registro.estudante_id)
            ? {
                ...item,
                pos_preconselho_recuperado: registro.pos_preconselho_recuperado,
                pos_preconselho_motivo_ids: registro.pos_preconselho_motivo_ids,
                pos_preconselho_motivos: registro.pos_preconselho_motivos,
                pos_preconselho_observacao: registro.pos_preconselho_observacao,
            }
            : item
    );
    renderizarEstudantesDocente();
    renderizarRegistrosDocente();
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
    const resultadoReavaliacao = estudante.pos_preconselho_recuperado === true
        ? "recuperado"
        : (estudante.pos_preconselho_recuperado === false ? "nao_recuperado" : "");
    el("preconselhoEstudanteSelecionadoMeta").textContent = estadoDocente.modo === "reavaliacao"
        ? `${estudante.turma_nome || ""} • ${comboDocenteAtual()?.disciplina_nome || ""} • ${resultadoReavaliacao ? "Reavaliação já registrada" : "Reavaliação pendente"}.`
        : estudante.sinalizado
        ? `${estudante.turma_nome || ""} • Registro já salvo para a seleção atual.`
        : `${estudante.turma_nome || ""} • Ainda não sinalizado neste período e disciplina.`;
    el("preconselhoSinalizarEstudante").checked = true;
    el("preconselhoNivelAtencao").value = String(estudante.nivel_atencao || "");
    el("preconselhoObservacaoProfessor").value = String(estudante.observacao_professor || "");
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => {
        radio.checked = radio.value === resultadoReavaliacao;
    });
    el("preconselhoObservacaoReavaliacao").value = String(estudante.pos_preconselho_observacao || "");
    el("preconselhoEstudanteEmRav").checked = periodoTemRav() && Boolean(estudante.estudante_em_rav);
    el("preconselhoRavBuscaHabilidade").value = "";
    el("preconselhoRavAcoes").value = String(estudante.rav_acoes || "");
    aplicarSelecaoMotivosDocente(estudante.motivo_ids || []);
    renderizarHabilidadesRavDocente();
    aplicarSelecaoHabilidadesRavDocente(estudante.rav_habilidade_ids || []);
    renderizarMotivosReavaliacao();
    atualizarStatusSinalizacaoDocente({
        possuiEstudante: true,
        possuiRegistro: Boolean(estudante.sinalizado),
    });
    atualizarVisibilidadeRavDocente();

    renderizarEstudantesDocente();
    atualizarEstadoFormularioDocente();
    void atualizarPreviewDocente();
    modalDocenteAlterado = false;
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
                pos_preconselho_recuperado: null,
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: "",
                estudante_em_rav: periodoTemRav() && Boolean(el("preconselhoEstudanteEmRav").checked),
                rav_habilidade_ids: obterHabilidadesRavSelecionadasDocente(),
                rav_acoes: String(el("preconselhoRavAcoes").value || "").trim(),
                estudante_nome: String(estudante?.nome || "").trim(),
                estudante_sexo: estudante?.sexo || null,
                periodo_id: Number(estadoDocente.periodoId || 0) || null,
                turma_id: Number(combo?.turma_id || 0) || null,
                disciplina_id: Number(combo?.disciplina_id || 0) || null,
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

    atualizarModoDocente();
    const params = new URLSearchParams({
        periodo_id: String(estadoDocente.periodoId),
        turma_id: String(combo.turma_id),
        disciplina_id: String(combo.disciplina_id),
        q: String(el("preconselhoBuscaEstudante").value || "").trim(),
        status: estadoDocente.modo === "reavaliacao"
            ? "sinalizados"
            : String(el("preconselhoStatusEstudante").value || "todos")
    });

    if (buscaEstudanteController) buscaEstudanteController.abort();
    buscaEstudanteController = new AbortController();
    const sequenciaAtual = ++buscaEstudanteSequencia;
    let resposta;
    try {
        resposta = await fetchComAuth(`/preconselho/estudantes?${params.toString()}`, {
            headers,
            signal: buscaEstudanteController.signal
        });
    } catch (erro) {
        if (erro?.name === "AbortError") return;
        throw erro;
    }
    if (sequenciaAtual !== buscaEstudanteSequencia) return;
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os estudantes."));
    }

    const estudantes = await resposta.json();
    if (sequenciaAtual !== buscaEstudanteSequencia) return;
    estadoDocente.estudantes = estudantes;
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
        atualizarModoDocente();
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

function statusDisciplinaReavaliacao(registro) {
    if (registro.pos_preconselho_recuperado === true) {
        return { rotulo: "Recuperado", classe: "is-recuperado" };
    }
    if (registro.pos_preconselho_recuperado === false) {
        return { rotulo: "Ficou para o conselho", classe: "is-conselho" };
    }
    return { rotulo: "Em reavaliação", classe: "is-pendente" };
}

function resultadoRegistroReavaliacao(registro) {
    if (registro?.pos_preconselho_recuperado === true) return "recuperado";
    if (registro?.pos_preconselho_recuperado === false) return "nao_recuperado";
    return "";
}

function renderizarEditorGestaoReavaliacao(registro) {
    const resultado = estadoPainelReavaliacao.resultadoEmEdicao;
    const motivos = Array.isArray(contextoAtual?.motivos_pos_preconselho?.[resultado])
        ? contextoAtual.motivos_pos_preconselho[resultado]
        : [];
    const selecionados = new Set(registro.pos_preconselho_motivo_ids || []);
    return `
        <form class="preconselho-review-manager-form" data-form-reavaliacao-id="${Number(registro.id)}">
            <fieldset>
                <legend>Resultado da reavaliação</legend>
                <label><input type="radio" name="resultadoGestaoReavaliacao" value="recuperado" ${resultado === "recuperado" ? "checked" : ""}> Recuperado</label>
                <label><input type="radio" name="resultadoGestaoReavaliacao" value="nao_recuperado" ${resultado === "nao_recuperado" ? "checked" : ""}> Ficou para o conselho</label>
            </fieldset>
            <fieldset class="preconselho-review-manager-reasons" ${resultado ? "" : "hidden"}>
                <legend>Motivos</legend>
                ${motivos.map((motivo) => `<label><input type="checkbox" name="motivoGestaoReavaliacao" value="${escaparHtml(motivo.id || "")}" ${selecionados.has(String(motivo.id || "")) ? "checked" : ""}> ${escaparHtml(motivo.descricao || "")}</label>`).join("") || "<p>Nenhum motivo disponível para este resultado.</p>"}
            </fieldset>
            <label class="pcpi-field">
                <span>Observação (opcional)</span>
                <textarea name="observacaoGestaoReavaliacao" rows="3" maxlength="1000">${escaparHtml(registro.pos_preconselho_observacao || "")}</textarea>
            </label>
            <p class="pcpi-hint">Registro originalmente atribuído a ${escaparHtml(registro.professor_nome || "professor não informado")}.</p>
            <div class="pcpi-inline-actions">
                <button class="btn-destaque" type="submit">Salvar reavaliação</button>
                <button type="button" data-action="cancelar-reavaliacao-gestao">Cancelar</button>
            </div>
            <p class="pcpi-status-copy" data-msg-reavaliacao-id="${Number(registro.id)}"></p>
        </form>`;
}

function agruparRegistrosPainelReavaliacao(registros) {
    const grupos = new Map();
    registros.forEach((registro) => {
        const chave = String(registro.estudante_id || registro.estudante_nome || "");
        const grupo = grupos.get(chave) || {
            id: registro.estudante_id,
            nome: registro.estudante_nome || "Estudante sem nome",
            turma: registro.turma_nome || "Turma não informada",
            disciplinas: []
        };
        grupo.disciplinas.push(registro);
        grupos.set(chave, grupo);
    });
    return Array.from(grupos.values()).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

function renderizarPainelReavaliacao() {
    const container = el("listaPainelReavaliacao");
    const periodo = estadoPainelReavaliacao.periodo;
    const estudantes = agruparRegistrosPainelReavaliacao(estadoPainelReavaliacao.registros);
    el("preconselhoReavaliacaoPeriodoNome").textContent = periodo ? rotuloPeriodo(periodo) : "Nenhum período ativo";

    if (!periodo) {
        el("preconselhoResumoPainelReavaliacao").textContent = "Inicie a reavaliação de um período para habilitar este painel.";
        container.innerHTML = '<p class="preconselho-empty-state">Não há período em reavaliação no momento.</p>';
        return;
    }
    if (estudantes.length === 0) {
        el("preconselhoResumoPainelReavaliacao").textContent = "Nenhum estudante encontrado para o filtro aplicado.";
        container.innerHTML = '<p class="preconselho-empty-state">Nenhum estudante está em reavaliação nesta turma.</p>';
        return;
    }

    const totalDisciplinas = estudantes.reduce((total, estudante) => total + estudante.disciplinas.length, 0);
    el("preconselhoResumoPainelReavaliacao").textContent = `${estudantes.length} estudante(s) • ${totalDisciplinas} disciplina(s) sinalizada(s).`;
    container.innerHTML = estudantes.map((estudante) => {
        const chave = String(estudante.id || estudante.nome);
        const expandido = estadoPainelReavaliacao.estudantesExpandidos.has(chave);
        const disciplinas = estudante.disciplinas
            .slice()
            .sort((a, b) => String(a.disciplina_nome || "").localeCompare(String(b.disciplina_nome || ""), "pt-BR"));
        return `
            <section class="preconselho-review-student">
                <button type="button" class="preconselho-review-student-toggle"
                    data-estudante-reavaliacao="${escaparHtml(chave)}" aria-expanded="${expandido ? "true" : "false"}">
                    <span><strong>${escaparHtml(estudante.nome)}</strong><small>${escaparHtml(estudante.turma)} • ${disciplinas.length} disciplina(s)</small></span>
                    <span class="preconselho-review-chevron" aria-hidden="true"></span>
                </button>
                <div class="preconselho-review-disciplines" ${expandido ? "" : "hidden"}>
                    ${disciplinas.map((disciplina) => {
                        const status = statusDisciplinaReavaliacao(disciplina);
                        return `<div class="preconselho-review-discipline">
                            <div class="preconselho-review-discipline-main">
                                <span>${escaparHtml(disciplina.disciplina_nome || "Disciplina não informada")}</span>
                                <small>${escaparHtml(disciplina.professor_nome || "Professor não informado")}</small>
                            </div>
                            <div class="preconselho-review-discipline-actions">
                                <strong class="preconselho-review-status ${status.classe}">${status.rotulo}</strong>
                                <button type="button" data-action="editar-reavaliacao-gestao" data-registro-id="${Number(disciplina.id)}">
                                    ${disciplina.pos_preconselho_recuperado === null ? "Registrar reavaliação" : "Alterar resultado"}
                                </button>
                            </div>
                            ${Number(estadoPainelReavaliacao.registroEmEdicaoId) === Number(disciplina.id) ? renderizarEditorGestaoReavaliacao(disciplina) : ""}
                        </div>`;
                    }).join("")}
                </div>
            </section>`;
    }).join("");
}

async function carregarPainelReavaliacao() {
    limparMensagem("msgPreconselhoReavaliacao");
    const periodo = obterPeriodos().find((item) => String(item.status || "").toUpperCase() === "EM_REAVALIACAO") || null;
    estadoPainelReavaliacao.periodo = periodo;
    estadoPainelReavaliacao.registros = [];
    if (!periodo) {
        renderizarPainelReavaliacao();
        return;
    }

    const params = new URLSearchParams({ periodo_id: String(periodo.id) });
    const turmaId = String(el("preconselhoTurmaReavaliacao")?.value || "").trim();
    const professorId = String(el("preconselhoProfessorReavaliacao")?.value || "").trim();
    if (turmaId) params.set("turma_id", turmaId);
    if (professorId) params.set("professor_id", professorId);
    try {
        const resposta = await fetchComAuth(`/preconselho/registros?${params.toString()}`, { headers });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar as reavaliações."));
        const dados = await resposta.json();
        estadoPainelReavaliacao.registros = Array.isArray(dados.itens) ? dados.itens : [];
        renderizarPainelReavaliacao();
    } catch (erro) {
        renderizarPainelReavaliacao();
        definirMensagem("msgPreconselhoReavaliacao", erro.message || "Não foi possível carregar as reavaliações.", true);
    }
}

async function salvarReavaliacaoGestao(form) {
    const registroId = Number(form.dataset.formReavaliacaoId || 0);
    const resultado = form.querySelector('[name="resultadoGestaoReavaliacao"]:checked')?.value || "";
    const motivoIds = Array.from(form.querySelectorAll('[name="motivoGestaoReavaliacao"]:checked')).map((item) => item.value);
    const observacao = String(form.querySelector('[name="observacaoGestaoReavaliacao"]')?.value || "").trim();
    const mensagem = form.querySelector("[data-msg-reavaliacao-id]");
    if (!resultado || motivoIds.length === 0) {
        mensagem.textContent = "Selecione o resultado e ao menos um motivo.";
        mensagem.dataset.state = "erro";
        return;
    }
    const botao = form.querySelector('button[type="submit"]');
    botao.disabled = true;
    botao.textContent = "Salvando...";
    try {
        const resposta = await fetchComAuth(`/preconselho/registros/${registroId}/reavaliacao`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({ recuperado: resultado === "recuperado", motivo_ids: motivoIds, observacao })
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar a reavaliação."));
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
        definirMensagem("msgPreconselhoReavaliacao", "Reavaliação registrada pela gestão com sucesso.");
    } catch (erro) {
        mensagem.textContent = erro.message || "Não foi possível salvar a reavaliação.";
        mensagem.dataset.state = "erro";
        botao.disabled = false;
        botao.textContent = "Salvar reavaliação";
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

function construirParametrosRav() {
    const params = new URLSearchParams({
        periodo_id: String(el("preconselhoPeriodoRav").value || "")
    });
    const turmaId = String(el("preconselhoTurmaRav").value || "").trim();
    if (turmaId) params.set("turma_id", turmaId);
    return params;
}

function modoVisualizacaoRav() {
    const modo = String(el("preconselhoModoRav")?.value || "estudante");
    return ["estudante", "disciplina", "habilidade"].includes(modo) ? modo : "estudante";
}

function chaveHabilidadeRav(habilidade) {
    return String(habilidade?.id || habilidade?.codigo || habilidade?.descricao || "").trim();
}

function rotuloHabilidadeRav(habilidade) {
    return [habilidade?.codigo, habilidade?.descricao].filter(Boolean).join(" - ");
}

function adicionarUnicoPorChave(mapa, chave, valor) {
    const chaveLimpa = String(chave || "").trim();
    if (chaveLimpa && !mapa.has(chaveLimpa)) {
        mapa.set(chaveLimpa, valor);
    }
}

function formatarListaRav(valores, vazio = "Nao informado") {
    const itens = Array.from(valores || []).map((valor) => String(valor || "").trim()).filter(Boolean);
    return itens.length ? itens.join("; ") : vazio;
}

function habilidadesRegistroRav(item) {
    return Array.isArray(item?.rav_habilidades) ? item.rav_habilidades : [];
}

function contarHabilidadesUnicasRav(itens) {
    const habilidades = new Set();
    itens.forEach((item) => {
        habilidadesRegistroRav(item).forEach((habilidade) => {
            const chave = chaveHabilidadeRav(habilidade);
            if (chave) habilidades.add(chave);
        });
    });
    return habilidades.size;
}

function renderizarBlocoRav(titulo, meta, habilidades, acoes, professor) {
    const mostrarHabilidades = habilidades !== null;
    const habilidadesTexto = mostrarHabilidades ? formatarListaRav(habilidades, "Nenhuma habilidade selecionada.") : "";
    const acoesTexto = formatarListaRav(acoes, "");
    const professorTexto = formatarListaRav(professor, "Nao informado");
    return `
        <div class="preconselho-rav-group-block">
            <div class="preconselho-rav-group-title">
                <strong>${escaparHtml(titulo)}</strong>
                ${meta ? `<span>${escaparHtml(meta)}</span>` : ""}
            </div>
            ${mostrarHabilidades ? `<p class="pcpi-item-note">${escaparHtml(`Habilidades: ${habilidadesTexto}`)}</p>` : ""}
            ${acoesTexto ? `<p class="pcpi-item-note is-secondary">${escaparHtml(`Acoes: ${acoesTexto}`)}</p>` : ""}
            <p class="pcpi-item-note is-secondary">${escaparHtml(`Professor: ${professorTexto}`)}</p>
        </div>
    `;
}

function agruparRavPorEstudante(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const estudanteId = String(item.estudante_id || item.estudante_nome || "");
        const grupo = grupos.get(estudanteId) || {
            nome: item.estudante_nome || "Estudante sem nome",
            turmas: new Map(),
            disciplinas: new Map()
        };
        adicionarUnicoPorChave(grupo.turmas, item.turma_id || item.turma_nome, item.turma_nome);

        const disciplinaId = String(item.disciplina_id || item.disciplina_nome || "");
        const disciplina = grupo.disciplinas.get(disciplinaId) || {
            nome: item.disciplina_nome || "Disciplina nao informada",
            habilidades: new Map(),
            acoes: new Map(),
            professores: new Map()
        };
        habilidadesRegistroRav(item).forEach((habilidade) => {
            adicionarUnicoPorChave(disciplina.habilidades, chaveHabilidadeRav(habilidade), rotuloHabilidadeRav(habilidade));
        });
        adicionarUnicoPorChave(disciplina.acoes, item.rav_acoes, item.rav_acoes);
        adicionarUnicoPorChave(disciplina.professores, item.professor_id || item.professor_nome, item.professor_nome);

        grupo.disciplinas.set(disciplinaId, disciplina);
        grupos.set(estudanteId, grupo);
    });
    return Array.from(grupos.values());
}

function agruparRavPorDisciplina(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const disciplinaId = String(item.disciplina_id || item.disciplina_nome || "");
        const grupo = grupos.get(disciplinaId) || {
            nome: item.disciplina_nome || "Disciplina nao informada",
            estudantes: new Map()
        };
        const estudanteId = String(item.estudante_id || item.estudante_nome || "");
        const estudante = grupo.estudantes.get(estudanteId) || {
            nome: item.estudante_nome || "Estudante sem nome",
            turma: item.turma_nome || "",
            habilidades: new Map(),
            acoes: new Map(),
            professores: new Map()
        };
        habilidadesRegistroRav(item).forEach((habilidade) => {
            adicionarUnicoPorChave(estudante.habilidades, chaveHabilidadeRav(habilidade), rotuloHabilidadeRav(habilidade));
        });
        adicionarUnicoPorChave(estudante.acoes, item.rav_acoes, item.rav_acoes);
        adicionarUnicoPorChave(estudante.professores, item.professor_id || item.professor_nome, item.professor_nome);

        grupo.estudantes.set(estudanteId, estudante);
        grupos.set(disciplinaId, grupo);
    });
    return Array.from(grupos.values());
}

function agruparRavPorHabilidade(itens) {
    const grupos = new Map();
    itens.forEach((item) => {
        const habilidades = habilidadesRegistroRav(item);
        const habilidadesDoRegistro = habilidades.length ? habilidades : [{ id: "sem-habilidade", descricao: "Sem habilidade selecionada" }];
        habilidadesDoRegistro.forEach((habilidade) => {
            const chave = chaveHabilidadeRav(habilidade) || "sem-habilidade";
            const grupo = grupos.get(chave) || {
                nome: rotuloHabilidadeRav(habilidade) || "Sem habilidade selecionada",
                estudantes: new Map()
            };
            const estudanteId = `${item.estudante_id || item.estudante_nome || ""}-${item.disciplina_id || item.disciplina_nome || ""}`;
            const estudante = grupo.estudantes.get(estudanteId) || {
                nome: item.estudante_nome || "Estudante sem nome",
                disciplina: item.disciplina_nome || "Disciplina nao informada",
                turma: item.turma_nome || "",
                acoes: new Map(),
                professores: new Map()
            };
            adicionarUnicoPorChave(estudante.acoes, item.rav_acoes, item.rav_acoes);
            adicionarUnicoPorChave(estudante.professores, item.professor_id || item.professor_nome, item.professor_nome);
            grupo.estudantes.set(estudanteId, estudante);
            grupos.set(chave, grupo);
        });
    });
    return Array.from(grupos.values());
}

function renderizarRavPorEstudante(itens) {
    return agruparRavPorEstudante(itens).map((grupo) => {
        const disciplinas = Array.from(grupo.disciplinas.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${disciplinas.length} disciplina(s)</span>
                            </div>
                        </div>
                        <p class="pcpi-item-line">${escaparHtml(formatarListaRav(grupo.turmas.values(), "Turma nao informada"))}</p>
                        <div class="preconselho-rav-group-list">
                            ${disciplinas.map((disciplina) => renderizarBlocoRav(
                                disciplina.nome,
                                "",
                                disciplina.habilidades.values(),
                                disciplina.acoes.values(),
                                disciplina.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRavPorDisciplina(itens) {
    return agruparRavPorDisciplina(itens).map((grupo) => {
        const estudantes = Array.from(grupo.estudantes.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${estudantes.length} estudante(s)</span>
                            </div>
                        </div>
                        <div class="preconselho-rav-group-list">
                            ${estudantes.map((estudante) => renderizarBlocoRav(
                                estudante.nome,
                                estudante.turma,
                                estudante.habilidades.values(),
                                estudante.acoes.values(),
                                estudante.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRavPorHabilidade(itens) {
    return agruparRavPorHabilidade(itens).map((grupo) => {
        const estudantes = Array.from(grupo.estudantes.values());
        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-checkbox-row">
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(grupo.nome)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">RAV</span>
                                <span class="pcpi-chip">${estudantes.length} ocorrencia(s)</span>
                            </div>
                        </div>
                        <div class="preconselho-rav-group-list">
                            ${estudantes.map((estudante) => renderizarBlocoRav(
                                estudante.nome,
                                [estudante.turma, estudante.disciplina].filter(Boolean).join(" | "),
                                null,
                                estudante.acoes.values(),
                                estudante.professores.values()
                            )).join("")}
                        </div>
                    </div>
                </div>
            </li>
        `;
    }).join("");
}

function renderizarRav() {
    const dados = estadoRav.dados;
    const lista = el("listaRavPreconselho");
    const turmaSelecionada = Array.from(el("preconselhoTurmaRav")?.options || [])
        .find((option) => option.value === String(el("preconselhoTurmaRav")?.value || ""));

    if (!dados) {
        el("preconselhoResumoRavEstudantes").textContent = "0";
        el("preconselhoResumoRavRegistros").textContent = "0";
        el("preconselhoResumoRavHabilidades").textContent = "0";
        el("preconselhoResumoRavTurma").textContent = turmaSelecionada?.textContent || "Todas";
        lista.innerHTML = criarEstadoVazio("Selecione um periodo para visualizar os estudantes em RAV.");
        return;
    }

    const itens = Array.isArray(dados.itens) ? dados.itens : [];
    el("preconselhoResumoRavEstudantes").textContent = String(Number(dados.total_estudantes || 0));
    el("preconselhoResumoRavRegistros").textContent = String(Number(dados.total_registros || 0));
    el("preconselhoResumoRavHabilidades").textContent = String(contarHabilidadesUnicasRav(itens));
    el("preconselhoResumoRavTurma").textContent = turmaSelecionada?.textContent || "Todas";

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum estudante em RAV para os filtros selecionados.");
        return;
    }

    const modo = modoVisualizacaoRav();
    if (modo === "disciplina") {
        lista.innerHTML = renderizarRavPorDisciplina(itens);
        return;
    }
    if (modo === "habilidade") {
        lista.innerHTML = renderizarRavPorHabilidade(itens);
        return;
    }
    lista.innerHTML = renderizarRavPorEstudante(itens);
}

async function carregarRav() {
    limparMensagem("msgPreconselhoRav");
    const periodoId = Number(el("preconselhoPeriodoRav").value || 0);
    if (!periodoId) {
        estadoRav.dados = null;
        renderizarRav();
        return;
    }

    try {
        const resposta = await fetchComAuth(`/preconselho/rav/turma?${construirParametrosRav().toString()}`, { headers });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel carregar a visualizacao de RAV."));
        }
        estadoRav.dados = await resposta.json();
        renderizarRav();
        definirMensagem("msgPreconselhoRav", "Visualizacao de RAV atualizada.");
    } catch (erro) {
        estadoRav.dados = null;
        renderizarRav();
        definirMensagem("msgPreconselhoRav", erro.message || "Nao foi possivel carregar a visualizacao de RAV.", true);
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
                        ${item.status === "ABERTO" ? "Iniciar reavaliação" : (item.status === "EM_REAVALIACAO" ? "Encerrar" : "Reabrir")}
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

function sincronizarCatalogoReavaliacao(itens) {
    contextoAtual.motivos_reavaliacao_admin = itens;
    contextoAtual.motivos_pos_preconselho = {
        recuperado: itens.filter((item) => item.resultado === "recuperado" && Number(item.ativo) === 1)
            .map((item) => ({ id: item.codigo, descricao: item.descricao })),
        nao_recuperado: itens.filter((item) => item.resultado === "nao_recuperado" && Number(item.ativo) === 1)
            .map((item) => ({ id: item.codigo, descricao: item.descricao })),
    };
}

function renderizarTabelaMotivosReavaliacao() {
    const tbody = el("tbodyMotivosReavaliacao");
    if (!tbody) return;
    const itens = contextoAtual?.motivos_reavaliacao_admin || [];
    tbody.innerHTML = itens.map((item) => `
        <tr>
            <td data-label="Resultado">${item.resultado === "recuperado" ? "Recuperado" : "Ficou para o conselho"}</td>
            <td data-label="Código">${escaparHtml(item.codigo || "")}</td>
            <td data-label="Descrição">${escaparHtml(item.descricao || "")}</td>
            <td data-label="Status">${Number(item.ativo) === 1 ? "Ativo" : "Inativo"}</td>
            <td data-label="Ações"><div class="preconselho-table-actions">
                <button type="button" data-action="editar-motivo-reavaliacao" data-id="${Number(item.id)}">Editar</button>
                <button type="button" data-action="status-motivo-reavaliacao" data-id="${Number(item.id)}" data-ativo="${Number(item.ativo)}">${Number(item.ativo) === 1 ? "Inativar" : "Ativar"}</button>
            </div></td>
        </tr>`).join("");
}

async function carregarMotivosReavaliacaoAdmin() {
    if (!contextoAtual?.pode_configurar) return;
    const resposta = await fetchComAuth("/preconselho/motivos-reavaliacao?incluir_inativos=true", { headers });
    if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os motivos da reavaliação."));
    sincronizarCatalogoReavaliacao(await resposta.json());
    renderizarTabelaMotivosReavaliacao();
}

function limparFormularioMotivoReavaliacao() {
    el("preconselhoMotivoReavaliacaoId").value = "";
    el("preconselhoMotivoReavaliacaoResultado").value = "recuperado";
    el("preconselhoMotivoReavaliacaoCodigo").value = "";
    el("preconselhoMotivoReavaliacaoCodigo").disabled = false;
    el("preconselhoMotivoReavaliacaoDescricao").value = "";
    el("preconselhoMotivoReavaliacaoOrdem").value = "0";
}

async function salvarMotivoReavaliacao(event) {
    event.preventDefault();
    limparMensagem("msgMotivoReavaliacao");
    const id = Number(el("preconselhoMotivoReavaliacaoId").value || 0);
    const payload = {
        resultado: el("preconselhoMotivoReavaliacaoResultado").value,
        descricao: el("preconselhoMotivoReavaliacaoDescricao").value.trim(),
        ordem: Number(el("preconselhoMotivoReavaliacaoOrdem").value || 0),
    };
    if (!id) payload.codigo = el("preconselhoMotivoReavaliacaoCodigo").value.trim();
    try {
        const resposta = await fetchComAuth(id ? `/preconselho/motivos-reavaliacao/${id}` : "/preconselho/motivos-reavaliacao", {
            method: id ? "PUT" : "POST", headers: headersJson, body: JSON.stringify(payload)
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o motivo."));
        await carregarMotivosReavaliacaoAdmin();
        limparFormularioMotivoReavaliacao();
        definirMensagem("msgMotivoReavaliacao", "Motivo salvo com sucesso.");
    } catch (erro) { definirMensagem("msgMotivoReavaliacao", erro.message, true); }
}

function renderizarTabelaHabilidadesRav() {
    const tbody = el("tbodyHabilidadesRavPreconselho");
    if (!tbody) {
        return;
    }

    const habilidades = obterHabilidadesRavContexto();
    if (habilidades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="booking-empty">Nenhuma habilidade de RAV cadastrada.</td></tr>';
        return;
    }

    tbody.innerHTML = habilidades.map((item) => `
        <tr>
            <td data-label="Periodo">
                <strong>${escaparHtml(item.periodo_nome || "")}</strong>
            </td>
            <td data-label="Disciplina">
                <strong>${escaparHtml(item.disciplina_nome || "")}</strong>
                <div class="preconselho-table-meta">Ordem ${Number(item.ordem || 0)}</div>
            </td>
            <td data-label="Codigo">
                ${escaparHtml(item.codigo || "")}
            </td>
            <td data-label="Habilidade">
                ${escaparHtml(item.descricao || "")}
            </td>
            <td data-label="Turmas">
                ${escaparHtml((Array.isArray(item.turmas) ? item.turmas : []).map((turma) => turma.nome).filter(Boolean).join(", "))}
            </td>
            <td data-label="Status">
                <span class="status-chip ${Number(item.ativo ?? 1) === 1 ? "status-aberto" : "status-fechado"}">
                    ${Number(item.ativo ?? 1) === 1 ? "Ativa" : "Inativa"}
                </span>
            </td>
            <td data-label="Acoes">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-habilidade-rav" data-habilidade-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-habilidade-rav" data-habilidade-id="${Number(item.id)}" data-ativo="${Number(item.ativo ?? 1)}">
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

function limparFormularioHabilidadeRav() {
    el("preconselhoRavHabilidadeEdicaoId").value = "";
    el("preconselhoRavHabilidadePeriodo").selectedIndex = 0;
    el("preconselhoRavHabilidadeDisciplina").selectedIndex = 0;
    el("preconselhoRavHabilidadeCodigo").value = "";
    Array.from(el("preconselhoRavHabilidadeTurmas").options || []).forEach((option) => {
        option.selected = false;
    });
    el("preconselhoRavHabilidadeDescricao").value = "";
    el("preconselhoRavHabilidadeOrdem").value = "0";
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
    el("preconselhoPeriodoStatusForm").value = String(periodo.status === "FECHADO" ? "ENCERRADO" : (periodo.status || "ENCERRADO"));
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

function carregarHabilidadeRavNoFormulario(habilidadeId) {
    const habilidade = obterHabilidadesRavContexto().find((item) => Number(item.id) === Number(habilidadeId));
    if (!habilidade) {
        return;
    }

    el("preconselhoRavHabilidadeEdicaoId").value = String(habilidade.id);
    el("preconselhoRavHabilidadePeriodo").value = String(habilidade.periodo_id || "");
    el("preconselhoRavHabilidadeDisciplina").value = String(habilidade.disciplina_id || "");
    el("preconselhoRavHabilidadeCodigo").value = String(habilidade.codigo || "");
    const turmaIds = new Set((Array.isArray(habilidade.turma_ids) ? habilidade.turma_ids : []).map((item) => String(item)));
    Array.from(el("preconselhoRavHabilidadeTurmas").options || []).forEach((option) => {
        option.selected = turmaIds.has(option.value);
    });
    el("preconselhoRavHabilidadeDescricao").value = String(habilidade.descricao || "");
    el("preconselhoRavHabilidadeOrdem").value = String(Number(habilidade.ordem || 0));
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
    renderizarSelectDisciplinaHabilidadeRav();
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

async function recarregarHabilidadesRav() {
    const incluirInativos = Boolean(contextoAtual?.pode_configurar);
    const sufixo = incluirInativos ? "?incluir_inativos=true" : "";
    const resposta = await fetchComAuth(`/preconselho/habilidades-rav${sufixo}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel atualizar as habilidades de RAV."));
    }

    const rav_habilidades = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        rav_habilidades
    };
    renderizarHabilidadesRavDocente();
    renderizarTabelaHabilidadesRav();
    await carregarMotivosReavaliacaoAdmin();
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
        renderizarSelectDisciplinaHabilidadeRav();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
            await carregarRav();
        }
        limparFormularioPeriodo();
        definirMensagem("msgPreconselhoPeriodo", periodoId > 0 ? "Período atualizado com sucesso." : "Período criado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoPeriodo", erro.message || "Erro ao salvar o período.", true);
    }
}

async function alternarStatusPeriodo(periodoId, statusAtual) {
    limparMensagem("msgPreconselhoPeriodo");
    const statusNormalizado = String(statusAtual || "").toUpperCase();
    const proximoStatus = statusNormalizado === "ABERTO"
        ? "EM_REAVALIACAO"
        : (statusNormalizado === "EM_REAVALIACAO" ? "ENCERRADO" : "EM_REAVALIACAO");
    try {
        const resposta = await fetchComAuth(`/preconselho/periodos/${Number(periodoId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                status: proximoStatus
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar o status do período."));
        }

        await recarregarPeriodos();
        renderizarSelectsConsolidacao();
        renderizarSelectDisciplinaHabilidadeRav();
        if (contextoAtual?.pode_consolidar) {
            await carregarConsolidacao();
        }
        if (contextoAtual?.pode_relatorio) {
            await carregarRelatorio();
            await carregarRav();
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

async function salvarHabilidadeRav(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRavHabilidade");

    const habilidadeId = Number(el("preconselhoRavHabilidadeEdicaoId").value || 0);
    const payload = {
        periodo_id: Number(el("preconselhoRavHabilidadePeriodo").value || 0),
        disciplina_id: Number(el("preconselhoRavHabilidadeDisciplina").value || 0),
        codigo: String(el("preconselhoRavHabilidadeCodigo").value || "").trim(),
        descricao: String(el("preconselhoRavHabilidadeDescricao").value || "").trim(),
        turma_ids: Array.from(el("preconselhoRavHabilidadeTurmas").selectedOptions || [])
            .map((option) => Number(option.value || 0))
            .filter((valor) => Number.isInteger(valor) && valor > 0),
        ordem: Number(el("preconselhoRavHabilidadeOrdem").value || 0)
    };

    try {
        const resposta = await fetchComAuth(
            habilidadeId > 0 ? `/preconselho/habilidades-rav/${habilidadeId}` : "/preconselho/habilidades-rav",
            {
                method: habilidadeId > 0 ? "PUT" : "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            }
        );

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel salvar a habilidade de RAV."));
        }

        await recarregarHabilidadesRav();
        limparFormularioHabilidadeRav();
        definirMensagem("msgPreconselhoRavHabilidade", habilidadeId > 0 ? "Habilidade atualizada com sucesso." : "Habilidade criada com sucesso.");
    } catch (erro) {
        definirMensagem("msgPreconselhoRavHabilidade", erro.message || "Erro ao salvar a habilidade de RAV.", true);
    }
}

async function importarHabilidadesRavJson(event) {
    event.preventDefault();
    limparMensagem("msgPreconselhoRavImport");

    let payload;
    try {
        const texto = String(el("preconselhoRavImportJson").value || "").trim();
        const dados = JSON.parse(texto);
        const periodoPadrao = Number(el("preconselhoRavImportPeriodo").value || 0);
        payload = Array.isArray(dados)
            ? { periodo_id: periodoPadrao || null, habilidades: dados }
            : {
                periodo_id: periodoPadrao || dados.periodo_id || null,
                periodo: String(dados.periodo || ""),
                habilidades: dados.habilidades || []
            };
    } catch (erro) {
        definirMensagem("msgPreconselhoRavImport", "JSON invalido. Confira a estrutura antes de importar.", true);
        return;
    }

    try {
        const resposta = await fetchComAuth("/preconselho/habilidades-rav/importar-json", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify(payload)
        });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel importar as habilidades."));
        }
        const resultado = await resposta.json();
        await recarregarHabilidadesRav();
        definirMensagem(
            "msgPreconselhoRavImport",
            `Importacao concluida: ${Number(resultado.criadas || 0)} criadas, ${Number(resultado.atualizadas || 0)} atualizadas, ${Number(resultado.ignoradas || 0)} ignoradas.`
        );
        if (Array.isArray(resultado.erros) && resultado.erros.length > 0) {
            definirMensagem("msgPreconselhoRavImport", resultado.erros.slice(0, 4).join(" | "), true);
        }
    } catch (erro) {
        definirMensagem("msgPreconselhoRavImport", erro.message || "Erro ao importar habilidades.", true);
    }
}

async function alternarStatusHabilidadeRav(habilidadeId, ativoAtual) {
    limparMensagem("msgPreconselhoRavHabilidade");
    try {
        const resposta = await fetchComAuth(`/preconselho/habilidades-rav/${Number(habilidadeId)}/status`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                ativo: Number(ativoAtual) !== 1
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel atualizar o status da habilidade."));
        }

        await recarregarHabilidadesRav();
        definirMensagem("msgPreconselhoRavHabilidade", "Status da habilidade atualizado.");
    } catch (erro) {
        definirMensagem("msgPreconselhoRavHabilidade", erro.message || "Erro ao atualizar o status da habilidade.", true);
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
    const estudanteEmRav = periodoTemRav(periodo) && Boolean(el("preconselhoEstudanteEmRav").checked);
    const ravHabilidadeIds = estudanteEmRav ? obterHabilidadesRavSelecionadasDocente() : [];
    const ravAcoes = estudanteEmRav ? String(el("preconselhoRavAcoes").value || "").trim() : "";

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
        definirEstadoSalvamentoModal(true);

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
                pos_preconselho_recuperado: null,
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: "",
                estudante_em_rav: estudanteEmRav,
                rav_habilidade_ids: ravHabilidadeIds,
                rav_acoes: ravAcoes
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
        modalDocenteAlterado = false;
        fecharModalRegistroDocente({ restaurarFoco: false, forcar: true });
    } catch (erro) {
        definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao salvar o registro.", true);
    } finally {
        definirEstadoSalvamentoModal(false);
    }
}

async function salvarReavaliacaoDocente() {
    limparMensagem("msgPreconselhoRegistro");
    const registro = registroDocenteAtual();
    const resultado = document.querySelector('[name="preconselhoResultadoReavaliacao"]:checked')?.value || "";
    const motivoIds = Array.from(document.querySelectorAll(".preconselho-review-reason:checked")).map((item) => item.value);
    if (!registro || !periodoEmReavaliacao()) {
        definirMensagem("msgPreconselhoRegistro", "Este registro não está disponível para reavaliação.", true);
        return;
    }
    if (!resultado || motivoIds.length === 0) {
        definirMensagem("msgPreconselhoRegistro", "Selecione o resultado e ao menos um motivo.", true);
        return;
    }
    try {
        definirEstadoSalvamentoModal(true);
        const resposta = await fetchComAuth(`/preconselho/registros/${Number(registro.id)}/reavaliacao`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                recuperado: resultado === "recuperado",
                motivo_ids: motivoIds,
                observacao: String(el("preconselhoObservacaoReavaliacao").value || "").trim()
            })
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar a reavaliação."));
        const registroAtualizado = await resposta.json();
        aplicarReavaliacaoNoEstado(registroAtualizado);
        definirMensagem("msgPreconselhoDocente", "Reavaliação salva com sucesso.");
        modalDocenteAlterado = false;
        fecharModalRegistroDocente({ restaurarFoco: false, forcar: true });
    } catch (erro) {
        definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao salvar a reavaliação.", true);
    } finally {
        definirEstadoSalvamentoModal(false);
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

async function copiarTexto(idCampo, idMensagem, sucesso, opcoes = {}) {
    const campo = el(idCampo);
    const texto = String(campo?.value || "").trim();
    if (!texto) {
        definirMensagem(idMensagem, "Não há texto disponível para copiar.", true);
        return;
    }

    try {
        const html = typeof opcoes.html === "function" ? String(opcoes.html(texto) || "") : "";
        if (html && navigator.clipboard?.write && window.ClipboardItem) {
            await navigator.clipboard.write([
                new ClipboardItem({
                    "text/plain": new Blob([texto], { type: "text/plain" }),
                    "text/html": new Blob([html], { type: "text/html" }),
                }),
            ]);
        } else if (navigator.clipboard?.writeText) {
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
    renderizarSelectDisciplinaHabilidadeRav();
    renderizarSelectNivelAtencao();
    renderizarSelectCategoriasMotivo();
    renderizarMotivosDocente();
    renderizarTabelaPeriodos();
    renderizarTabelaMotivos();
    renderizarTabelaHabilidadesRav();

    if (!el("preconselhoPeriodoConsolidacao").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoConsolidacao").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }
    if (!el("preconselhoPeriodoRelatorio").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoRelatorio").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }
    if (!el("preconselhoPeriodoRav").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoRav").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }

    renderizarRelatorio();
    renderizarRav();
    renderizarPainelReavaliacao();
}

async function carregarPainelInicial() {
    const tarefas = [];
    if (usuarioEhProfessor(usuarioAtual)) {
        tarefas.push(carregarPainelDocente());
    }
    if (contextoAtual?.pode_consolidar) {
        tarefas.push(carregarConsolidacao());
        tarefas.push(carregarPainelReavaliacao());
    }
    if (contextoAtual?.pode_relatorio) {
        tarefas.push(carregarRelatorio());
        tarefas.push(carregarRav());
    }
    await Promise.all(tarefas);
}

function registrarEventos() {
    window.addEventListener("beforeunload", (event) => {
        if (!modalDocenteAlterado && !modalDocenteSalvando) return;
        event.preventDefault();
        event.returnValue = "";
    });
    document.querySelectorAll("[data-preconselho-tab-trigger]").forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAba(botao.dataset.preconselhoTabTrigger || "");
        });
        botao.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            const abas = Array.from(document.querySelectorAll("[data-preconselho-tab-trigger]"))
                .filter((item) => !item.hidden);
            const indiceAtual = abas.indexOf(botao);
            if (indiceAtual < 0 || abas.length === 0) return;
            event.preventDefault();
            let proximoIndice = indiceAtual;
            if (event.key === "Home") proximoIndice = 0;
            if (event.key === "End") proximoIndice = abas.length - 1;
            if (event.key === "ArrowRight") proximoIndice = (indiceAtual + 1) % abas.length;
            if (event.key === "ArrowLeft") proximoIndice = (indiceAtual - 1 + abas.length) % abas.length;
            const proxima = abas[proximoIndice];
            ativarAba(proxima.dataset.preconselhoTabTrigger || "");
            proxima.focus();
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
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) return;
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("preconselhoPeriodoDocente").addEventListener("change", async () => {
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) {
            el("preconselhoPeriodoDocente").value = String(estadoDocente.periodoId || "");
            return;
        }
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("listaMinhasTurmasDisciplinas").addEventListener("click", async (event) => {
        const botao = event.target.closest("button[data-turma-id][data-disciplina-id]");
        if (!botao) {
            return;
        }
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) return;
        estadoDocente.turmaId = Number(botao.dataset.turmaId || 0);
        estadoDocente.disciplinaId = Number(botao.dataset.disciplinaId || 0);
        renderizarCombosDocente();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
        limparFormularioDocente();
        levarProfessorParaListaEstudantes();
    });

    el("formFiltrosEstudantesDocente").addEventListener("submit", async (event) => {
        event.preventDefault();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
    });

    el("preconselhoBuscaEstudante").addEventListener("input", () => {
        if (timerBuscaEstudante) window.clearTimeout(timerBuscaEstudante);
        timerBuscaEstudante = window.setTimeout(() => {
            void carregarEstudantesDocente();
        }, 250);
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
    el("formRegistroDocente").addEventListener("input", () => {
        if (modalRegistroDocenteAberto() && !modalDocenteSalvando) modalDocenteAlterado = true;
    });
    el("formRegistroDocente").addEventListener("change", () => {
        if (modalRegistroDocenteAberto() && !modalDocenteSalvando) modalDocenteAlterado = true;
    });
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => {
        radio.addEventListener("change", renderizarMotivosReavaliacao);
    });
    el("btnSalvarReavaliacao").addEventListener("click", salvarReavaliacaoDocente);
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
        prenderFocoNoModal(event);
        if (event.key === "Escape" && modalRegistroDocenteAberto()) {
            fecharModalRegistroDocente();
        }
    });
    document.addEventListener("click", (event) => {
        if (!event.target.closest("#preconselhoRavDetalhesField")) {
            ocultarSugestoesHabilidadesRav();
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
    el("preconselhoRavBuscaHabilidade").addEventListener("input", () => {
        renderizarSugestoesHabilidadesRav(false);
    });
    el("preconselhoRavBuscaHabilidade").addEventListener("focus", () => {
        renderizarSugestoesHabilidadesRav(true);
    });
    el("preconselhoRavBuscaHabilidade").addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        ocultarSugestoesHabilidadesRav();
    });
    el("preconselhoRavHabilidadesDocente").addEventListener("click", (event) => {
        const botao = event.target.closest("button[data-action='remover-habilidade-rav']");
        if (!botao) {
            return;
        }
        const removerId = Number(botao.dataset.habilidadeId || 0);
        const ids = obterHabilidadesRavSelecionadasDocente()
            .filter((habilidadeId) => Number(habilidadeId) !== removerId);
        aplicarSelecaoHabilidadesRavDocente(ids);
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    el("preconselhoEstudanteEmRav").addEventListener("change", () => {
        atualizarVisibilidadeRavDocente();
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    el("preconselhoRavAcoes").addEventListener("input", agendarPreviewDocente);

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
    el("preconselhoVersaoConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });

    el("preconselhoTurmaReavaliacao").addEventListener("change", async () => {
        estadoPainelReavaliacao.estudantesExpandidos.clear();
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
    });
    el("preconselhoProfessorReavaliacao").addEventListener("change", async () => {
        estadoPainelReavaliacao.estudantesExpandidos.clear();
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
    });
    el("listaPainelReavaliacao").addEventListener("click", (event) => {
        const editar = event.target.closest('button[data-action="editar-reavaliacao-gestao"]');
        if (editar) {
            event.stopPropagation();
            const registro = estadoPainelReavaliacao.registros.find((item) => Number(item.id) === Number(editar.dataset.registroId));
            if (!registro) return;
            estadoPainelReavaliacao.registroEmEdicaoId = Number(registro.id);
            estadoPainelReavaliacao.resultadoEmEdicao = resultadoRegistroReavaliacao(registro);
            renderizarPainelReavaliacao();
            el("listaPainelReavaliacao")?.querySelector(`[data-form-reavaliacao-id="${Number(registro.id)}"] input`)?.focus();
            return;
        }
        if (event.target.closest('button[data-action="cancelar-reavaliacao-gestao"]')) {
            estadoPainelReavaliacao.registroEmEdicaoId = null;
            estadoPainelReavaliacao.resultadoEmEdicao = "";
            renderizarPainelReavaliacao();
            return;
        }
        const botao = event.target.closest("button[data-estudante-reavaliacao]");
        if (!botao) return;
        const chave = String(botao.dataset.estudanteReavaliacao || "");
        if (estadoPainelReavaliacao.estudantesExpandidos.has(chave)) {
            estadoPainelReavaliacao.estudantesExpandidos.delete(chave);
        } else {
            estadoPainelReavaliacao.estudantesExpandidos.add(chave);
        }
        renderizarPainelReavaliacao();
        el("listaPainelReavaliacao")?.querySelector(`[data-estudante-reavaliacao="${CSS.escape(chave)}"]`)?.focus();
    });
    el("listaPainelReavaliacao").addEventListener("change", (event) => {
        if (event.target.name !== "resultadoGestaoReavaliacao") return;
        estadoPainelReavaliacao.resultadoEmEdicao = event.target.value;
        renderizarPainelReavaliacao();
        const registroId = Number(estadoPainelReavaliacao.registroEmEdicaoId);
        el("listaPainelReavaliacao")?.querySelector(`[data-form-reavaliacao-id="${registroId}"] [name="motivoGestaoReavaliacao"]`)?.focus();
    });
    el("listaPainelReavaliacao").addEventListener("submit", async (event) => {
        const form = event.target.closest("form[data-form-reavaliacao-id]");
        if (!form) return;
        event.preventDefault();
        await salvarReavaliacaoGestao(form);
    });

    el("btnCopiarTextoConsolidado").addEventListener("click", async () => {
        await copiarTexto(
            "preconselhoTextoConsolidado",
            "msgPreconselhoConsolidacao",
            "Texto consolidado copiado.",
            { html: () => criarHtmlTextoConsolidadoComEstudantesEmNegrito(estadoConsolidacao.dados) }
        );
    });

    el("formRelatorioPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRelatorio();
    });
    el("preconselhoPeriodoRelatorio").addEventListener("change", async () => {
        await carregarRelatorio();
    });

    el("formRavPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRav();
    });
    el("preconselhoPeriodoRav").addEventListener("change", async () => {
        await carregarRav();
    });
    el("preconselhoTurmaRav").addEventListener("change", async () => {
        await carregarRav();
    });
    el("preconselhoModoRav").addEventListener("change", () => {
        renderizarRav();
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
    el("formMotivoReavaliacao").addEventListener("submit", salvarMotivoReavaliacao);
    el("btnLimparMotivoReavaliacao").addEventListener("click", limparFormularioMotivoReavaliacao);
    el("tbodyMotivosReavaliacao").addEventListener("click", async (event) => {
        const editar = event.target.closest("button[data-action='editar-motivo-reavaliacao']");
        const status = event.target.closest("button[data-action='status-motivo-reavaliacao']");
        if (editar) {
            const item = (contextoAtual.motivos_reavaliacao_admin || []).find((motivo) => Number(motivo.id) === Number(editar.dataset.id));
            if (!item) return;
            el("preconselhoMotivoReavaliacaoId").value = String(item.id);
            el("preconselhoMotivoReavaliacaoResultado").value = item.resultado;
            el("preconselhoMotivoReavaliacaoCodigo").value = item.codigo;
            el("preconselhoMotivoReavaliacaoCodigo").disabled = true;
            el("preconselhoMotivoReavaliacaoDescricao").value = item.descricao;
            el("preconselhoMotivoReavaliacaoOrdem").value = String(item.ordem || 0);
            return;
        }
        if (status) {
            const resposta = await fetchComAuth(`/preconselho/motivos-reavaliacao/${Number(status.dataset.id)}/status`, {
                method: "PUT", headers: headersJson,
                body: JSON.stringify({ ativo: Number(status.dataset.ativo) !== 1 })
            });
            if (!resposta.ok) {
                definirMensagem("msgMotivoReavaliacao", await obterMensagemErroResposta(resposta, "Não foi possível alterar o status."), true);
                return;
            }
            await carregarMotivosReavaliacaoAdmin();
            definirMensagem("msgMotivoReavaliacao", "Status atualizado.");
        }
    });

    el("formHabilidadeRavPreconselho").addEventListener("submit", salvarHabilidadeRav);
    el("btnLimparHabilidadeRavPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoRavHabilidade");
        limparFormularioHabilidadeRav();
    });
    el("formImportarHabilidadesRavPreconselho").addEventListener("submit", importarHabilidadesRavJson);

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

    el("tbodyHabilidadesRavPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-habilidade-rav']");
        if (botaoEditar) {
            carregarHabilidadeRavNoFormulario(botaoEditar.dataset.habilidadeId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-habilidade-rav']");
        if (botaoStatus) {
            await alternarStatusHabilidadeRav(botaoStatus.dataset.habilidadeId, botaoStatus.dataset.ativo);
        }
    });
}

async function iniciarModulo() {
    registrarEventos();
    limparFormularioPeriodo();
    limparFormularioMotivo();
    limparFormularioHabilidadeRav();
    try {
        await carregarUsuario();
        await carregarContexto();
        await carregarPainelInicial();
    } catch (erro) {
        definirMensagem("msgPreconselhoDocente", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoConsolidacao", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoReavaliacao", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoRelatorio", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
    }
}

iniciarModulo();
