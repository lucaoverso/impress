const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": `Bearer ${token}`
};

async function carregarUsuario() {
    try {
        const res = await fetch("/me", { headers });
        if (!res.ok) {
            localStorage.removeItem("token");
            window.location.href = "/login-page";
            return;
        }

        const usuario = await res.json();
        const titulo = document.getElementById("tituloBoasVindas");
        titulo.innerText = `Olá, ${usuario.nome}. Escolha o serviço`;
    } catch (err) {
        localStorage.removeItem("token");
        window.location.href = "/login-page";
    }
}

function registrarEventos() {
    document.getElementById("btnIrImpressao").addEventListener("click", () => {
        window.location.href = "/impressao";
    });

    document.getElementById("btnIrAgendamento").addEventListener("click", () => {
        window.location.href = "/agendamento";
    });

    document.getElementById("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        window.location.href = "/login-page";
    });
}

registrarEventos();
carregarUsuario();
