(function (window) {
    const CARGO_ADMIN = "ADMIN";
    const CARGO_PROFESSOR = "PROFESSOR";
    const CARGO_COORDENADOR = "COORDENADOR";
    const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

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
        if (typeof usuario.eh_professor === "boolean") {
            return usuario.eh_professor;
        }
        return normalizarCargoUsuario(usuario) === CARGO_PROFESSOR;
    }

    function usuarioTemAcessoCoordenacao(usuario = {}) {
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
        if (typeof usuario.pode_gerir_impressoes === "boolean") {
            return usuario.pode_gerir_impressoes;
        }
        return normalizarCargoUsuario(usuario) === CARGO_ADMIN || (
            usuarioEhProfessor(usuario) && usuarioTemAcessoCoordenacao(usuario)
        );
    }

    function modulosPermitidos(usuario = {}) {
        if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
            return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
        }

        const cargo = normalizarCargoUsuario(usuario);
        if (cargo === CARGO_ADMIN) {
            return new Set(["impressao", "agendamento", "gestao", "coordenacao", "pcpi", "preconselho"]);
        }
        if (cargo === CARGO_COORDENADOR) {
            return new Set(["coordenacao", "pcpi", "preconselho"]);
        }
        return new Set(["impressao", "agendamento", "preconselho"]);
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
    });
})(window);
