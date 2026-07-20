const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    normalizarCargoUsuario,
    validarSenhaForte,
} = window.AppAuth;
const { fetchJson } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const headersJson = criarHeadersJsonAuth(token);
let opcoesProfessor = { turmas: [], disciplinas: [] };
let contextoAtribuicoesDocentes = { professores: [], turmas: [], disciplinas: [] };
let contextoTurmasDisciplinas = { professores: [], turmas: [], disciplinas: [] };
let professorEmEdicaoId = null;
const turmasDisciplinasExpandidas = new Set();
const TURNO_LABEL = {
    INTEGRAL: "Período integral",
    MATUTINO: "Matutino",
    VESPERTINO: "Vespertino",
    VESPERTINO_EM: "Vespertino E.M."
};
const CARGO_ADMIN = "ADMIN";
const CARGO_PROFESSOR = "PROFESSOR";
const CARGO_COORDENADOR = "COORDENADOR";
const MODELO_JSON_ATRIBUICOES_DOCENTES = JSON.stringify(
    {
        atribuicoes: [
            {
                professor_nome: "Professor Alex",
                disciplina: "Geometria",
                turmas: ["1 EM A", "1 EM B"]
            },
            {
                professor_nome: "Professor Alex",
                disciplina: "Letramento e Raciocinio Matematico",
                turmas: ["6 ano A"]
            }
        ]
    },
    null,
    2
);
let usuarioAtual = null;
let usuarioEhAdmin = false;
let usuarioEhGestor = false;
let abaAdminAtiva = "professores";

function mesAtualIso() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function setMensagem(id, texto, erro = false) {
    const target = el(id);
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function houveFalhaImportacao(resultado) {
    return Number(resultado?.importados || 0) <= 0 && Number(resultado?.erros || 0) > 0;
}

function comporMensagemImportacao(resultado) {
    const mensagemBase = String(resultado?.mensagem || "Importacao concluida.").trim();
    const detalhes = Array.isArray(resultado?.detalhes_erros) ? resultado.detalhes_erros : [];
    if (detalhes.length === 0) return mensagemBase;

    const amostra = detalhes.slice(0, 3);
    const restante = detalhes.length - amostra.length;
    let mensagem = `${mensagemBase} ${amostra.join(" | ")}`;
    if (restante > 0) {
        mensagem += ` | +${restante} erro(s) adicional(is).`;
    }
    return mensagem;
}

function baixarArquivoTexto(nomeArquivo, conteudo, tipo = "application/json;charset=utf-8") {
    window.AppApi.baixarArquivoTexto(nomeArquivo, conteudo, tipo);
}

function listarBotoesAbasAdmin() {
    return Array.from(document.querySelectorAll("[data-admin-tab-trigger]"));
}

function listarPaineisAbasAdmin() {
    return Array.from(document.querySelectorAll("[data-admin-tab-panel]"));
}

function botaoAbaDisponivel(botao) {
    return Boolean(botao) && botao.style.display !== "none";
}

function primeiraAbaDisponivel() {
    return listarBotoesAbasAdmin().find((botao) => botaoAbaDisponivel(botao)) || null;
}

function ativarAbaAdmin(abaId) {
    const botoes = listarBotoesAbasAdmin();
    const paineis = listarPaineisAbasAdmin();
    if (botoes.length === 0 || paineis.length === 0) {
        return;
    }

    let abaAlvo = abaId;
    const botaoAlvo = botoes.find((botao) => (
        botao.dataset.adminTabTrigger === abaAlvo && botaoAbaDisponivel(botao)
    ));
    if (!botaoAlvo) {
        const fallback = primeiraAbaDisponivel();
        if (!fallback) {
            return;
        }
        abaAlvo = fallback.dataset.adminTabTrigger;
    }

    abaAdminAtiva = abaAlvo;
    botoes.forEach((botao) => {
        const ativa = botao.dataset.adminTabTrigger === abaAlvo && botaoAbaDisponivel(botao);
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
    });
    paineis.forEach((painel) => {
        const ativo = painel.dataset.adminTabPanel === abaAlvo;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

function ajustarAbasAdminPorPermissao() {
    const ativaDisponivel = listarBotoesAbasAdmin().some((botao) => (
        botao.dataset.adminTabTrigger === abaAdminAtiva && botaoAbaDisponivel(botao)
    ));
    if (ativaDisponivel) {
        ativarAbaAdmin(abaAdminAtiva);
        return;
    }

    const fallback = primeiraAbaDisponivel();
    if (fallback) {
        ativarAbaAdmin(fallback.dataset.adminTabTrigger);
    }
}

function registrarEventosAbasAdmin() {
    listarBotoesAbasAdmin().forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAbaAdmin(botao.dataset.adminTabTrigger);
        });
    });
}

function aplicarPermissoesTela() {
    document.querySelectorAll("[data-admin-only='true']").forEach((secao) => {
        secao.style.display = usuarioEhAdmin ? "" : "none";
    });
    ajustarAbasAdminPorPermissao();
}

async function carregarUsuarioAtual() {
    usuarioAtual = await fetchJson("/me", { headers });
    const cargo = normalizarCargoUsuario(usuarioAtual);
    usuarioEhAdmin = cargo === CARGO_ADMIN;
    usuarioEhGestor = usuarioEhAdmin || cargo === CARGO_COORDENADOR;

    if (!usuarioEhGestor) {
        window.location.href = "/servicos";
    }
}

async function atualizarOpcoesProfessorSePermitido() {
    if (!usuarioEhAdmin || typeof carregarOpcoesProfessor !== "function") {
        return;
    }
    await carregarOpcoesProfessor();
}

async function atualizarAtribuicoesDocentesSePermitido() {
    if (!usuarioEhAdmin || typeof carregarContextoAtribuicoesDocentes !== "function") {
        return;
    }
    await carregarContextoAtribuicoesDocentes();
    await carregarAtribuicoesDocentes();
    await atualizarEstruturaEscolarSePermitido();
}

async function atualizarEstruturaEscolarSePermitido() {
    if (!usuarioEhAdmin || typeof carregarContextoTurmasDisciplinas !== "function") {
        return;
    }
    await carregarContextoTurmasDisciplinas();
    await carregarTurmasDisciplinasAdmin();
}

function formatarDataHora(dataHoraSql) {
    if (!dataHoraSql) return "NÃ£o informado";
    const texto = String(dataHoraSql).trim();
    const data = new Date(texto.replace(" ", "T") + "Z");
    if (Number.isNaN(data.getTime())) return texto;
    return data.toLocaleString("pt-BR");
}

function nomeTurno(turno) {
    return TURNO_LABEL[turno] || turno || "Não informado";
}

function preencherSelectComItens(
    selectId,
    itens,
    placeholder,
    {
        permitirVazio = false,
        labelFn = (item) => item.nome || "",
        valueFn = (item) => item.id
    } = {}
) {
    const select = el(selectId);
    if (!select) {
        return;
    }

    const valorAtual = select.value;
    select.innerHTML = "";

    const optionPlaceholder = document.createElement("option");
    optionPlaceholder.value = "";
    optionPlaceholder.innerText = placeholder;
    optionPlaceholder.disabled = !permitirVazio;
    optionPlaceholder.selected = true;
    select.appendChild(optionPlaceholder);

    (Array.isArray(itens) ? itens : []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(valueFn(item));
        option.innerText = labelFn(item);
        select.appendChild(option);
    });

    if (valorAtual && Array.from(select.options).some((option) => option.value === valorAtual)) {
        select.value = valorAtual;
    } else if (permitirVazio) {
        select.value = "";
    } else if (select.options.length > 1) {
        select.selectedIndex = 1;
    } else {
        select.selectedIndex = 0;
    }
}
