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
let recursoEmEdicaoId = null;
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

function atualizarVisibilidadeCamposCargo() {
    const cargo = String(el("profCargo")?.value || CARGO_PROFESSOR).toUpperCase();
    const hint = el("profCargoHint");
    if (!hint) {
        return;
    }
    hint.style.display = cargo === CARGO_COORDENADOR ? "block" : "none";
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
    if (!usuarioEhAdmin) {
        return;
    }
    await carregarOpcoesProfessor();
}

async function atualizarAtribuicoesDocentesSePermitido() {
    if (!usuarioEhAdmin) {
        return;
    }
    await carregarContextoAtribuicoesDocentes();
    await carregarAtribuicoesDocentes();
    await atualizarEstruturaEscolarSePermitido();
}

async function atualizarEstruturaEscolarSePermitido() {
    if (!usuarioEhAdmin) {
        return;
    }
    await carregarContextoTurmasDisciplinas();
    await carregarTurmasDisciplinasAdmin();
}

function atualizarHintSenha() {
    const senha = el("profSenha").value.trim();
    const hint = el("profSenhaHint");
    if (!senha) {
        hint.style.color = "#4b5563";
        return;
    }
    hint.style.color = validarSenhaForte(senha) ? "#0f766e" : "#b42318";
}

function renderCheckboxes(containerId, opcoes, prefixo) {
    const container = el(containerId);
    container.innerHTML = "";

    if (!Array.isArray(opcoes) || opcoes.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma opção ativa cadastrada.";
        container.appendChild(vazio);
        return;
    }

    opcoes.forEach((item, index) => {
        const id = `${prefixo}_${index}`;
        const label = document.createElement("label");
        label.className = "admin-checkbox-item";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = id;
        input.value = item;

        const texto = document.createElement("span");
        texto.innerText = item;

        label.appendChild(input);
        label.appendChild(texto);
        container.appendChild(label);
    });
}

function listarSelecionados(containerId) {
    return Array.from(el(containerId).querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => input.value);
}

function definirSelecionados(containerId, valores = []) {
    const selecionados = new Set((valores || []).map((item) => String(item)));
    Array.from(el(containerId).querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = selecionados.has(String(input.value));
    });
}

function resumoLista(lista, limite = 3) {
    if (!Array.isArray(lista) || lista.length === 0) return "Não informado";
    if (lista.length <= limite) return lista.join(", ");
    return `${lista.slice(0, limite).join(", ")} +${lista.length - limite}`;
}

function formatarDataBr(dataIso) {
    if (!dataIso) return "Não informada";
    const data = new Date(`${dataIso}T00:00:00`);
    if (Number.isNaN(data.getTime())) return dataIso;
    return data.toLocaleDateString("pt-BR");
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

function aplicarModoFormularioProfessor(edicao = false) {
    const titulo = el("tituloFormProfessor");
    const btnSalvar = el("btnSalvarProfessor");
    const btnCancelar = el("btnCancelarEdicaoProfessor");
    const inputSenha = el("profSenha");
    const hintSenha = el("profSenhaHint");
    const selectCargo = el("profCargo");

    if (edicao) {
        titulo.innerText = "Editar professor";
        btnSalvar.innerText = "Salvar alterações";
        btnCancelar.style.display = "inline-block";
        if (selectCargo) {
            selectCargo.value = CARGO_PROFESSOR;
            selectCargo.disabled = true;
        }
        inputSenha.value = "";
        inputSenha.required = false;
        inputSenha.disabled = true;
        inputSenha.placeholder = "Senha não alterada nesta edição";
        hintSenha.innerText = "Edição de cadastro: a senha não é alterada por este formulário.";
        hintSenha.style.color = "#4b5563";
        atualizarVisibilidadeCamposCargo();
        return;
    }

    const cargoSelecionado = String(selectCargo?.value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    titulo.innerText = ehCoordenador ? "Cadastrar coordenador" : "Cadastrar professor";
    btnSalvar.innerText = "Cadastrar";
    btnCancelar.style.display = "none";
    if (selectCargo) {
        selectCargo.disabled = false;
    }
    inputSenha.required = true;
    inputSenha.disabled = false;
    inputSenha.placeholder = "Senha inicial";
    hintSenha.innerText = ehCoordenador
        ? "Senha inicial do coordenador."
        : "Mínimo 8 caracteres com maiúscula, minúscula, número e caractere especial.";
    atualizarHintSenha();
    atualizarVisibilidadeCamposCargo();
}

function limparFormularioProfessor() {
    el("formProfessor").reset();
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = "0";
    definirSelecionados("profTurmasLista", []);
    definirSelecionados("profDisciplinasLista", []);
    professorEmEdicaoId = null;
    aplicarModoFormularioProfessor(false);
}

function iniciarEdicaoProfessor(professor) {
    professorEmEdicaoId = Number(professor.id);
    el("profNome").value = professor.nome || "";
    el("profEmail").value = professor.email || "";
    el("profDataNascimento").value = professor.data_nascimento || "";
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = String(professor.aulas_semanais ?? 0);
    definirSelecionados("profTurmasLista", professor.turmas || []);
    definirSelecionados("profDisciplinasLista", professor.disciplinas || []);
    aplicarModoFormularioProfessor(true);
    ativarAbaAdmin("professores");
    el("formProfessor").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function excluirProfessor(professor) {
    const professorId = Number(professor?.id || 0);
    if (professorId <= 0) {
        setMensagem("msgProfessor", "Professor invalido para exclusao.", true);
        return;
    }

    const nomeProfessor = String(professor?.nome || "este professor").trim() || "este professor";
    const confirmado = window.confirm(
        `Excluir ${nomeProfessor}? O acesso sera bloqueado e o professor saira das listas operacionais.`
    );
    if (!confirmado) {
        return;
    }

    try {
        await fetchJson(`/admin/professores/${professorId}`, {
            method: "DELETE",
            headers
        });
        if (professorEmEdicaoId === professorId) {
            limparFormularioProfessor();
        }
        setMensagem("msgProfessor", `${nomeProfessor} excluido com sucesso.`);
        await Promise.all([carregarProfessores(), atualizarAtribuicoesDocentesSePermitido()]);
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

function aplicarModoFormularioRecurso(edicao = false) {
    const titulo = el("tituloFormRecurso");
    const btnSalvar = el("btnSalvarRecurso");
    const btnCancelar = el("btnCancelarEdicaoRecurso");

    if (edicao) {
        titulo.innerText = "Editar recurso";
        btnSalvar.innerText = "Salvar alterações";
        btnCancelar.style.display = "inline-block";
        return;
    }

    titulo.innerText = "Cadastrar recurso";
    btnSalvar.innerText = "Cadastrar recurso";
    btnCancelar.style.display = "none";
}

function limparFormularioRecurso() {
    el("formRecurso").reset();
    el("recursoQuantidadeItens").value = "1";
    recursoEmEdicaoId = null;
    aplicarModoFormularioRecurso(false);
}

function iniciarEdicaoRecurso(recurso) {
    recursoEmEdicaoId = Number(recurso.id);
    el("recursoNome").value = recurso.nome || "";
    el("recursoTipo").value = recurso.tipo || "";
    el("recursoDescricao").value = recurso.descricao || "";
    el("recursoQuantidadeItens").value = String(recurso.quantidade_itens ?? 1);
    aplicarModoFormularioRecurso(true);
    ativarAbaAdmin("recursos");
    el("formRecurso").scrollIntoView({ behavior: "smooth", block: "center" });
}

