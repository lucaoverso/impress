const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

function el(id) {
    return document.getElementById(id);
}

function setMensagem(texto, erro = false) {
    const target = el("msgCadastro");
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function validarSenhaForte(senha) {
    return SENHA_FORTE_REGEX.test(senha || "");
}

function atualizarHintSenha() {
    const senha = el("cadSenha").value.trim();
    const hint = el("cadSenhaHint");
    if (!senha) {
        hint.style.color = "#4b5563";
        return;
    }
    hint.style.color = validarSenhaForte(senha) ? "#0f766e" : "#b42318";
}

function renderCheckboxes(containerId, opcoes, prefixo) {
    const container = el(containerId);
    container.innerHTML = "";

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

function normalizarErro(res, body) {
    if (body && body.detail) return body.detail;
    return `Erro ${res.status}`;
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let body = null;
    try {
        body = await res.json();
    } catch (err) {
        body = null;
    }

    if (!res.ok) {
        throw new Error(normalizarErro(res, body));
    }
    return body;
}

async function carregarOpcoes() {
    const dados = await fetchJson("/professores/opcoes");
    const turmas = Array.isArray(dados.turmas) ? dados.turmas : [];
    const disciplinas = Array.isArray(dados.disciplinas) ? dados.disciplinas : [];

    renderCheckboxes("cadTurmasLista", turmas, "turma");
    renderCheckboxes("cadDisciplinasLista", disciplinas, "disciplina");
}

async function cadastrarProfessor(event) {
    event.preventDefault();
    setMensagem("");

    const nome = el("cadNome").value.trim();
    const email = el("cadEmail").value.trim();
    const senha = el("cadSenha").value.trim();
    const senhaConfirmacao = el("cadSenhaConfirmacao").value.trim();
    const dataNascimento = el("cadDataNascimento").value;
    const aulasSemanais = Number(el("cadAulas").value);
    const turmas = listarSelecionados("cadTurmasLista");
    const disciplinas = listarSelecionados("cadDisciplinasLista");

    if (!validarSenhaForte(senha)) {
        setMensagem("Senha fora do padrão de segurança.", true);
        return;
    }

    if (senha !== senhaConfirmacao) {
        setMensagem("A confirmação de senha não confere.", true);
        return;
    }

    if (turmas.length === 0) {
        setMensagem("Selecione ao menos uma turma.", true);
        return;
    }

    if (disciplinas.length === 0) {
        setMensagem("Selecione ao menos uma disciplina.", true);
        return;
    }

    try {
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

        setMensagem("Conta criada com sucesso. Redirecionando para o login...");
        setTimeout(() => {
            window.location.href = `/login-page?email=${encodeURIComponent(email)}`;
        }, 1000);
    } catch (err) {
        setMensagem(err.message, true);
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
