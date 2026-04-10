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

const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
let opcoesProfessor = { turmas: [], disciplinas: [] };
let contextoAtribuicoesDocentes = { professores: [], turmas: [], disciplinas: [] };
let professorEmEdicaoId = null;
let recursoEmEdicaoId = null;
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
                professor_email: "alex@escola.local",
                disciplina: "Geometria",
                turmas: ["1 EM A", "1 EM B"]
            },
            {
                professor_email: "alex@escola.local",
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

function el(id) {
    return document.getElementById(id);
}

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

function normalizarErro(res, body) {
    if (body && body.detail) return body.detail;
    return `Erro ${res.status}`;
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
    const blob = new Blob(["\uFEFF", conteudo], { type: tipo });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let body = null;
    try {
        body = await res.json();
    } catch (err) {
        body = null;
    }

    if (res.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
        throw new Error("Sessão expirada.");
    }

    if (!res.ok) {
        throw new Error(normalizarErro(res, body));
    }
    return body;
}

function normalizarCargoUsuario(usuario = {}) {
    const cargo = String(usuario.cargo || "").trim().toUpperCase();
    if (cargo) {
        return cargo;
    }

    const perfil = String(usuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return CARGO_ADMIN;
    if (perfil === "coordenador") return CARGO_COORDENADOR;
    return CARGO_PROFESSOR;
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
}

function validarSenhaForte(senha) {
    return SENHA_FORTE_REGEX.test(senha || "");
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

async function carregarOpcoesProfessor() {
    const dados = await fetchJson("/admin/professores/opcoes", { headers });
    opcoesProfessor = {
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    renderCheckboxes("profTurmasLista", opcoesProfessor.turmas, "turma");
    renderCheckboxes("profDisciplinasLista", opcoesProfessor.disciplinas, "disciplina");
}

async function carregarContextoAtribuicoesDocentes() {
    const dados = await fetchJson("/admin/atribuicoes-docentes/contexto", { headers });
    contextoAtribuicoesDocentes = {
        professores: Array.isArray(dados.professores) ? dados.professores : [],
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    preencherSelectComItens(
        "atribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Selecione o professor",
        { labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "atribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Selecione a disciplina"
    );

    preencherSelectComItens(
        "filtroAtribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Todos os professores",
        { permitirVazio: true, labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "filtroAtribuicaoTurma",
        contextoAtribuicoesDocentes.turmas,
        "Todas as turmas",
        { permitirVazio: true }
    );
    preencherSelectComItens(
        "filtroAtribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Todas as disciplinas",
        { permitirVazio: true }
    );

    await carregarTurmasAtribuidasProfessorDisciplina();
}

function obterProfessorIdAtribuicaoFormulario() {
    return Number(el("atribuicaoProfessor")?.value || 0);
}

function obterDisciplinaIdAtribuicaoFormulario() {
    return Number(el("atribuicaoDisciplina")?.value || 0);
}

function obterTurmaIdsSelecionadasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return [];
    }
    return Array.from(container.querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => Number(input.value))
        .filter((valor) => Number.isFinite(valor) && valor > 0);
}

function atualizarResumoTurmasAtribuicao() {
    const resumo = el("atribuicaoTurmasResumo");
    if (!resumo) {
        return;
    }

    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    if (professorId <= 0 || disciplinaId <= 0) {
        resumo.innerText = "Selecione professor e disciplina para carregar as turmas.";
        return;
    }

    const selecionadas = obterTurmaIdsSelecionadasAtribuicao();
    if (selecionadas.length === 0) {
        resumo.innerText = "Nenhuma turma marcada. Salvar agora remove as atribuicoes desta disciplina para o professor.";
        return;
    }

    resumo.innerText = `${selecionadas.length} turma(s) marcada(s) para esta disciplina.`;
}

function renderTurmasAtribuicaoCheckboxes(turmaIdsSelecionadas = []) {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!Array.isArray(contextoAtribuicoesDocentes.turmas) || contextoAtribuicoesDocentes.turmas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma ativa cadastrada.";
        container.appendChild(vazio);
        atualizarResumoTurmasAtribuicao();
        return;
    }

    const selecionadas = new Set((turmaIdsSelecionadas || []).map((item) => String(item)));
    contextoAtribuicoesDocentes.turmas.forEach((turma, index) => {
        const label = document.createElement("label");
        label.className = "admin-checkbox-item admin-checkbox-item-stack";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = `atribuicao_turma_${index}_${turma.id}`;
        input.value = String(turma.id);
        input.checked = selecionadas.has(String(turma.id));
        input.addEventListener("change", atualizarResumoTurmasAtribuicao);

        const texto = document.createElement("span");
        texto.innerText = turma.nome;

        const detalhe = document.createElement("small");
        detalhe.className = "admin-checkbox-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)}`;

        const conteudo = document.createElement("div");
        conteudo.className = "admin-checkbox-content";
        conteudo.appendChild(texto);
        conteudo.appendChild(detalhe);

        label.appendChild(input);
        label.appendChild(conteudo);
        container.appendChild(label);
    });

    atualizarResumoTurmasAtribuicao();
}

async function carregarTurmasAtribuidasProfessorDisciplina() {
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();

    if (professorId <= 0 || disciplinaId <= 0) {
        renderTurmasAtribuicaoCheckboxes([]);
        return;
    }

    const lista = await fetchJson(
        `/admin/atribuicoes-docentes?professor_id=${professorId}&disciplina_id=${disciplinaId}`,
        { headers }
    );
    renderTurmasAtribuicaoCheckboxes(
        (Array.isArray(lista) ? lista : []).map((item) => Number(item.turma_id))
    );
}

function selecionarTodasTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = true;
    });
    atualizarResumoTurmasAtribuicao();
}

function limparSelecaoTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = false;
    });
    atualizarResumoTurmasAtribuicao();
}

function queryAtribuicoesDocentes() {
    const params = new URLSearchParams();
    const professorId = el("filtroAtribuicaoProfessor")?.value || "";
    const turmaId = el("filtroAtribuicaoTurma")?.value || "";
    const disciplinaId = el("filtroAtribuicaoDisciplina")?.value || "";
    if (professorId) params.set("professor_id", professorId);
    if (turmaId) params.set("turma_id", turmaId);
    if (disciplinaId) params.set("disciplina_id", disciplinaId);
    return params.toString() ? `?${params.toString()}` : "";
}

async function carregarAtribuicoesDocentes() {
    const lista = await fetchJson(`/admin/atribuicoes-docentes${queryAtribuicoesDocentes()}`, { headers });
    const ul = el("listaAtribuicoesDocentesAdmin");
    if (!ul) {
        return;
    }
    ul.innerHTML = "";

    if (!Array.isArray(lista) || lista.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma atribuição docente encontrada para os filtros selecionados.";
        ul.appendChild(vazio);
        return;
    }

    lista.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${item.professor_nome} | ${item.turma_nome} | ${item.disciplina_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turno: ${nomeTurno(item.turno)} | Status: ${
            item.professor_ativo && item.turma_ativa && item.disciplina_ativa ? "Ativo" : "Vínculo com item inativo"
        }`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.innerText = "Remover atribuição";
        btnExcluir.addEventListener("click", async () => {
            const confirmado = window.confirm(
                `Remover a atribuição de ${item.professor_nome} em ${item.disciplina_nome} para ${item.turma_nome}?`
            );
            if (!confirmado) {
                return;
            }
            try {
                await fetchJson(`/admin/atribuicoes-docentes/${item.id}`, {
                    method: "DELETE",
                    headers
                });
                setMensagem("msgAtribuicoesDocentes", "Atribuição docente removida com sucesso.");
                await Promise.all([carregarProfessores(), carregarContextoAtribuicoesDocentes(), carregarAtribuicoesDocentes()]);
            } catch (err) {
                setMensagem("msgAtribuicoesDocentes", err.message, true);
            }
        });

        linha.appendChild(btnExcluir);
        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function cadastrarAtribuicaoDocente(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/atribuicoes-docentes", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                professor_id: Number(el("atribuicaoProfessor").value),
                turma_id: Number(el("atribuicaoTurma").value),
                disciplina_id: Number(el("atribuicaoDisciplina").value)
            })
        });
        setMensagem("msgAtribuicoesDocentes", "Atribuição docente cadastrada com sucesso.");
        el("formAtribuicaoDocente").reset();
        await Promise.all([carregarProfessores(), carregarContextoAtribuicoesDocentes(), carregarAtribuicoesDocentes()]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

function limparFiltrosAtribuicoesDocentes() {
    if (el("filtroAtribuicaoProfessor")) el("filtroAtribuicaoProfessor").value = "";
    if (el("filtroAtribuicaoTurma")) el("filtroAtribuicaoTurma").value = "";
    if (el("filtroAtribuicaoDisciplina")) el("filtroAtribuicaoDisciplina").value = "";
    carregarAtribuicoesDocentes().catch((err) => {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    });
}

async function carregarAtribuicoesDocentes() {
    const lista = await fetchJson(`/admin/atribuicoes-docentes${queryAtribuicoesDocentes()}`, { headers });
    const ul = el("listaAtribuicoesDocentesAdmin");
    if (!ul) {
        return;
    }
    ul.innerHTML = "";

    if (!Array.isArray(lista) || lista.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma atribuicao docente encontrada para os filtros selecionados.";
        ul.appendChild(vazio);
        return;
    }

    const grupos = new Map();
    lista.forEach((item) => {
        const chave = `${item.professor_id}::${item.disciplina_id}`;
        if (!grupos.has(chave)) {
            grupos.set(chave, {
                professor_id: Number(item.professor_id),
                professor_nome: item.professor_nome,
                disciplina_id: Number(item.disciplina_id),
                disciplina_nome: item.disciplina_nome,
                professor_ativo: Boolean(item.professor_ativo),
                disciplina_ativa: Boolean(item.disciplina_ativa),
                turmas: []
            });
        }
        grupos.get(chave).turmas.push({
            id: Number(item.turma_id),
            nome: item.turma_nome,
            turno: item.turno,
            ativa: Boolean(item.turma_ativa)
        });
    });

    Array.from(grupos.values()).forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${item.professor_nome} | ${item.disciplina_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turmas: ${item.turmas.map((turma) => `${turma.nome} (${nomeTurno(turma.turno)})`).join(", ")}`;

        const status = document.createElement("p");
        status.className = "booking-detail";
        status.innerText = `Status: ${
            item.professor_ativo && item.disciplina_ativa && item.turmas.every((turma) => turma.ativa)
                ? "Ativo"
                : "Vinculo com item inativo"
        }`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar turmas";
        btnEditar.addEventListener("click", async () => {
            el("atribuicaoProfessor").value = String(item.professor_id);
            el("atribuicaoDisciplina").value = String(item.disciplina_id);
            await carregarTurmasAtribuidasProfessorDisciplina();
            ativarAbaAdmin("atribuicoes");
            el("formAtribuicaoDocente").scrollIntoView({ behavior: "smooth", block: "start" });
        });

        const btnLimpar = document.createElement("button");
        btnLimpar.type = "button";
        btnLimpar.innerText = "Limpar turmas";
        btnLimpar.addEventListener("click", async () => {
            const confirmado = window.confirm(
                `Remover todas as turmas de ${item.professor_nome} em ${item.disciplina_nome}?`
            );
            if (!confirmado) {
                return;
            }
            try {
                await fetchJson("/admin/atribuicoes-docentes/lote", {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        professor_id: item.professor_id,
                        disciplina_id: item.disciplina_id,
                        turma_ids: []
                    })
                });
                setMensagem("msgAtribuicoesDocentes", "Atribuicoes removidas com sucesso.");
                await Promise.all([carregarProfessores(), carregarContextoAtribuicoesDocentes(), carregarAtribuicoesDocentes()]);
            } catch (err) {
                setMensagem("msgAtribuicoesDocentes", err.message, true);
            }
        });

        linha.appendChild(btnEditar);
        linha.appendChild(btnLimpar);
        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(status);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function cadastrarAtribuicaoDocente(event) {
    event.preventDefault();
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    const turmaIds = obterTurmaIdsSelecionadasAtribuicao();

    if (professorId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione o professor.", true);
        return;
    }
    if (disciplinaId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione a disciplina.", true);
        return;
    }
    if (turmaIds.length === 0) {
        const confirmado = window.confirm(
            "Nenhuma turma foi marcada. Deseja remover todas as atribuicoes desta disciplina para o professor?"
        );
        if (!confirmado) {
            return;
        }
    }

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/lote", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                professor_id: professorId,
                disciplina_id: disciplinaId,
                turma_ids: turmaIds
            })
        });
        setMensagem("msgAtribuicoesDocentes", resposta.mensagem || "Atribuicoes atualizadas com sucesso.");
        await Promise.all([carregarProfessores(), carregarAtribuicoesDocentes(), carregarTurmasAtribuidasProfessorDisciplina()]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

async function importarAtribuicoesDocentesArquivo(event) {
    event.preventDefault();
    const arquivo = el("arquivoJsonAtribuicoesDocentes")?.files?.[0];
    if (!arquivo) {
        setMensagem("msgAtribuicoesDocentes", "Selecione um arquivo JSON para importar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/importar", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagem("msgAtribuicoesDocentes", comporMensagemImportacao(resposta), houveFalhaImportacao(resposta));
        el("formImportarAtribuicoesDocentes").reset();
        await Promise.all([carregarProfessores(), carregarContextoAtribuicoesDocentes(), carregarAtribuicoesDocentes()]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

function baixarModeloAtribuicoesJson() {
    baixarArquivoTexto("modelo_atribuicoes_docentes.json", MODELO_JSON_ATRIBUICOES_DOCENTES);
}

async function carregarTurmasAdmin() {
    const turmas = await fetchJson("/admin/turmas?incluir_inativas=true", { headers });
    const ul = el("listaTurmasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(turmas) || turmas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    turmas.forEach((turma) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = turma.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)} | Estudantes: ${turma.quantidade_estudantes ?? 0} | Status: ${turma.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputTurno = document.createElement("select");
        ["MATUTINO", "VESPERTINO", "VESPERTINO_EM", "INTEGRAL"].forEach((turno) => {
            const option = document.createElement("option");
            option.value = turno;
            option.innerText = nomeTurno(turno);
            inputTurno.appendChild(option);
        });
        inputTurno.value = turma.turno && TURNO_LABEL[turma.turno] ? turma.turno : "MATUTINO";

        const inputQuantidade = document.createElement("input");
        inputQuantidade.type = "number";
        inputQuantidade.min = "0";
        inputQuantidade.value = String(turma.quantidade_estudantes ?? 0);
        inputQuantidade.title = "Quantidade de estudantes";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar dados";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        turno: inputTurno.value,
                        quantidade_estudantes: Number(inputQuantidade.value)
                    })
                });
                setMensagem("msgTurma", `Dados da turma ${turma.nome} atualizados.`);
                await Promise.all([carregarTurmasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = turma.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(turma.ativo) })
                });
                await Promise.all([
                    carregarTurmasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        linha.appendChild(inputTurno);
        linha.appendChild(inputQuantidade);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarTurma(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/turmas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("turmaNome").value.trim(),
                turno: el("turmaTurno").value,
                quantidade_estudantes: Number(el("turmaQuantidadeEstudantes").value)
            })
        });

        setMensagem("msgTurma", "Turma cadastrada com sucesso.");
        el("formTurma").reset();
        el("turmaTurno").value = "MATUTINO";
        el("turmaQuantidadeEstudantes").value = "0";
        await Promise.all([
            carregarTurmasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgTurma", err.message, true);
    }
}

async function carregarDisciplinasAdmin() {
    const disciplinas = await fetchJson("/admin/disciplinas?incluir_inativas=true", { headers });
    const ul = el("listaDisciplinasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(disciplinas) || disciplinas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    disciplinas.forEach((disciplina) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = disciplina.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Aulas semanais: ${disciplina.aulas_semanais ?? 0} | Status: ${disciplina.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(disciplina.aulas_semanais ?? 0);
        inputAulas.title = "Aulas semanais";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar aulas";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value)
                    })
                });
                setMensagem("msgDisciplina", `Aulas da disciplina ${disciplina.nome} atualizadas.`);
                await Promise.all([carregarDisciplinasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = disciplina.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(disciplina.ativo) })
                });
                await Promise.all([
                    carregarDisciplinasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarDisciplina(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/disciplinas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("disciplinaNome").value.trim(),
                aulas_semanais: Number(el("disciplinaAulasSemanais").value)
            })
        });

        setMensagem("msgDisciplina", "Disciplina cadastrada com sucesso.");
        el("formDisciplina").reset();
        el("disciplinaAulasSemanais").value = "0";
        await Promise.all([
            carregarDisciplinasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgDisciplina", err.message, true);
    }
}

function queryPeriodo(prefix = "") {
    const inicio = el(`${prefix}relDataInicio`) ? el(`${prefix}relDataInicio`).value : el("relDataInicio").value;
    const fim = el(`${prefix}relDataFim`) ? el(`${prefix}relDataFim`).value : el("relDataFim").value;

    const params = new URLSearchParams();
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function queryHistorico() {
    const params = new URLSearchParams();
    const inicio = el("inicio").value;
    const fim = el("fim").value;
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

async function carregarFilaAdmin() {
    const jobs = await fetchJson("/admin/fila", { headers });
    const ul = el("fila-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const descricao = document.createElement("p");
        descricao.innerText = `${job.arquivo} | ${job.status} | ${job.paginas_totais ?? 0} páginas`;

        const actions = document.createElement("div");
        actions.className = "admin-inline";

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarJob(job.id));

        const btnUrgente = document.createElement("button");
        btnUrgente.type = "button";
        btnUrgente.innerText = "Urgente";
        btnUrgente.addEventListener("click", () => prioridadeJob(job.id));

        actions.appendChild(btnCancelar);
        actions.appendChild(btnUrgente);
        li.appendChild(descricao);
        li.appendChild(actions);
        ul.appendChild(li);
    });
}

async function cancelarJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/cancelar`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function prioridadeJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/prioridade`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function buscarHistorico() {
    const jobs = await fetchJson(`/admin/historico${queryHistorico()}`, { headers });
    const ul = el("historico-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${job.criado_em} | ${job.arquivo} | ${job.paginas_totais ?? 0} páginas | ${job.status}`;
        ul.appendChild(li);
    });
}

async function carregarProfessores() {
    const mes = el("mesReferenciaCota").value || mesAtualIso();
    const dados = await fetchJson(`/admin/professores?mes=${mes}`, { headers });

    if (dados.regras_cota) {
        el("cotaMensalEscola").value = dados.regras_cota.cota_mensal_escola ?? 0;
        el("cotaBase").value = dados.regras_cota.base_paginas ?? 0;
        el("cotaPorAula").value = dados.regras_cota.paginas_por_aula ?? 0;
        el("cotaPorTurma").value = dados.regras_cota.paginas_por_turma ?? 0;
    }

    const ul = el("listaProfessoresAdmin");
    ul.innerHTML = "";

    dados.professores.forEach((prof) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${prof.nome} (${prof.email})`;

        const cadastro = document.createElement("p");
        cadastro.className = "booking-detail";
        cadastro.innerText = `Nascimento: ${formatarDataBr(prof.data_nascimento)} | Turmas operacionais: ${resumoLista(prof.turmas_operacionais || prof.turmas)} | Disciplinas operacionais: ${resumoLista(prof.disciplinas_operacionais || prof.disciplinas)}`;

        const meta = document.createElement("p");
        const limiteMes = prof.cota_mes ? prof.cota_mes.limite_paginas : "-";
        const usadasMes = prof.cota_mes ? prof.cota_mes.usadas_paginas : "-";
        meta.className = "booking-detail";
        meta.innerText = `Projetada: ${prof.cota_projetada} | Mês: ${usadasMes}/${limiteMes}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(prof.aulas_semanais ?? "");
        inputAulas.title = "Aulas semanais";
        inputAulas.placeholder = "Quantidade de aulas semanais";

        const inputTurmas = document.createElement("input");
        inputTurmas.type = "number";
        inputTurmas.min = "0";
        inputTurmas.placeholder = "Quantidade de turmas";
        inputTurmas.value = String(prof.turmas_quantidade ?? "");
        inputTurmas.title = "Quantidade de turmas";

        const btnSalvar = document.createElement("button");
        btnSalvar.type = "button";
        btnSalvar.innerText = "Salvar carga";
        btnSalvar.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/professores/${prof.id}/carga`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value),
                        turmas_quantidade: Number(inputTurmas.value)
                    })
                });
                setMensagem("msgProfessor", `Carga atualizada para ${prof.nome}.`);
                await carregarProfessores();
            } catch (err) {
                setMensagem("msgProfessor", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoProfessor(prof);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.innerText = "Excluir professor";
        btnExcluir.addEventListener("click", async () => {
            await excluirProfessor(prof);
        });

        const linhaSenha = document.createElement("div");
        linhaSenha.className = "admin-inline";

        const inputNovaSenha = document.createElement("input");
        inputNovaSenha.type = "password";
        inputNovaSenha.placeholder = "Nova senha";
        inputNovaSenha.autocomplete = "new-password";

        const inputConfirmacaoSenha = document.createElement("input");
        inputConfirmacaoSenha.type = "password";
        inputConfirmacaoSenha.placeholder = "Confirmar nova senha";
        inputConfirmacaoSenha.autocomplete = "new-password";

        const btnRedefinirSenha = document.createElement("button");
        btnRedefinirSenha.type = "button";
        btnRedefinirSenha.innerText = "Redefinir senha";
        btnRedefinirSenha.addEventListener("click", async () => {
            const novaSenha = inputNovaSenha.value.trim();
            const confirmacao = inputConfirmacaoSenha.value.trim();

            if (!novaSenha) {
                setMensagem("msgProfessor", "Informe a nova senha para redefinir.", true);
                return;
            }
            if (!validarSenhaForte(novaSenha)) {
                setMensagem("msgProfessor", "Nova senha fora do padrao de seguranca.", true);
                return;
            }
            if (novaSenha !== confirmacao) {
                setMensagem("msgProfessor", "A confirmacao da nova senha nao confere.", true);
                return;
            }

            try {
                await fetchJson(`/admin/professores/${prof.id}/senha`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ nova_senha: novaSenha })
                });
                inputNovaSenha.value = "";
                inputConfirmacaoSenha.value = "";
                setMensagem("msgProfessor", `Senha redefinida para ${prof.nome}.`);
            } catch (err) {
                setMensagem("msgProfessor", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(inputTurmas);
        linha.appendChild(btnSalvar);
        linha.appendChild(btnEditar);
        linha.appendChild(btnExcluir);

        linhaSenha.appendChild(inputNovaSenha);
        linhaSenha.appendChild(inputConfirmacaoSenha);
        linhaSenha.appendChild(btnRedefinirSenha);

        li.appendChild(titulo);
        li.appendChild(cadastro);
        li.appendChild(meta);
        li.appendChild(linha);
        li.appendChild(linhaSenha);
        ul.appendChild(li);
    });
}

async function carregarCoordenadores() {
    const ul = el("listaCoordenadoresAdmin");
    if (!ul || !usuarioEhAdmin) {
        return;
    }

    const coordenadores = await fetchJson("/admin/coordenadores", { headers });
    ul.innerHTML = "";

    if (!Array.isArray(coordenadores) || coordenadores.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhum coordenador cadastrado.";
        ul.appendChild(vazio);
        return;
    }

    coordenadores.forEach((coord) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${coord.nome} (${coord.email}) | Nascimento: ${formatarDataBr(coord.data_nascimento)}`;
        ul.appendChild(li);
    });
}

async function cadastrarProfessor(event) {
    event.preventDefault();
    if (!usuarioEhAdmin) {
        setMensagem("msgProfessor", "Apenas administradores podem cadastrar usuários.", true);
        return;
    }

    const cargoSelecionado = String(el("profCargo").value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    const turmas = listarSelecionados("profTurmasLista");
    const disciplinas = listarSelecionados("profDisciplinasLista");

    if (!ehCoordenador && turmas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma turma.", true);
        return;
    }
    if (!ehCoordenador && disciplinas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma disciplina.", true);
        return;
    }

    const payloadBase = {
        nome: el("profNome").value.trim(),
        email: el("profEmail").value.trim(),
        data_nascimento: el("profDataNascimento").value,
        aulas_semanais: Number(el("profAulas").value),
        turmas,
        disciplinas
    };

    try {
        if (professorEmEdicaoId) {
            if (ehCoordenador) {
                setMensagem("msgProfessor", "A edição deste formulário é exclusiva para professor.", true);
                return;
            }
            await fetchJson(`/admin/professores/${professorEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payloadBase)
            });
            setMensagem("msgProfessor", "Professor atualizado com sucesso.");
        } else {
            const senha = el("profSenha").value.trim();
            if (!validarSenhaForte(senha)) {
                setMensagem("msgProfessor", "Senha fora do padrão de segurança.", true);
                return;
            }

            if (ehCoordenador) {
                await fetchJson("/admin/coordenadores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: payloadBase.nome,
                        email: payloadBase.email,
                        senha,
                        data_nascimento: payloadBase.data_nascimento
                    })
                });
                setMensagem("msgProfessor", "Coordenador cadastrado com sucesso.");
            } else {
                await fetchJson("/admin/professores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        ...payloadBase,
                        senha
                    })
                });
                setMensagem("msgProfessor", "Professor cadastrado com sucesso.");
            }
        }

        limparFormularioProfessor();
        if (ehCoordenador) {
            await carregarCoordenadores();
        } else {
            await Promise.all([carregarProfessores(), atualizarAtribuicoesDocentesSePermitido()]);
        }
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

async function salvarRegrasCota(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/cotas/regras", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                cota_mensal_escola: Number(el("cotaMensalEscola").value),
                base_paginas: Number(el("cotaBase").value),
                paginas_por_aula: Number(el("cotaPorAula").value),
                paginas_por_turma: Number(el("cotaPorTurma").value)
            })
        });

        setMensagem("msgCotas", "Regras de cota atualizadas.");
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function recalcularCotasMes() {
    try {
        const mes = el("mesReferenciaCota").value || mesAtualIso();
        await fetchJson(`/admin/cotas/recalcular?mes=${mes}`, {
            method: "POST",
            headers
        });
        setMensagem("msgCotas", `Cotas recalculadas para ${mes}.`);
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function carregarRecursos() {
    const recursos = await fetchJson("/admin/recursos?incluir_inativos=true", { headers });
    const ul = el("listaRecursosAdmin");
    ul.innerHTML = "";

    recursos.forEach((recurso) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${recurso.nome} (${recurso.tipo})`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `${recurso.descricao || "Sem descrição"} | Quantidade: ${recurso.quantidade_itens ?? 1} | Status: ${recurso.ativo ? "Ativo" : "Inativo"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputQuantidadeItens = document.createElement("input");
        inputQuantidadeItens.type = "number";
        inputQuantidadeItens.min = "1";
        inputQuantidadeItens.value = String(recurso.quantidade_itens ?? 1);
        inputQuantidadeItens.title = "Quantidade de itens";

        const btnSalvarQuantidade = document.createElement("button");
        btnSalvarQuantidade.type = "button";
        btnSalvarQuantidade.innerText = "Salvar quantidade";
        btnSalvarQuantidade.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: recurso.nome,
                        tipo: recurso.tipo,
                        descricao: recurso.descricao || "",
                        quantidade_itens: Number(inputQuantidadeItens.value)
                    })
                });
                setMensagem("msgRecurso", `Quantidade atualizada para ${recurso.nome}.`);
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoRecurso(recurso);
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = recurso.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(recurso.ativo) })
                });
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        linha.appendChild(inputQuantidadeItens);
        linha.appendChild(btnSalvarQuantidade);
        linha.appendChild(btnEditar);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarRecurso(event) {
    event.preventDefault();
    const payload = {
        nome: el("recursoNome").value.trim(),
        tipo: el("recursoTipo").value.trim(),
        descricao: el("recursoDescricao").value.trim(),
        quantidade_itens: Number(el("recursoQuantidadeItens").value)
    };

    try {
        if (recursoEmEdicaoId) {
            await fetchJson(`/admin/recursos/${recursoEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso atualizado com sucesso.");
        } else {
            await fetchJson("/admin/recursos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso cadastrado com sucesso.");
        }

        limparFormularioRecurso();
        await carregarRecursos();
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

function renderListaRelatorio(id, itens, formatador, vazio = "Sem dados no período.") {
    const ul = el(id);
    ul.innerHTML = "";

    if (!itens || itens.length === 0) {
        const li = document.createElement("li");
        li.className = "booking-empty";
        li.innerText = vazio;
        ul.appendChild(li);
        return;
    }

    itens.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = formatador(item);
        ul.appendChild(li);
    });
}

async function carregarRelatorios() {
    try {
        const query = queryPeriodo();
        const relImpressao = await fetchJson(`/admin/relatorio/impressao${query}`, { headers });
        const relRecursos = await fetchJson(`/admin/relatorio/recursos${query}`, { headers });

        renderListaRelatorio(
            "relatorioImpressaoAdmin",
            relImpressao,
            (item) => `${item.nome}: ${item.total_jobs} job(s), ${item.total_paginas} páginas`
        );

        renderListaRelatorio(
            "relatorioRecursosAdmin",
            relRecursos.por_recurso,
            (item) => `${item.recurso_nome} (${item.recurso_tipo}): ${item.total_reservas} reservas, ${item.professores_distintos} professor(es)`
        );

        renderListaRelatorio(
            "relatorioRecursosProfessorAdmin",
            relRecursos.por_professor,
            (item) => `${item.nome}: ${item.total_reservas} reserva(s)`
        );

        setMensagem("msgRelatorios", "Relatórios atualizados.");
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

function registrarEventos() {
    registrarEventosAbasAdmin();
    el("formTurma").addEventListener("submit", cadastrarTurma);
    el("formDisciplina").addEventListener("submit", cadastrarDisciplina);
    el("formRecurso").addEventListener("submit", cadastrarRecurso);
    el("btnCancelarEdicaoRecurso").addEventListener("click", limparFormularioRecurso);

    el("btnGerarRelatorios").addEventListener("click", carregarRelatorios);
    el("btnBuscarHistorico").addEventListener("click", buscarHistorico);

    if (usuarioEhAdmin) {
        el("formProfessor").addEventListener("submit", cadastrarProfessor);
        el("formAtribuicaoDocente").addEventListener("submit", cadastrarAtribuicaoDocente);
        el("formImportarAtribuicoesDocentes").addEventListener("submit", importarAtribuicoesDocentesArquivo);
        el("formCotaRegras").addEventListener("submit", salvarRegrasCota);
        el("profSenha").addEventListener("input", atualizarHintSenha);
        el("profCargo").addEventListener("change", () => {
            if (!professorEmEdicaoId) {
                aplicarModoFormularioProfessor(false);
            }
        });
        el("atribuicaoProfessor").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("atribuicaoDisciplina").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("btnSelecionarTodasTurmasAtribuicao").addEventListener("click", selecionarTodasTurmasAtribuicao);
        el("btnLimparTurmasAtribuicao").addEventListener("click", limparSelecaoTurmasAtribuicao);
        el("btnBaixarModeloAtribuicoesJson").addEventListener("click", baixarModeloAtribuicoesJson);
        el("filtroAtribuicaoProfessor").addEventListener("change", carregarAtribuicoesDocentes);
        el("filtroAtribuicaoTurma").addEventListener("change", carregarAtribuicoesDocentes);
        el("filtroAtribuicaoDisciplina").addEventListener("change", carregarAtribuicoesDocentes);
        el("btnLimparFiltrosAtribuicoes").addEventListener("click", limparFiltrosAtribuicoesDocentes);
        el("btnCancelarEdicaoProfessor").addEventListener("click", limparFormularioProfessor);
        el("btnRecalcularCotas").addEventListener("click", recalcularCotasMes);
        el("mesReferenciaCota").addEventListener("change", carregarProfessores);
    }

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) {
            return;
        }

        aplicarPermissoesTela();

        if (usuarioEhAdmin) {
            el("mesReferenciaCota").value = mesAtualIso();
            await carregarOpcoesProfessor();
            await carregarContextoAtribuicoesDocentes();
            limparFormularioProfessor();
        }
        limparFormularioRecurso();
        registrarEventos();
        if (usuarioEhAdmin) {
            atualizarHintSenha();
        }

        const tarefas = [
            carregarFilaAdmin(),
            buscarHistorico(),
            carregarRecursos(),
            carregarRelatorios(),
            carregarTurmasAdmin(),
            carregarDisciplinasAdmin()
        ];
        if (usuarioEhAdmin) {
            tarefas.push(carregarProfessores(), carregarCoordenadores(), carregarAtribuicoesDocentes());
        }
        await Promise.all(tarefas);
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

init();
