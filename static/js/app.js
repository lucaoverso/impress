async function login() {
    const token = localStorage.getItem("token");
    if (token) {
        window.location.href = "/servicos";
        return;
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

    if (data.perfil === "admin") {
        window.location.href = "/admin";
    } else {
        window.location.href = "/servicos";
    }
}

function configurarLoginPage() {
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
