(function (window, document) {
    const state = { open: false, initialized: false, config: null, registration: null };
    const el = (id) => document.getElementById(id);
    const headers = () => window.AppAuth?.criarHeadersAuth?.() || {};
    const jsonHeaders = () => window.AppAuth?.criarHeadersJsonAuth?.() || {};

    function parseUtc(value) {
        const date = new Date(`${String(value || "").replace(" ", "T")}Z`);
        return Number.isNaN(date.getTime()) ? new Date() : date;
    }

    function isToday(value) {
        const date = parseUtc(value);
        const now = new Date();
        return date.toDateString() === now.toDateString();
    }

    function formatTime(value) {
        const date = parseUtc(value);
        if (isToday(value)) {
            return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        }
        return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
    }

    function setBadge(count) {
        const badge = el("appNavbarNotificationsBadge");
        const toggle = el("appNavbarNotificationsToggle");
        if (!badge || !toggle) return;
        const total = Math.max(0, Number(count || 0));
        badge.textContent = total > 99 ? "99+" : String(total);
        badge.hidden = total === 0;
        badge.setAttribute("aria-label", `${total} notificações não lidas`);
        toggle.setAttribute("aria-label", total
            ? `Abrir notificações. ${total} não lidas`
            : "Abrir notificações");
        if ("setAppBadge" in navigator) {
            total ? navigator.setAppBadge(total).catch(() => {}) : navigator.clearAppBadge().catch(() => {});
        }
    }

    function showState(message, retry = false) {
        const box = el("appNavbarNotificationsState");
        const list = el("appNavbarNotificationsList");
        if (!box || !list) return;
        box.replaceChildren();
        const icon = document.createElement("i");
        icon.className = retry ? "bi bi-wifi-off" : "bi bi-bell";
        icon.setAttribute("aria-hidden", "true");
        const copy = document.createElement("p");
        copy.textContent = message;
        box.append(icon, copy);
        if (retry) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button";
            button.textContent = "Tentar novamente";
            button.addEventListener("click", loadInbox);
            box.appendChild(button);
        }
        box.hidden = false;
        list.replaceChildren();
    }

    function makeItem(item) {
        return window.AppNotificationsDrawer.makeItem(item, {
            formatTime,
            headers,
            setBadge,
            reload: loadInbox,
        });
    }

    function renderItems(items) {
        const box = el("appNavbarNotificationsState");
        const list = el("appNavbarNotificationsList");
        if (!box || !list) return;
        box.hidden = true;
        list.replaceChildren();
        if (!items.length) {
            showState("Você está em dia. Novos avisos aparecerão aqui.");
            return;
        }
        [["Hoje", items.filter((item) => isToday(item.available_at))],
         ["Anteriores", items.filter((item) => !isToday(item.available_at))]]
            .forEach(([label, group]) => {
                if (!group.length) return;
                const heading = document.createElement("h3");
                heading.className = "app-notifications-group-title";
                heading.textContent = label;
                list.appendChild(heading);
                group.forEach((item) => list.appendChild(makeItem(item)));
            });
    }

    async function loadCount() {
        if (!window.AppAuth?.obterToken?.()) return;
        try {
            const result = await window.AppApi.fetchJson("/notifications/unread-count", { headers: headers() });
            setBadge(result.unread_count);
        } catch (_error) {
            // A contagem volta a ser consultada no próximo foco/polling.
        }
    }

    async function loadInbox() {
        if (!navigator.onLine) {
            showState("Sem conexão. Seus avisos continuam salvos e aparecerão quando a conexão voltar.", true);
            return;
        }
        try {
            const result = await window.AppApi.fetchJson(
                "/notifications?filter=unread&page_size=8", { headers: headers() }
            );
            setBadge(result.unread_count);
            renderItems(result.items || []);
        } catch (_error) {
            showState("Não foi possível carregar as notificações agora.", true);
        }
    }

    function setOpen(open) {
        const panel = el("appNavbarNotificationsPanel");
        const toggle = el("appNavbarNotificationsToggle");
        if (!panel || !toggle) return;
        state.open = Boolean(open);
        panel.hidden = !state.open;
        toggle.setAttribute("aria-expanded", String(state.open));
        if (state.open) {
            el("appNavbarProfileMenu")?.setAttribute("hidden", "");
            el("appNavbarProfileToggle")?.setAttribute("aria-expanded", "false");
            loadInbox();
        }
    }

    function urlBase64ToUint8Array(value) {
        const padding = "=".repeat((4 - value.length % 4) % 4);
        const raw = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
        return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
    }

    function isIosNotInstalled() {
        const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
        return ios && !window.matchMedia("(display-mode: standalone)").matches
            && !window.navigator.standalone;
    }

    function emitPushStatus(kind, message) {
        document.querySelectorAll("[data-push-status]").forEach((node) => {
            node.dataset.state = kind;
            node.textContent = message;
        });
        document.dispatchEvent(new CustomEvent("notifications:push-status", {
            detail: { kind, message },
        }));
    }

    async function saveBrowserSubscription(subscription) {
        await window.AppApi.fetchJson("/notifications/push/subscriptions", {
            method: "PUT",
            headers: jsonHeaders(),
            body: JSON.stringify(subscription.toJSON()),
        });
    }

    async function activatePush() {
        if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
            emitPushStatus("unsupported", "Este navegador não oferece notificações no dispositivo. A caixa interna continua ativa.");
            return false;
        }
        if (isIosNotInstalled()) {
            emitPushStatus("install", "No iPhone ou iPad, adicione o sistema à Tela de Início e abra por lá para ativar notificações.");
            return false;
        }
        state.config = state.config || await window.AppApi.fetchJson("/notifications/push/config", { headers: headers() });
        if (!state.config.enabled) {
            emitPushStatus("unavailable", "As notificações no dispositivo ainda não foram habilitadas pela escola.");
            return false;
        }
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
            emitPushStatus("denied", "A permissão foi bloqueada. Você pode liberá-la nas configurações deste site.");
            return false;
        }
        state.registration = state.registration || await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
        let subscription = await state.registration.pushManager.getSubscription();
        if (!subscription) {
            subscription = await state.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(state.config.public_key),
            });
        }
        await saveBrowserSubscription(subscription);
        emitPushStatus("active", "Este dispositivo receberá notificações mesmo com a aba fechada.");
        return true;
    }

    async function deactivatePush() {
        if (!("serviceWorker" in navigator)) return false;
        const registration = await navigator.serviceWorker.getRegistration("/");
        const subscription = await registration?.pushManager?.getSubscription();
        if (subscription) {
            await window.AppApi.fetchJson("/notifications/push/subscriptions", {
                method: "DELETE", headers: jsonHeaders(),
                body: JSON.stringify({ endpoint: subscription.endpoint }),
            }).catch(() => null);
            await subscription.unsubscribe().catch(() => false);
        }
        emitPushStatus("inactive", "As notificações deste dispositivo estão desativadas.");
        return true;
    }

    async function reconcileSubscription() {
        if (!("serviceWorker" in navigator) || !window.AppAuth?.obterToken?.()) return;
        state.registration = await navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
        const subscription = await state.registration.pushManager?.getSubscription();
        if (subscription) await saveBrowserSubscription(subscription).catch(() => null);
    }

    async function markFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const id = Number(params.get("notification_id") || 0);
        if (id > 0) {
            await window.AppApi.fetchJson(`/notifications/${id}/read`, {
                method: "POST", headers: headers(),
            }).catch(() => null);
        }
    }

    function bindEvents() {
        el("appNavbarNotificationsToggle")?.addEventListener("click", () => setOpen(!state.open));
        el("appNavbarNotificationsReadAll")?.addEventListener("click", async () => {
            await window.AppApi.fetchJson("/notifications/read-all", { method: "POST", headers: headers() });
            await loadInbox();
        });
        document.addEventListener("click", (event) => {
            if (state.open && !event.target.closest(".app-navbar-notifications-panel")
                && !event.target.closest("#appNavbarNotificationsToggle")) setOpen(false);
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && state.open) {
                setOpen(false);
                el("appNavbarNotificationsToggle")?.focus();
            }
        });
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) loadCount();
        });
        window.addEventListener("focus", loadCount);
        window.addEventListener("online", loadCount);
        navigator.serviceWorker?.addEventListener("message", (event) => {
            if (event.data?.type === "notification-received") {
                loadCount();
                if (state.open) loadInbox();
            }
        });
    }

    function init() {
        if (state.initialized || !el("appNavbarNotificationsToggle")) return;
        state.initialized = true;
        bindEvents();
        window.AppAuth?.carregarUsuarioAtual?.().then((user) => {
            el("appNavbarNotificationsManage").hidden = !user?.eh_gestor;
        }).catch(() => {});
        markFromUrl();
        reconcileSubscription();
        loadCount();
        window.setInterval(() => { if (!document.hidden) loadCount(); }, 60000);
    }

    window.AppNotifications = Object.assign(window.AppNotifications || {}, {
        init, activatePush, deactivatePush, beforeLogout: deactivatePush,
        refresh: loadCount,
    });
    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})(window, document);
