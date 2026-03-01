function limparSessaoLocal() {
    localStorage.removeItem("token");
    localStorage.removeItem("token_expira_em");
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

async function login() {
    if (sessaoLocalValida()) {
        window.location.href = "/servicos";
        return;
    }

    if (localStorage.getItem("token")) {
        limparSessaoLocal();
    }
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;

    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha })
    });

    const data = await res.json();

    if (!res.ok) {
        document.getElementById("erro").innerText = data.detail;
        return;
    }

    localStorage.setItem("token", data.token);
    localStorage.setItem("token_expira_em", data.expira_em || "");

    if (data.perfil === "admin") {
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

    const btnCadastro = document.getElementById("btnCadastroProfessor");
    if (btnCadastro) {
        btnCadastro.addEventListener("click", () => {
            window.location.href = "/cadastro-professor";
        });
    }

    const emailInput = document.getElementById("email");
    const params = new URLSearchParams(window.location.search);
    const emailPrefill = params.get("email");
    if (emailInput && emailPrefill) {
        emailInput.value = emailPrefill;
    }
}

window.addEventListener("DOMContentLoaded", configurarLoginPage);
