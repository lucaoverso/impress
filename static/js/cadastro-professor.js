const { el } = window.AppDom;
const { validarSenhaForte } = window.AppAuth;
const { fetchJson } = window.AppApi;

function setMensagem(texto, erro = false) {
    const target = el("msgCadastro");
    target.innerText = texto || "";
    target.dataset.variant = erro ? "error" : "success";
    target.setAttribute("role", erro ? "alert" : "status");
}

function setErroCampo(inputId, erroId, texto) {
    const input = el(inputId);
    el(erroId).innerText = texto || "";
    input.setAttribute("aria-invalid", texto ? "true" : "false");
    if (texto) input.focus();
}

function setErroGrupo(grupoId, erroId, texto) {
    const grupo = el(grupoId);
    el(erroId).innerText = texto || "";
    grupo.setAttribute("aria-invalid", texto ? "true" : "false");
    if (texto) {
        const primeiraOpcao = grupo.querySelector("input[type='checkbox']");
        (primeiraOpcao || grupo).focus();
    }
}

function limparErrosValidacao() {
    setErroCampo("cadSenha", "cadSenhaErro", "");
    setErroCampo("cadSenhaConfirmacao", "cadSenhaConfirmacaoErro", "");
    setErroGrupo("cadTurmasGrupo", "cadTurmasErro", "");
    setErroGrupo("cadDisciplinasGrupo", "cadDisciplinasErro", "");
}

function atualizarHintSenha() {
    const senha = el("cadSenha").value.trim();
    const hint = el("cadSenhaHint");
    if (!senha) {
        hint.removeAttribute("data-valid");
        return;
    }
    hint.dataset.valid = validarSenhaForte(senha) ? "true" : "false";
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
        label.className = "register-checkbox-item";

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

async function carregarOpcoes() {
    const dados = await fetchJson("/professores/opcoes");
    const turmas = Array.isArray(dados.turmas) ? dados.turmas : [];
    const disciplinas = Array.isArray(dados.disciplinas) ? dados.disciplinas : [];

    renderCheckboxes("cadTurmasLista", turmas, "turma");
    renderCheckboxes("cadDisciplinasLista", disciplinas, "disciplina");

    if (turmas.length === 0 || disciplinas.length === 0) {
        setMensagem("Cadastro indisponível: peça ao administrador para ativar turmas e disciplinas.", true);
    }
}

async function cadastrarProfessor(event) {
    event.preventDefault();
    setMensagem("");
    limparErrosValidacao();

    const nome = el("cadNome").value.trim();
    const email = el("cadEmail").value.trim();
    const senha = el("cadSenha").value.trim();
    const senhaConfirmacao = el("cadSenhaConfirmacao").value.trim();
    const dataNascimento = el("cadDataNascimento").value;
    const aulasSemanais = Number(el("cadAulas").value);
    const turmas = listarSelecionados("cadTurmasLista");
    const disciplinas = listarSelecionados("cadDisciplinasLista");

    if (!validarSenhaForte(senha)) {
        setErroCampo("cadSenha", "cadSenhaErro", "A senha ainda não atende a todos os requisitos.");
        return;
    }

    if (senha !== senhaConfirmacao) {
        setErroCampo("cadSenhaConfirmacao", "cadSenhaConfirmacaoErro", "As senhas digitadas não são iguais.");
        return;
    }

    if (turmas.length === 0) {
        setErroGrupo("cadTurmasGrupo", "cadTurmasErro", "Selecione ao menos uma turma.");
        return;
    }

    if (disciplinas.length === 0) {
        setErroGrupo("cadDisciplinasGrupo", "cadDisciplinasErro", "Selecione ao menos uma disciplina.");
        return;
    }

    const submit = event.currentTarget.querySelector("button[type='submit']");
    let cadastroConcluido = false;
    try {
        submit.disabled = true;
        event.currentTarget.setAttribute("aria-busy", "true");
        submit.innerText = "Criando conta...";
        await fetchJson("/professores/cadastro", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome,
                email,
                senha,
                data_nascimento: dataNascimento,
                aulas_semanais: aulasSemanais,
                turmas,
                disciplinas
            })
        });

        cadastroConcluido = true;
        setMensagem("Conta criada com sucesso. Redirecionando para o login...");
        submit.innerText = "Conta criada";
        setTimeout(() => {
            window.location.href = `/login-page?email=${encodeURIComponent(email)}`;
        }, 1000);
    } catch (err) {
        setMensagem(err.message, true);
    } finally {
        event.currentTarget.removeAttribute("aria-busy");
        if (!cadastroConcluido) {
            submit.disabled = false;
            submit.innerText = "Criar conta";
        }
    }
}

function registrarEventos() {
    el("formCadastroProfessor").addEventListener("submit", cadastrarProfessor);
    el("cadSenha").addEventListener("input", atualizarHintSenha);
    el("btnVoltarLogin").addEventListener("click", () => {
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        registrarEventos();
        atualizarHintSenha();
        await carregarOpcoes();
    } catch (err) {
        setMensagem(err.message, true);
    }
}

init();
