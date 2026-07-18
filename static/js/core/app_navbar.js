(function (window, document) {
    const FEATURES = [
        ["impressao", "/impressao", "Enviar para impressão", "Envie arquivos e acompanhe seus pedidos"],
        ["impressao", "/impressao#historico", "Meus pedidos de impressão", "Consulte pedidos e status de impressão"],
        ["agendamento", "/agendamento", "Agendar equipamento", "Reserve projetores, notebooks e outros recursos"],
        ["agendamento", "/agendamento#agenda", "Agenda de recursos", "Consulte reservas e horários disponíveis"],
        ["download", "/download", "Baixar vídeo ou áudio", "Prepare mídias para uso em aula"],
        ["horario", "/horario-escolar", "Horário escolar", "Consulte turmas, professores e aulas"],
        ["apc", "/apc", "Central de anexos", "Envie e acompanhe documentos docentes"],
        ["preconselho", "/preconselho", "Pré-conselho", "Registre e acompanhe sinalizações"],
        ["pcpi", "/pcpi", "Registros PCPI", "Gere registros administrativos do turno"],
        ["relatorios", "/relatorios", "Relatórios", "Consulte indicadores e informações da escola"],
        ["coordenacao", "/coordenacao", "Coordenação", "Acompanhe ocorrências e atendimentos"],
        ["gestao", "/admin", "Painel de gestão", "Administre usuários, recursos e impressão"],
        ["servicos", "/servicos", "Todos os serviços", "Volte à central de serviços do sistema"],
    ].map(([module, href, label, description]) => ({ module, href, label, description }));

    const state = { user: null, initialized: false, activeResult: -1 };
    const el = (id) => document.getElementById(id);

    function normalize(value) {
        return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    }

    function userName(user = {}) {
        user = user || {};
        return String(user.nome || user.username || user.email || "Usuário").trim();
    }

    function userRole(user = {}) {
        user = user || {};
        if (window.AppAuth?.normalizarCargoUsuario) return window.AppAuth.normalizarCargoUsuario(user);
        return String(user.cargo || user.perfil || "Usuário").trim().toUpperCase();
    }

    function userModules(user = {}) {
        user = user || {};
        if (Array.isArray(user.modulos)) return new Set(user.modulos.map(normalize));
        return window.AppAuth?.modulosPermitidos?.(user) || new Set();
    }

    function initials(name) {
        const parts = String(name || "U").trim().split(/\s+/).filter(Boolean);
        return ((parts[0]?.[0] || "U") + (parts.length > 1 ? parts.at(-1)[0] : "")).toUpperCase();
    }

    function allowedFeatures() {
        const modules = userModules(state.user || {});
        return FEATURES.filter((item) => item.module === "servicos" || modules.has(item.module));
    }

    function closeSearch() {
        const results = el("appNavbarSearchResults");
        const input = el("appNavbarSearch");
        if (results) results.hidden = true;
        input?.setAttribute("aria-expanded", "false");
        state.activeResult = -1;
    }

    function renderSearch(query) {
        const results = el("appNavbarSearchResults");
        const input = el("appNavbarSearch");
        if (!results || !input) return;
        const term = normalize(query);
        if (!term) return closeSearch();

        const matches = allowedFeatures().filter((item) =>
            normalize(`${item.label} ${item.description}`).includes(term)
        ).slice(0, 7);
        results.replaceChildren();

        if (!matches.length) {
            const empty = document.createElement("p");
            empty.className = "app-navbar-search-empty";
            empty.textContent = "Nenhuma funcionalidade encontrada.";
            results.appendChild(empty);
        } else {
            matches.forEach((item, index) => {
                const link = document.createElement("a");
                link.className = "app-navbar-search-result";
                link.href = item.href;
                link.role = "option";
                link.dataset.resultIndex = index;
                const title = document.createElement("strong");
                const detail = document.createElement("small");
                title.textContent = item.label;
                detail.textContent = item.description;
                link.append(title, detail);
                results.appendChild(link);
            });
        }
        results.hidden = false;
        input.setAttribute("aria-expanded", "true");
        state.activeResult = -1;
    }

    function moveSearchSelection(direction) {
        const links = [...document.querySelectorAll(".app-navbar-search-result")];
        if (!links.length) return;
        state.activeResult = (state.activeResult + direction + links.length) % links.length;
        links.forEach((link, index) => link.classList.toggle("is-active", index === state.activeResult));
        links[state.activeResult].scrollIntoView({ block: "nearest" });
    }

    function profileOpen() {
        return !el("appNavbarProfileMenu")?.hidden;
    }

    function setProfileOpen(open) {
        const menu = el("appNavbarProfileMenu");
        const toggle = el("appNavbarProfileToggle");
        if (!menu || !toggle) return;
        menu.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
    }

    async function loadUsage() {
        const value = el("appNavbarUsageValue");
        const detail = el("appNavbarUsageDetail");
        if (!value || !detail || !state.user) return;
        if (state.user.eh_gestor) {
            value.textContent = "Uso ilimitado";
            detail.textContent = "Seu perfil não possui limite mensal de impressão.";
            return;
        }
        try {
            const quota = await window.AppApi.fetchJson("/impressao/minha-cota", {
                headers: window.AppAuth.criarHeadersAuth(),
            });
            value.textContent = `${quota.restante ?? 0} páginas disponíveis`;
            detail.textContent = `${quota.usadas ?? 0} de ${quota.limite ?? 0} páginas usadas neste mês.`;
        } catch (_error) {
            value.textContent = "Uso indisponível";
            detail.textContent = "Não foi possível consultar sua cota agora.";
        }
    }

    function applyUser(user) {
        state.user = user || null;
        const name = userName(user);
        const avatar = initials(name);
        if (el("appNavbarUserName")) el("appNavbarUserName").textContent = name;
        if (el("appNavbarUserMeta")) el("appNavbarUserMeta").textContent = user ? `${user.email || "Sem e-mail"} • ${userRole(user)}` : "Sessão não identificada";
        if (el("appNavbarAvatarInitials")) el("appNavbarAvatarInitials").textContent = avatar;
        if (el("appNavbarProfileInitials")) el("appNavbarProfileInitials").textContent = avatar;
        el("appNavbarProfileToggle")?.setAttribute("aria-label", `Abrir perfil de ${name}`);
        loadUsage();
    }

    function openProfileDialog() {
        const dialog = el("appNavbarProfileDialog");
        if (!dialog || !state.user) return;
        el("appProfileName").value = state.user.nome || "";
        el("appProfileEmail").value = state.user.email || "";
        el("appProfilePassword").value = "";
        el("appProfileFeedback").hidden = true;
        setProfileOpen(false);
        dialog.showModal();
    }

    async function saveProfile(event) {
        event.preventDefault();
        const submit = el("appProfileSubmit");
        const feedback = el("appProfileFeedback");
        const payload = {
            nome: el("appProfileName").value.trim(),
            email: el("appProfileEmail").value.trim(),
            nova_senha: el("appProfilePassword").value,
        };
        submit.disabled = true;
        submit.textContent = "Salvando...";
        feedback.hidden = true;
        feedback.classList.remove("is-success");
        try {
            const user = await window.AppApi.fetchJson("/me/profile", {
                method: "PATCH",
                headers: window.AppAuth.criarHeadersJsonAuth(),
                body: JSON.stringify(payload),
            });
            applyUser(user);
            sessionStorage.setItem("usuario_atual", JSON.stringify(user));
            feedback.textContent = "Perfil atualizado com sucesso.";
            feedback.classList.add("is-success");
            feedback.hidden = false;
            el("appProfilePassword").value = "";
        } catch (error) {
            feedback.textContent = error.message || "Não foi possível atualizar o perfil.";
            feedback.hidden = false;
        } finally {
            submit.disabled = false;
            submit.textContent = "Salvar alterações";
        }
    }

    function bindEvents() {
        const search = el("appNavbarSearch");
        search?.addEventListener("input", () => renderSearch(search.value));
        search?.addEventListener("focus", () => setProfileOpen(false));
        search?.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                moveSearchSelection(event.key === "ArrowDown" ? 1 : -1);
            } else if (event.key === "Enter" && state.activeResult >= 0) {
                event.preventDefault();
                document.querySelector(`.app-navbar-search-result[data-result-index="${state.activeResult}"]`)?.click();
            } else if (event.key === "Escape") closeSearch();
        });
        el("appNavbarProfileToggle")?.addEventListener("click", () => setProfileOpen(!profileOpen()));
        el("appNavbarEditProfile")?.addEventListener("click", openProfileDialog);
        el("appNavbarProfileForm")?.addEventListener("submit", saveProfile);
        document.querySelectorAll("[data-profile-dialog-close]").forEach((button) =>
            button.addEventListener("click", () => el("appNavbarProfileDialog")?.close())
        );
        el("btnSair")?.addEventListener("click", () => {
            if (window.AppAuth?.encerrarSessao) window.AppAuth.encerrarSessao();
            else window.location.href = "/login-page";
        });
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".app-navbar-search")) closeSearch();
            if (!event.target.closest(".app-navbar-account")) setProfileOpen(false);
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && profileOpen()) {
                setProfileOpen(false);
                el("appNavbarProfileToggle")?.focus();
            }
        });
    }

    function init() {
        if (state.initialized || !document.querySelector("[data-app-navbar]")) return;
        state.initialized = true;
        bindEvents();
        window.AppAuth?.carregarUsuarioAtual?.().then(applyUser).catch(() => applyUser(null));
        document.addEventListener("app:user-loaded", (event) => applyUser(event.detail));
    }

    window.AppNavbar = Object.assign(window.AppNavbar || {}, {
        init,
        aplicarUsuario: applyUser,
        definirUsuario: applyUser,
        obterUsuarioAtual: () => state.user,
    });
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, { once: true }) : init();
})(window, document);
