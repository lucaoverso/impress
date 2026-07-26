(function (window, document) {
    const state = { filter: "all", page: 1 };
    const el = (id) => document.getElementById(id);
    const headers = () => window.AppAuth.criarHeadersAuth();

    function parseUtc(value) {
        return new Date(`${String(value || "").replace(" ", "T")}Z`);
    }

    function isToday(value) {
        return parseUtc(value).toDateString() === new Date().toDateString();
    }

    function formatDate(value) {
        return parseUtc(value).toLocaleString("pt-BR", {
            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
        });
    }

    function showState(message, retry = false) {
        const box = el("notificationsPageState");
        box.replaceChildren();
        const icon = document.createElement("i");
        icon.className = retry ? "bi bi-wifi-off" : "bi bi-bell-check";
        icon.setAttribute("aria-hidden", "true");
        const copy = document.createElement("p");
        copy.textContent = message;
        box.append(icon, copy);
        if (retry) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button";
            button.textContent = "Tentar novamente";
            button.addEventListener("click", load);
            box.appendChild(button);
        }
        box.hidden = false;
        el("notificationsPageList").replaceChildren();
        el("notificationsPagination").replaceChildren();
    }

    function itemButton(item) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "app-notification-item";
        if (!item.read_at) button.classList.add("is-unread");
        if (item.priority === "urgent") button.classList.add("is-urgent");
        const dot = document.createElement("span");
        dot.className = "app-notification-dot";
        dot.setAttribute("aria-hidden", "true");
        const copy = document.createElement("span");
        copy.className = "app-notification-copy";
        const title = document.createElement("strong");
        title.textContent = item.title;
        const body = document.createElement("span");
        body.textContent = item.body;
        const time = document.createElement("time");
        time.dateTime = item.available_at;
        time.textContent = formatDate(item.available_at);
        copy.append(title, body, time);
        button.append(dot, copy);
        button.addEventListener("click", async () => {
            await window.AppApi.fetchJson(`/notifications/${item.id}/read`, {
                method: "POST", headers: headers(),
            }).catch(() => null);
            window.location.href = item.action_url || "/notificacoes";
        });
        return button;
    }

    function renderGroup(list, label, items) {
        if (!items.length) return;
        const heading = document.createElement("h3");
        heading.className = "app-notifications-group-title";
        heading.textContent = label;
        list.appendChild(heading);
        items.forEach((item) => list.appendChild(itemButton(item)));
    }

    function renderPagination(result) {
        const nav = el("notificationsPagination");
        nav.replaceChildren();
        if (result.pages <= 1) return;
        const previous = document.createElement("button");
        previous.type = "button";
        previous.textContent = "Página anterior";
        previous.disabled = state.page <= 1;
        previous.addEventListener("click", () => { state.page -= 1; load(); });
        const summary = document.createElement("span");
        summary.textContent = `Página ${state.page} de ${result.pages}`;
        const next = document.createElement("button");
        next.type = "button";
        next.textContent = "Próxima página";
        next.disabled = state.page >= result.pages;
        next.addEventListener("click", () => { state.page += 1; load(); });
        nav.append(previous, summary, next);
    }

    async function load() {
        if (!navigator.onLine) {
            showState("Sem conexão. As notificações salvas aparecerão quando você voltar a ficar online.", true);
            return;
        }
        try {
            const result = await window.AppApi.fetchJson(
                `/notifications?filter=${state.filter}&page=${state.page}&page_size=20`,
                { headers: headers() }
            );
            el("notificationsUnreadSummary").textContent = result.unread_count
                ? `${result.unread_count} não lidas`
                : "Nenhum aviso pendente de leitura";
            window.AppNotifications?.refresh?.();
            if (!result.items.length) {
                showState(state.filter === "unread"
                    ? "Você leu todos os avisos. Troque para “Todas” para consultar o histórico."
                    : "Nenhuma notificação ainda. Prazos e comunicados aparecerão aqui.");
                return;
            }
            el("notificationsPageState").hidden = true;
            const list = el("notificationsPageList");
            list.replaceChildren();
            renderGroup(list, "Hoje", result.items.filter((item) => isToday(item.available_at)));
            renderGroup(list, "Anteriores", result.items.filter((item) => !isToday(item.available_at)));
            renderPagination(result);
        } catch (_error) {
            showState("Não foi possível abrir sua caixa de notificações.", true);
        }
    }

    async function inspectPushState() {
        const status = document.querySelector("[data-push-status]");
        const enable = el("notificationsEnablePush");
        const disable = el("notificationsDisablePush");
        const showActions = (active, canActivate = true) => {
            enable.hidden = active;
            enable.disabled = !canActivate;
            disable.hidden = !active;
        };
        if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
            status.textContent = "Este navegador não oferece notificações no dispositivo. A caixa interna continua ativa.";
            showActions(false, false);
            return;
        }
        const config = await window.AppApi.fetchJson("/notifications/push/config", { headers: headers() });
        if (!config.enabled) {
            status.textContent = "O canal no dispositivo ainda não foi habilitado pela escola.";
            showActions(false, false);
        } else if (Notification.permission === "denied") {
            status.textContent = "A permissão foi bloqueada. Libere notificações nas configurações deste site.";
            showActions(false, false);
        } else if (config.active) {
            status.textContent = "Este dispositivo está ativo para receber notificações.";
            showActions(true);
        } else {
            showActions(false);
        }
    }

    function init() {
        window.AppAuth.garantirToken();
        document.querySelectorAll("[data-filter]").forEach((button) => {
            button.addEventListener("click", () => {
                state.filter = button.dataset.filter;
                state.page = 1;
                document.querySelectorAll("[data-filter]").forEach((item) => {
                    item.classList.toggle("is-active", item === button);
                });
                load();
            });
        });
        el("notificationsReadAll").addEventListener("click", async () => {
            await window.AppApi.fetchJson("/notifications/read-all", { method: "POST", headers: headers() });
            await load();
        });
        el("notificationsEnablePush").addEventListener("click", () => window.AppNotifications.activatePush());
        el("notificationsDisablePush").addEventListener("click", () => window.AppNotifications.deactivatePush());
        document.addEventListener("notifications:push-status", (event) => {
            if (event.detail?.kind === "active") {
                el("notificationsEnablePush").hidden = true;
                el("notificationsDisablePush").hidden = false;
            } else if (event.detail?.kind === "inactive") {
                el("notificationsEnablePush").hidden = false;
                el("notificationsDisablePush").hidden = true;
            }
        });
        inspectPushState().catch(() => {});
        load();
    }

    window.addEventListener("DOMContentLoaded", init);
})(window, document);
