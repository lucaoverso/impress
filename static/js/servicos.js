const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchComAuth } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);

function modulosPermitidos(usuario = {}) {
    if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
        return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
    }

    const cargo = normalizarCargoUsuario(usuario);
    if (cargo === "ADMIN") return new Set(["impressao", "agendamento", "download", "gestao", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
    if (cargo === "COORDENADOR") return new Set(["download", "coordenacao", "horario", "apc", "preconselho"]);
    return new Set(["impressao", "agendamento", "download", "apc", "preconselho"]);
}

function aplicarVisibilidadeModulos(modulos) {
    document.querySelectorAll(".service-card[data-modulo]").forEach((card) => {
        const modulo = String(card.dataset.modulo || "").trim().toLowerCase();
        card.hidden = !modulos.has(modulo);
    });
}

async function carregarUsuario() {
    try {
        const res = await fetchComAuth("/me", { headers });
        if (!res.ok) {
            encerrarSessao();
            return;
        }

        const usuario = await res.json();
        const titulo = document.getElementById("tituloBoasVindas");
        titulo.innerText = `Olá, ${usuario.nome.split(" ")[0]}. Escolha o serviço`;
        aplicarVisibilidadeModulos(modulosPermitidos(usuario));
    } catch (err) {
        encerrarSessao();
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

    const btnIrHorario = document.getElementById("cardHorario");
    if (btnIrHorario) {
        btnIrHorario.addEventListener("click", () => {
            window.location.href = "/horario-escolar";
        });
    }

    const btnIrApc = document.getElementById("cardApc");
    if (btnIrApc) {
        btnIrApc.addEventListener("click", () => {
            window.location.href = "/apc";
        });
    }

    const btnIrPcpi = document.getElementById("cardPcpi");
    if (btnIrPcpi) {
        btnIrPcpi.addEventListener("click", () => {
            window.location.href = "/pcpi";
        });
    }

    document.getElementById("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });
}

registrarEventos();
carregarUsuario();
