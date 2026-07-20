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
    usuario = usuario && typeof usuario === "object" ? usuario : {};
    if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
        return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
    }

    const cargo = normalizarCargoUsuario(usuario);
    if (cargo === "ADMIN") return new Set(["impressao", "agendamento", "download", "gestao", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
    if (cargo === "COORDENADOR") return new Set(["impressao", "download", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
    return new Set(["impressao", "agendamento", "download", "coordenacao", "horario", "apc", "preconselho"]);
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

carregarUsuario();
