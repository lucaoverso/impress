(function (window) {
    const CARGO_ADMIN = "ADMIN";
    const CARGO_PROFESSOR = "PROFESSOR";
    const CARGO_COORDENADOR = "COORDENADOR";
    const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
    const USUARIO_CACHE_KEY = "usuario_atual";

    function normalizarUsuario(usuario) {
        return usuario && typeof usuario === "object" ? usuario : {};
    }

    function obterToken() {
        return localStorage.getItem("token") || "";
    }

    function garantirToken() {
        const token = obterToken();
        if (!token) {
            window.location.href = "/login-page";
        }
        return token;
    }

    function limparSessaoLocal() {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        sessionStorage.removeItem(USUARIO_CACHE_KEY);
    }

    function encerrarSessao() {
        limparSessaoLocal();
        window.location.href = "/login-page";
    }

    function criarHeadersAuth(token = obterToken()) {
        return {
            Authorization: `Bearer ${token}`,
        };
    }

    function criarHeadersJsonAuth(token = obterToken()) {
        return Object.assign({}, criarHeadersAuth(token), {
            "Content-Type": "application/json",
        });
    }

    function normalizarCargoUsuario(usuario = {}) {
        usuario = normalizarUsuario(usuario);
        const cargo = String(usuario.cargo || "").trim().toUpperCase();
        if (cargo) {
            return cargo;
        }

        const perfil = String(usuario.perfil || "").trim().toLowerCase();
        if (perfil === "admin") return CARGO_ADMIN;
        if (perfil === "coordenador") return CARGO_COORDENADOR;
        return CARGO_PROFESSOR;
    }

    function usuarioEhProfessor(usuario = {}) {
        usuario = normalizarUsuario(usuario);
        if (typeof usuario.eh_professor === "boolean") {
            return usuario.eh_professor;
        }
        return normalizarCargoUsuario(usuario) === CARGO_PROFESSOR;
    }

    function usuarioTemAcessoCoordenacao(usuario = {}) {
        usuario = normalizarUsuario(usuario);
        if (typeof usuario.tem_acesso_coordenacao === "boolean") {
            return usuario.tem_acesso_coordenacao;
        }
        if (usuarioEhProfessor(usuario)) {
            return Boolean(usuario.acesso_coordenacao);
        }
        const cargo = normalizarCargoUsuario(usuario);
        return cargo === CARGO_ADMIN || cargo === CARGO_COORDENADOR;
    }

    function usuarioPodeGerirImpressoes(usuario = {}) {
        usuario = normalizarUsuario(usuario);
        if (typeof usuario.pode_gerir_impressoes === "boolean") {
            return usuario.pode_gerir_impressoes;
        }
        const cargo = normalizarCargoUsuario(usuario);
        return cargo === CARGO_ADMIN || cargo === CARGO_COORDENADOR || (
            usuarioEhProfessor(usuario) && usuarioTemAcessoCoordenacao(usuario)
        );
    }

    function modulosPermitidos(usuario = {}) {
        usuario = normalizarUsuario(usuario);
        if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
            return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
        }

        const cargo = normalizarCargoUsuario(usuario);
        if (cargo === CARGO_ADMIN) {
            return new Set(["impressao", "agendamento", "gestao", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
        }
        if (cargo === CARGO_COORDENADOR) {
            return new Set(["impressao", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
        }
        return new Set(["impressao", "agendamento", "coordenacao", "horario", "apc", "preconselho"]);
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

    function lerUsuarioCache() {
        const bruto = sessionStorage.getItem(USUARIO_CACHE_KEY);
        if (!bruto) {
            return null;
        }

        try {
            return JSON.parse(bruto);
        } catch (_erro) {
            sessionStorage.removeItem(USUARIO_CACHE_KEY);
            return null;
        }
    }

    function salvarUsuarioCache(usuario = null) {
        if (!usuario) {
            sessionStorage.removeItem(USUARIO_CACHE_KEY);
            return null;
        }

        sessionStorage.setItem(USUARIO_CACHE_KEY, JSON.stringify(usuario));
        return usuario;
    }

    async function carregarUsuarioAtual({ forcar = false } = {}) {
        if (!forcar) {
            const usuarioCache = lerUsuarioCache();
            if (usuarioCache) {
                return usuarioCache;
            }
        }

        const token = obterToken();
        if (!token || !window.AppApi?.fetchJson) {
            return null;
        }

        const usuario = await window.AppApi.fetchJson("/me", {
            headers: criarHeadersAuth(token),
        });
        return salvarUsuarioCache(usuario);
    }

    function validarSenhaForte(senha) {
        return SENHA_FORTE_REGEX.test(senha || "");
    }

    window.AppAuth = Object.assign(window.AppAuth || {}, {
        obterToken,
        garantirToken,
        limparSessaoLocal,
        encerrarSessao,
        criarHeadersAuth,
        criarHeadersJsonAuth,
        normalizarCargoUsuario,
        usuarioEhProfessor,
        usuarioTemAcessoCoordenacao,
        usuarioPodeGerirImpressoes,
        modulosPermitidos,
        parseDataSqlUtc,
        sessaoLocalValida,
        validarSenhaForte,
        lerUsuarioCache,
        salvarUsuarioCache,
        carregarUsuarioAtual,
    });
})(window);
