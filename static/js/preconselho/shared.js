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
const paginaPreconselhoAtual = document.body.dataset.preconselhoPage || "docente";

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
let abaAtiva = paginaPreconselhoAtual;
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

