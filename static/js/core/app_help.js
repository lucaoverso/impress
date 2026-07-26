(() => {
    const el = (id) => document.getElementById(id);
    let contextsPromise = null;
    let closeTimer = null;

    function normalizePath(pathname) {
        const path = String(pathname || "/").replace(/\/+$/, "");
        return path || "/";
    }

    function isVisible(element) {
        return Boolean(
            element
            && !element.closest("[hidden], [aria-hidden='true'], [inert]")
            && element.getClientRects().length
        );
    }

    function activeTab() {
        const sidebarTab = document.querySelector(
            "[data-app-sidebar] [data-app-sidebar-tab-value].is-active"
        );
        if (sidebarTab?.dataset.appSidebarTabValue) return sidebarTab.dataset.appSidebarTabValue;

        const trigger = document.querySelector([
            "[data-coord-tab-trigger][aria-selected='true']",
            "[data-relatorios-tab-trigger][aria-selected='true']",
        ].join(","));
        return trigger?.dataset.coordTabTrigger || trigger?.dataset.relatoriosTabTrigger || "";
    }

    function activeStep(path, tab) {
        const root = document.documentElement.dataset;
        if (path === "/impressao") return root.printingCurrentStep || "";
        if (path === "/agendamento") return root.schedulerCurrentStep || "";
        if (path !== "/coordenacao" || tab !== "ocorrencias") return "";

        const formView = document.querySelector("[data-ocorrencia-view='form'].is-active");
        const step = document.querySelector("[data-ocorrencia-step-trigger][aria-current='step']");
        return isVisible(formView) && isVisible(step) ? step.dataset.ocorrenciaStepTrigger || "" : "";
    }

    function contextCandidates() {
        const path = normalizePath(window.location.pathname);
        const tab = activeTab();
        const step = activeStep(path, tab);
        const candidates = [];
        if (tab && step) candidates.push(`${path}|tab=${tab}|step=${step}`);
        if (tab) candidates.push(`${path}|tab=${tab}`);
        if (step) candidates.push(`${path}|step=${step}`);
        candidates.push(path);
        return [...new Set(candidates)];
    }

    async function loadContexts(toggle) {
        if (!contextsPromise) {
            contextsPromise = fetch(toggle.dataset.helpContentUrl, {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            }).then((response) => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            }).then((payload) => {
                if (!payload?.contexts || typeof payload.contexts !== "object") {
                    throw new Error("Conteúdo de ajuda inválido");
                }
                return payload.contexts;
            }).catch((error) => {
                contextsPromise = null;
                throw error;
            });
        }
        return contextsPromise;
    }

    function appendList(body, title, items, ordered = false, className = "") {
        if (!Array.isArray(items) || !items.length) return;
        const section = document.createElement("section");
        section.className = `app-help-section ${className}`.trim();
        const heading = document.createElement("h3");
        const list = document.createElement(ordered ? "ol" : "ul");
        heading.textContent = title;
        items.forEach((text) => {
            const item = document.createElement("li");
            item.textContent = text;
            list.appendChild(item);
        });
        section.append(heading, list);
        body.appendChild(section);
    }

    function renderContent(content) {
        const title = el("appHelpTitle");
        const body = el("appHelpBody");
        if (!title || !body) return;
        title.textContent = content.title;
        body.replaceChildren();
        body.removeAttribute("aria-busy");

        const objective = document.createElement("p");
        objective.className = "app-help-objective";
        objective.textContent = content.objective;
        body.appendChild(objective);
        appendList(body, "Antes de decidir", content.decisions);
        appendList(body, "Como usar esta tela", content.steps, true);
        appendList(body, "Atenção", content.cautions, false, "app-help-cautions");
        body.scrollTop = 0;
    }

    function renderLoading() {
        const body = el("appHelpBody");
        if (!body) return;
        el("appHelpTitle").textContent = "Carregando ajuda";
        body.setAttribute("aria-busy", "true");
        body.replaceChildren();
        const skeleton = document.createElement("div");
        skeleton.className = "app-help-skeleton";
        skeleton.setAttribute("aria-hidden", "true");
        skeleton.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
        const copy = document.createElement("p");
        copy.className = "sr-only";
        copy.textContent = "Carregando orientações para esta tela.";
        body.append(skeleton, copy);
    }

    function renderState(message, retry = false) {
        const body = el("appHelpBody");
        if (!body) return;
        el("appHelpTitle").textContent = "Ajuda desta tela";
        body.removeAttribute("aria-busy");
        body.replaceChildren();
        const state = document.createElement("div");
        const copy = document.createElement("p");
        state.className = "app-help-state";
        copy.textContent = message;
        state.appendChild(copy);
        if (retry) {
            const button = document.createElement("button");
            button.className = "app-help-retry";
            button.type = "button";
            button.textContent = "Tentar novamente";
            button.addEventListener("click", openHelp);
            state.appendChild(button);
        }
        body.appendChild(state);
    }

    function finishClose(dialog, toggle) {
        window.clearTimeout(closeTimer);
        closeTimer = null;
        dialog.classList.remove("is-closing");
        if (dialog.open) dialog.close();
        document.body.classList.remove("app-help-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus({ preventScroll: true });
    }

    function closeHelp() {
        const dialog = el("appHelpDialog");
        const toggle = el("appNavbarHelpToggle");
        if (!dialog?.open || !toggle || dialog.classList.contains("is-closing")) return;
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (reducedMotion) return finishClose(dialog, toggle);
        dialog.classList.add("is-closing");
        closeTimer = window.setTimeout(() => finishClose(dialog, toggle), 180);
    }

    async function openHelp() {
        const dialog = el("appHelpDialog");
        const toggle = el("appNavbarHelpToggle");
        if (!dialog || !toggle) return;
        if (!dialog.open) {
            dialog.showModal();
            document.body.classList.add("app-help-open");
            toggle.setAttribute("aria-expanded", "true");
            requestAnimationFrame(() => el("appHelpClose")?.focus());
        }
        renderLoading();
        try {
            const contexts = await loadContexts(toggle);
            if (!dialog.open) return;
            const context = contextCandidates().map((key) => contexts[key]).find(Boolean);
            context
                ? renderContent(context)
                : renderState("Ajuda ainda não cadastrada para esta tela.");
        } catch (_error) {
            if (dialog.open) renderState("Não foi possível carregar a ajuda agora.", true);
        }
    }

    function init() {
        const dialog = el("appHelpDialog");
        const toggle = el("appNavbarHelpToggle");
        if (!dialog || !toggle) return;
        toggle.addEventListener("click", openHelp);
        el("appHelpClose")?.addEventListener("click", closeHelp);
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            closeHelp();
        });
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) closeHelp();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && dialog.open) {
                event.preventDefault();
                closeHelp();
            }
        });
        dialog.addEventListener("close", () => {
            document.body.classList.remove("app-help-open");
            toggle.setAttribute("aria-expanded", "false");
            dialog.classList.remove("is-closing");
        });
    }

    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})();
