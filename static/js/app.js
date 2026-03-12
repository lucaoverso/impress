const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

function el(id) {
    return document.getElementById(id);
}

function limparSessaoLocal() {
    localStorage.removeItem("token");
    localStorage.removeItem("token_expira_em");
}

function normalizarCargoUsuario(dadosUsuario = {}) {
    const cargo = String(dadosUsuario.cargo || "").trim().toUpperCase();
    if (cargo) {
        return cargo;
    }

    const perfil = String(dadosUsuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return "ADMIN";
    if (perfil === "coordenador") return "COORDENADOR";
    return "PROFESSOR";
}

function parseDataSqlUtc(valor) {
    if (!valor) return null;
    const isoBase = String(valor).trim().replace(" ", "T");
    const data = new Date(`${isoBase}Z`);
    return Number.isNaN(data.getTime()) ? null : data;
}

function sessaoLocalValida() {
    const token = localStorage.getItem("token");
    const expiraEm = localStorage.getItem("token_expira_em");
    if (!token || !expiraEm) {
        return false;
    }
    const expiraData = parseDataSqlUtc(expiraEm);
    if (!expiraData) {
        return false;
    }
    return expiraData.getTime() > Date.now();
}

function validarSenhaForte(senha) {
    return SENHA_FORTE_REGEX.test(senha || "");
}

function setErroLogin(texto) {
    const erro = el("erro");
    if (!erro) return;
    erro.innerText = texto || "";
}

function setMensagemRecuperacao(texto, erro = false) {
    const alvo = el("msgRecuperacao");
    if (!alvo) return;
    alvo.innerText = texto || "";
    alvo.style.color = erro ? "#dc2626" : "#0f766e";
}

function painelRecuperacaoAberto() {
    const painel = el("painelRecuperacao");
    return Boolean(painel) && !painel.hidden;
}

function atualizarBotaoRecuperacao() {
    const botao = el("btnMostrarRecuperacao");
    if (!botao) return;
    botao.innerText = painelRecuperacaoAberto()
        ? "Ocultar recuperacao"
        : "Esqueci minha senha";
}

function alternarPainelRecuperacao() {
    const painel = el("painelRecuperacao");
    if (!painel) return;

    painel.hidden = !painel.hidden;
    if (!painel.hidden) {
        const emailLogin = String(el("email")?.value || "").trim();
        const emailRecuperacao = el("recEmail");
        if (emailRecuperacao && !String(emailRecuperacao.value || "").trim()) {
            emailRecuperacao.value = emailLogin;
        }
    } else {
        setMensagemRecuperacao("");
    }
    atualizarBotaoRecuperacao();
}

async function recuperarSenhaProfessor() {
    const email = String(el("recEmail")?.value || "").trim().toLowerCase();
    const dataNascimento = String(el("recDataNascimento")?.value || "").trim();
    const novaSenha = String(el("recNovaSenha")?.value || "").trim();
    const confirmacao = String(el("recConfirmacaoSenha")?.value || "").trim();

    setMensagemRecuperacao("");

    if (!email || !dataNascimento || !novaSenha || !confirmacao) {
        setMensagemRecuperacao("Preencha todos os campos da recuperacao.", true);
        return;
    }
    if (!validarSenhaForte(novaSenha)) {
        setMensagemRecuperacao("Nova senha fora do padrao de seguranca.", true);
        return;
    }
    if (novaSenha !== confirmacao) {
        setMensagemRecuperacao("A confirmacao da nova senha nao confere.", true);
        return;
    }

    const res = await fetch("/professores/recuperar-senha", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email,
            data_nascimento: dataNascimento,
            nova_senha: novaSenha
        })
    });

    let dados = null;
    try {
        dados = await res.json();
    } catch (err) {
        dados = null;
    }

    if (!res.ok) {
        setMensagemRecuperacao(
            (dados && dados.detail) ? dados.detail : `Erro ${res.status} ao recuperar senha.`,
            true
        );
        return;
    }

    if (el("email")) {
        el("email").value = email;
    }
    if (el("senha")) {
        el("senha").value = "";
    }
    if (el("recNovaSenha")) {
        el("recNovaSenha").value = "";
    }
    if (el("recConfirmacaoSenha")) {
        el("recConfirmacaoSenha").value = "";
    }

    setErroLogin("");
    setMensagemRecuperacao(
        (dados && dados.mensagem) ? dados.mensagem : "Senha redefinida com sucesso."
    );
}

async function login() {
    if (sessaoLocalValida()) {
        window.location.href = "/servicos";
        return;
    }

    if (localStorage.getItem("token")) {
        limparSessaoLocal();
    }
    setErroLogin("");

    const email = String(el("email")?.value || "").trim();
    const senha = String(el("senha")?.value || "");

    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha })
    });

    let data = null;
    try {
        data = await res.json();
    } catch (err) {
        data = null;
    }

    if (!res.ok) {
        setErroLogin((data && data.detail) ? data.detail : "Falha no login.");
        return;
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("token_expira_em", data.expira_em || "");

    const cargo = normalizarCargoUsuario(data);
    if (cargo === "ADMIN") {
        window.location.href = "/admin";
    } else {
        window.location.href = "/servicos";
    }
}

function configurarLoginPage() {
    if (sessaoLocalValida()) {
        window.location.href = "/servicos";
        return;
    }
    if (localStorage.getItem("token")) {
        limparSessaoLocal();
    }

    const btnCadastro = el("btnCadastroProfessor");
    if (btnCadastro) {
        btnCadastro.addEventListener("click", () => {
            window.location.href = "/cadastro-professor";
        });
    }

    const btnMostrarRecuperacao = el("btnMostrarRecuperacao");
    if (btnMostrarRecuperacao) {
        btnMostrarRecuperacao.addEventListener("click", alternarPainelRecuperacao);
    }

    const btnRecuperarSenha = el("btnRecuperarSenha");
    if (btnRecuperarSenha) {
        btnRecuperarSenha.addEventListener("click", recuperarSenhaProfessor);
    }

    ["recEmail", "recDataNascimento", "recNovaSenha", "recConfirmacaoSenha"].forEach((idCampo) => {
        const campo = el(idCampo);
        if (!campo) return;
        campo.addEventListener("keydown", (event) => {
            if (event.key !== "Enter") return;
            event.preventDefault();
            recuperarSenhaProfessor();
        });
    });

    const emailInput = el("email");
    const params = new URLSearchParams(window.location.search);
    const emailPrefill = params.get("email");
    if (emailInput && emailPrefill) {
        emailInput.value = emailPrefill;
    }

    atualizarBotaoRecuperacao();
}

window.addEventListener("DOMContentLoaded", configurarLoginPage);
