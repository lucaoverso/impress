(function (window, document) {
    const MODULE_ITEMS = [
        {
            key: "impressao",
            href: "/impressao",
            label: "Impressão",
            description: "Enviar arquivos e acompanhar pedidos.",
        },
        {
            key: "agendamento",
            href: "/agendamento",
            label: "Agendamento",
            description: "Reservar equipamentos e recursos.",
        },
        {
            key: "download",
            href: "/download",
            label: "Download",
            description: "Baixar vídeos e músicas para aula.",
        },
        {
            key: "horario",
            href: "/horario-escolar",
            label: "Horário escolar",
            description: "Consultar e organizar a grade.",
        },
        {
            key: "apc",
            href: "/apc",
            label: "Central de anexos",
            description: "Gerenciar entregas e arquivos docentes.",
        },
        {
            key: "preconselho",
            href: "/preconselho",
            label: "Pré-conselho",
            description: "Registrar e acompanhar sinalizações.",
        },
        {
            key: "pcpi",
            href: "/pcpi",
            label: "PCPI",
            description: "Gerar registros administrativos do turno.",
        },
        {
            key: "relatorios",
            href: "/relatorios",
            label: "Relatórios",
            description: "Acompanhar indicadores e painéis.",
        },
        {
            key: "coordenacao",
            href: "/coordenacao",
            label: "Coordenação",
            description: "Centralizar ocorrências e atendimentos.",
        },
        {
            key: "gestao",
            href: "/admin",
            label: "Painel de gestão",
            description: "Administrar pessoas, recursos e impressão.",
        },
    ];

    const state = {
        initialized: false,
        user: null,
        userPromise: null,
        closeTimer: null,
        root: null,
        toggle: null,
        drawer: null,
        panel: null,
        moduleList: null,
        moduleEmpty: null,
    };
    const DRAWER_ANIMATION_MS = 260;

    function obterElementos() {
        state.root = document.querySelector("[data-app-navbar]");
        state.toggle = document.getElementById("appNavbarToggle");
        state.drawer = document.getElementById("appNavbarDrawer");
        state.panel = state.drawer?.querySelector(".app-navbar-panel") || null;
        state.moduleList = document.getElementById("appNavbarModuleList");
        state.moduleEmpty = document.getElementById("appNavbarModuleEmpty");
    }

    function obterModuloAtual() {
        return String(state.root?.dataset.navbarCurrent || "").trim().toLowerCase();
    }

    function normalizarTexto(valor, fallback = "") {
        const texto = String(valor || "").trim();
        return texto || fallback;
    }

    function obterCargoUsuario(usuario = {}) {
        if (window.AppAuth?.normalizarCargoUsuario) {
            return window.AppAuth.normalizarCargoUsuario(usuario);
        }
        return normalizarTexto(usuario?.cargo || usuario?.perfil, "Usuário");
    }

    function obterNomeUsuario(usuario = {}) {
        return normalizarTexto(
            usuario?.nome || usuario?.username || usuario?.email,
            "Usuário não identificado"
        );
    }

    function obterModulosPermitidos(usuario = {}) {
        if (Array.isArray(usuario?.modulos) && usuario.modulos.length > 0) {
            return new Set(
                usuario.modulos
                    .map((item) => String(item || "").trim().toLowerCase())
                    .filter(Boolean)
            );
        }

        if (window.AppAuth?.modulosPermitidos) {
            return window.AppAuth.modulosPermitidos(usuario);
        }

        return new Set();
    }

    function atualizarUsuarioNaInterface(usuario = null) {
        const nomeEl = document.getElementById("appNavbarUserName");
        const metaEl = document.getElementById("appNavbarUserMeta");
        if (!nomeEl || !metaEl) {
            return;
        }

        if (!usuario) {
            nomeEl.innerText = "Usuário não identificado";
            metaEl.innerText = "Não foi possível carregar as permissões desta sessão.";
            return;
        }

        const cargo = obterCargoUsuario(usuario);
        const modulos = obterModulosPermitidos(usuario);
        nomeEl.innerText = obterNomeUsuario(usuario);
        metaEl.innerText = `${cargo} • ${modulos.size} módulo(s) disponível(is)`;
    }

    function criarLinkModulo(item, currentKey) {
        const link = document.createElement("a");
        link.className = "app-navbar-link";
        link.href = item.href;
        link.dataset.navbarModuleKey = item.key;

        const ativo = item.key === currentKey;
        if (ativo) {
            link.classList.add("is-current");
            link.setAttribute("aria-current", "page");
        }

        const copy = document.createElement("span");
        copy.className = "app-navbar-link-copy";

        const titulo = document.createElement("strong");
        titulo.innerText = item.label;

        const descricao = document.createElement("small");
        descricao.innerText = item.description;

        copy.appendChild(titulo);
        copy.appendChild(descricao);

        const badge = document.createElement("span");
        badge.className = "app-navbar-link-badge";
        badge.innerText = ativo ? "Atual" : "Abrir";

        link.appendChild(copy);
        link.appendChild(badge);
        return link;
    }

    function renderizarListaModulos(usuario = null) {
        if (!state.moduleList || !state.moduleEmpty) {
            return;
        }

        const currentKey = obterModuloAtual();
        const permitidos = obterModulosPermitidos(usuario);
        const itens = MODULE_ITEMS.filter((item) => permitidos.has(item.key));

        state.moduleList.innerHTML = "";

        if (!itens.length) {
            state.moduleEmpty.hidden = false;
            return;
        }

        state.moduleEmpty.hidden = true;
        itens.forEach((item) => {
            state.moduleList.appendChild(criarLinkModulo(item, currentKey));
        });
    }

    function sincronizarSecoesAcoesRapidas() {
        document.querySelectorAll("[data-app-navbar-section='page-actions']").forEach((section) => {
            const possuiAcaoVisivel = Array.from(
                section.querySelectorAll("[data-navbar-extra-action='true']")
            ).some((botao) => !botao.hidden);
            section.hidden = !possuiAcaoVisivel;
        });
    }

    function observarAcoesRapidas() {
        const botoes = document.querySelectorAll("[data-navbar-extra-action='true']");
        if (!botoes.length) {
            return;
        }

        const observer = new MutationObserver(() => {
            sincronizarSecoesAcoesRapidas();
        });

        botoes.forEach((botao) => {
            observer.observe(botao, {
                attributes: true,
                attributeFilter: ["hidden"],
            });
        });

        sincronizarSecoesAcoesRapidas();
    }

    function menuAberto() {
        return Boolean(state.drawer && state.drawer.classList.contains("is-visible"));
    }

    function abrirMenu() {
        if (!state.drawer || !state.toggle || !state.panel) {
            return;
        }

        if (state.closeTimer) {
            window.clearTimeout(state.closeTimer);
            state.closeTimer = null;
        }

        state.drawer.hidden = false;
        state.toggle.setAttribute("aria-expanded", "true");
        document.body.classList.add("is-app-navbar-open");
        window.requestAnimationFrame(() => {
            state.drawer.classList.add("is-visible");
            state.panel.focus();
        });
    }

    function fecharMenu() {
        if (!state.drawer || !state.toggle) {
            return;
        }

        if (state.drawer.hidden && !state.drawer.classList.contains("is-visible")) {
            state.toggle.setAttribute("aria-expanded", "false");
            document.body.classList.remove("is-app-navbar-open");
            return;
        }

        if (state.closeTimer) {
            window.clearTimeout(state.closeTimer);
            state.closeTimer = null;
        }

        state.toggle.setAttribute("aria-expanded", "false");
        state.drawer.classList.remove("is-visible");
        state.closeTimer = window.setTimeout(() => {
            state.drawer.hidden = true;
            document.body.classList.remove("is-app-navbar-open");
            state.closeTimer = null;
        }, DRAWER_ANIMATION_MS);
    }

    function alternarMenu() {
        if (menuAberto()) {
            fecharMenu();
            return;
        }
        abrirMenu();
    }

    function registrarEventosGlobais() {
        state.toggle?.addEventListener("click", alternarMenu);

        state.drawer?.addEventListener("click", (event) => {
            const alvoFechar = event.target.closest("[data-app-navbar-close='true']");
            if (alvoFechar) {
                fecharMenu();
                return;
            }

            const acao = event.target.closest("a,button");
            if (!acao || acao.disabled) {
                return;
            }

            if (acao.id === "appNavbarToggle") {
                return;
            }

            fecharMenu();
        });

        state.panel?.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                fecharMenu();
                state.toggle?.focus();
            }
        });

        document.getElementById("btnVoltarServicos")?.addEventListener("click", () => {
            window.location.href = "/servicos";
        });

        document.getElementById("btnSair")?.addEventListener("click", () => {
            if (window.AppAuth?.encerrarSessao) {
                window.AppAuth.encerrarSessao();
                return;
            }
            window.location.href = "/login-page";
        });
    }

    function carregarUsuarioNavbar() {
        if (state.user) {
            return Promise.resolve(state.user);
        }

        if (state.userPromise) {
            return state.userPromise;
        }

        if (!window.AppAuth?.garantirToken || !window.AppAuth?.criarHeadersAuth || !window.AppApi?.fetchJson) {
            return Promise.resolve(null);
        }

        const token = window.AppAuth.garantirToken();
        const headers = window.AppAuth.criarHeadersAuth(token);

        state.userPromise = window.AppApi.fetchJson("/me", { headers })
            .then((usuario) => {
                state.user = usuario;
                state.userPromise = null;
                document.dispatchEvent(new CustomEvent("app-navbar:user-loaded", {
                    detail: usuario,
                }));
                return usuario;
            })
            .catch((erro) => {
                state.userPromise = null;
                throw erro;
            });

        return state.userPromise;
    }

    function aplicarUsuario(usuario = null) {
        atualizarUsuarioNaInterface(usuario);
        renderizarListaModulos(usuario);
        sincronizarSecoesAcoesRapidas();
    }

    function init() {
        if (state.initialized) {
            return;
        }

        obterElementos();
        if (!state.root || !state.toggle || !state.drawer || !state.panel) {
            return;
        }

        state.initialized = true;
        fecharMenu();
        registrarEventosGlobais();
        observarAcoesRapidas();
        aplicarUsuario(null);

        carregarUsuarioNavbar()
            .then((usuario) => {
                aplicarUsuario(usuario);
            })
            .catch(() => {
                aplicarUsuario(null);
            });
    }

    window.AppNavbar = Object.assign(window.AppNavbar || {}, {
        init,
        fecharMenu,
        abrirMenu,
        aplicarUsuario,
        obterUsuarioAtual: () => state.user,
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})(window, document);
