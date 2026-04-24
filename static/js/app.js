const { el } = window.AppDom;
const {
    limparSessaoLocal,
    normalizarCargoUsuario,
    sessaoLocalValida,
    validarSenhaForte,
} = window.AppAuth;

let ultimoElementoFocadoRecuperacao = null;

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

function modalRecuperacaoAberto() {
    const modal = el("modalRecuperacaoSenha");
    return Boolean(modal) && !modal.hidden;
}

function atualizarBotaoRecuperacao(aberto) {
    const botao = el("btnMostrarRecuperacao");
    if (!botao) return;
    botao.setAttribute("aria-expanded", aberto ? "true" : "false");
}

function obterCampoInicialRecuperacao() {
    const campos = [
        el("recEmail"),
        el("recDataNascimento"),
        el("recNovaSenha"),
        el("recConfirmacaoSenha"),
    ].filter(Boolean);

    return campos.find((campo) => !campo.value.trim()) || campos[0] || el("painelRecuperacaoSenha");
}

function abrirModalRecuperacao() {
    const modal = el("modalRecuperacaoSenha");
    if (!modal || !modal.hidden) return;

    const focoAtual = document.activeElement;
    ultimoElementoFocadoRecuperacao = focoAtual && typeof focoAtual.focus === "function" ? focoAtual : null;

    const emailLogin = String(el("email")?.value || "").trim().toLowerCase();
    const recEmail = el("recEmail");
    if (recEmail && emailLogin && !recEmail.value.trim()) {
        recEmail.value = emailLogin;
    }

    setMensagemRecuperacao("");
    modal.hidden = false;
    document.body.classList.add("auth-modal-open");
    atualizarBotaoRecuperacao(true);

    requestAnimationFrame(() => {
        const campoInicial = obterCampoInicialRecuperacao();
        if (campoInicial && typeof campoInicial.focus === "function") {
            campoInicial.focus();
        }
    });
}

function fecharModalRecuperacao({ restaurarFoco = true } = {}) {
    const modal = el("modalRecuperacaoSenha");
    if (!modal || modal.hidden) return;

    modal.hidden = true;
    setMensagemRecuperacao("");
    document.body.classList.remove("auth-modal-open");
    atualizarBotaoRecuperacao(false);

    if (restaurarFoco && ultimoElementoFocadoRecuperacao && typeof ultimoElementoFocadoRecuperacao.focus === "function") {
        ultimoElementoFocadoRecuperacao.focus();
    }
    ultimoElementoFocadoRecuperacao = null;
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
        btnMostrarRecuperacao.addEventListener("click", abrirModalRecuperacao);
    }

    const formRecuperacao = el("formRecuperacaoSenha");
    if (formRecuperacao) {
        formRecuperacao.addEventListener("submit", async (event) => {
            event.preventDefault();
            await recuperarSenhaProfessor();
        });
    }

    ["btnFecharRecuperacao", "btnCancelarRecuperacao"].forEach((idBotao) => {
        const botao = el(idBotao);
        if (!botao) return;
        botao.addEventListener("click", () => {
            fecharModalRecuperacao();
        });
    });

    const modalRecuperacao = el("modalRecuperacaoSenha");
    if (modalRecuperacao) {
        modalRecuperacao.addEventListener("click", (event) => {
            if (event.target === modalRecuperacao) {
                fecharModalRecuperacao();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modalRecuperacaoAberto()) {
            fecharModalRecuperacao();
        }
    });

    const emailInput = el("email");
    const params = new URLSearchParams(window.location.search);
    const emailPrefill = params.get("email");
    if (emailInput && emailPrefill) {
        emailInput.value = emailPrefill;
    }

    atualizarBotaoRecuperacao(false);
}

window.addEventListener("DOMContentLoaded", configurarLoginPage);
