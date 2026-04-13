const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": `Bearer ${token}`
};

function normalizarCargoUsuario(usuario = {}) {
    const cargo = String(usuario.cargo || "").trim().toUpperCase();
    if (cargo) {
        return cargo;
    }

    const perfil = String(usuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return "ADMIN";
    if (perfil === "coordenador") return "COORDENADOR";
    return "PROFESSOR";
}

function modulosPermitidos(usuario = {}) {
    if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
        return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
    }

    const cargo = normalizarCargoUsuario(usuario);
    if (cargo === "ADMIN") return new Set(["impressao", "agendamento", "gestao", "coordenacao", "pcpi", "preconselho"]);
    if (cargo === "COORDENADOR") return new Set(["coordenacao", "preconselho"]);
    return new Set(["impressao", "agendamento", "preconselho"]);
}

function aplicarVisibilidadeModulos(modulos) {
    document.querySelectorAll(".service-card[data-modulo]").forEach((card) => {
        const modulo = String(card.dataset.modulo || "").trim().toLowerCase();
        card.hidden = !modulos.has(modulo);
    });
}

async function carregarUsuario() {
    try {
        const res = await fetch("/me", { headers });
        if (!res.ok) {
            localStorage.removeItem("token");
            localStorage.removeItem("token_expira_em");
            window.location.href = "/login-page";
            return;
        }

        const usuario = await res.json();
        const titulo = document.getElementById("tituloBoasVindas");
        titulo.innerText = `Olá, ${usuario.nome.split(" ")[0]}. Escolha o serviço`;
        aplicarVisibilidadeModulos(modulosPermitidos(usuario));
    } catch (err) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    }
}

function registrarEventos() {
    document.getElementById("cardImpressao").addEventListener("click", () => {
        window.location.href = "/impressao";
    });

    document.getElementById("cardAgendamento").addEventListener("click", () => {
        window.location.href = "/agendamento";
    });

    document.getElementById("cardDownload").addEventListener("click", () => {
        window.location.href = "/download";
    });

    const btnIrPreconselho = document.getElementById("cardPreconselho");
    if (btnIrPreconselho) {
        btnIrPreconselho.addEventListener("click", () => {
            window.location.href = "/preconselho";
        });
    }

    document.getElementById("cardGestao").addEventListener("click", () => {
        window.location.href = "/admin";
    });

    const btnIrCoordenacao = document.getElementById("cardCoordenacao");
    if (btnIrCoordenacao) {
        btnIrCoordenacao.addEventListener("click", () => {
            window.location.href = "/coordenacao";
        });
    }

    const btnIrPcpi = document.getElementById("cardPcpi");
    if (btnIrPcpi) {
        btnIrPcpi.addEventListener("click", () => {
            window.location.href = "/pcpi";
        });
    }

    document.getElementById("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

registrarEventos();
carregarUsuario();
