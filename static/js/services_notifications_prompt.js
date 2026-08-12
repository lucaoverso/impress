(function (window, document) {
    const SNOOZE_DAYS = 7;
    const INSTALL_ACK_HOURS = 24;
    const MODE_PUSH = "push";
    const MODE_IOS_INSTALL = "ios-install";
    const MODE_IOS_BROWSER = "ios-browser";
    let initialized = false;
    let currentUserId = 0;
    let currentMode = MODE_PUSH;
    const el = (id) => document.getElementById(id);
    const headers = () => window.AppAuth?.criarHeadersAuth?.() || {};

    function storageKey(mode = currentMode) {
        if (mode === MODE_PUSH) {
            return `services-notifications-prompt-snooze:${currentUserId}`;
        }
        return `services-install-prompt-snooze:${currentUserId}`;
    }

    function isSnoozed(mode) {
        try {
            const until = Number(window.localStorage.getItem(storageKey(mode)) || 0);
            return Number.isFinite(until) && until > Date.now();
        } catch (_error) {
            return false;
        }
    }

    function snooze(mode, hours = SNOOZE_DAYS * 24) {
        const until = Date.now() + hours * 60 * 60 * 1000;
        try {
            window.localStorage.setItem(storageKey(mode), String(until));
        } catch (_error) {
            // O fechamento continua válido mesmo sem armazenamento local disponível.
        }
    }

    function isIosDevice() {
        const mobileIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
        const ipadDesktopMode = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
        return mobileIos || ipadDesktopMode;
    }

    function isInstalled() {
        return window.matchMedia("(display-mode: standalone)").matches
            || window.navigator.standalone === true;
    }

    function isSafari() {
        const userAgent = navigator.userAgent;
        return /safari/i.test(userAgent) && !/(crios|fxios|edgios|opios)/i.test(userAgent);
    }

    function installMode() {
        if (!isIosDevice() || isInstalled() || isSnoozed(MODE_IOS_INSTALL)) return null;
        return isSafari() ? MODE_IOS_INSTALL : MODE_IOS_BROWSER;
    }

    async function loadPushConfig() {
        return window.AppApi.fetchJson(
            "/notifications/push/config", { headers: headers() }
        );
    }

    async function shouldOpenPush(config) {
        if (isSnoozed(MODE_PUSH)) return false;
        if (!("Notification" in window) || !("serviceWorker" in navigator)
            || !("PushManager" in window) || Notification.permission === "denied") return false;
        if (!config.enabled) return false;
        const registration = await navigator.serviceWorker.getRegistration("/");
        const subscription = await registration?.pushManager?.getSubscription();
        return !subscription;
    }

    function setInstallSteps(browserMode) {
        el("servicesNotificationsInstallStepOne").textContent = browserMode
            ? "Abra este endereço no Safari."
            : "No Safari, toque no botão Compartilhar.";
        el("servicesNotificationsInstallStepTwo").textContent = browserMode
            ? "No Safari, toque em Compartilhar e escolha “Adicionar à Tela de Início”."
            : "Escolha “Adicionar à Tela de Início”.";
        el("servicesNotificationsInstallStepThree").textContent =
            "Se aparecer, ative “Abrir como App da Web” e toque em “Adicionar”.";
    }

    function renderMode(mode) {
        currentMode = mode;
        const installing = mode !== MODE_PUSH;
        const browserMode = mode === MODE_IOS_BROWSER;
        el("servicesNotificationsPromptIcon").className = `bi ${installing ? "bi-phone" : "bi-bell-fill"}`;
        el("servicesNotificationsInstallSteps").hidden = !installing;
        el("servicesNotificationsPromptEnable").textContent = installing ? "Entendi" : "Ativar notificações";
        el("servicesNotificationsPromptTitle").textContent = browserMode
            ? "Abra o sistema no Safari"
            : installing ? "Adicione o sistema à Tela de Início" : "Não perca prazos importantes";
        el("servicesNotificationsPromptCopy").textContent = installing
            ? "No iPhone, a instalação é necessária para receber notificações mesmo com o navegador fechado."
            : "Ative as notificações para receber avisos sobre prazos de anexos, comunicados e outras atualizações importantes, mesmo com o sistema fechado.";
        el("servicesNotificationsPromptNote").textContent = installing
            ? "Depois, abra o sistema pelo novo ícone para ativar as notificações."
            : "Você pode alterar isso a qualquer momento na Central de Notificações.";
        if (installing) setInstallSteps(browserMode);
    }

    function close({ rememberHours = 0 } = {}) {
        const dialog = el("servicesNotificationsPrompt");
        if (rememberHours) snooze(currentMode, rememberHours);
        if (dialog?.open) dialog.close();
    }

    function primaryAction() {
        if (currentMode === MODE_PUSH) return enablePush();
        close({ rememberHours: INSTALL_ACK_HOURS });
    }

    async function enablePush() {
        const button = el("servicesNotificationsPromptEnable");
        button.disabled = true;
        button.textContent = "Ativando...";
        try {
            const active = await window.AppNotifications.activatePush();
            if (active) {
                try { window.localStorage.removeItem(storageKey(MODE_PUSH)); } catch (_error) {}
                close();
                return;
            }
        } catch (_error) {
            const status = el("servicesNotificationsPromptCopy");
            status.textContent = "Não foi possível ativar agora. Tente novamente ou use a Central de Notificações.";
            status.dataset.state = "error";
        }
        const denied = "Notification" in window && Notification.permission === "denied";
        button.disabled = denied;
        button.textContent = denied ? "Permissão bloqueada" : "Tentar novamente";
    }

    async function init(user) {
        if (initialized) return;
        initialized = true;
        currentUserId = Number(user?.id || 0);
        const dialog = el("servicesNotificationsPrompt");
        if (!currentUserId || !dialog) return;
        el("servicesNotificationsPromptEnable").addEventListener("click", primaryAction);
        el("servicesNotificationsPromptLater").addEventListener("click", () => {
            close({ rememberHours: SNOOZE_DAYS * 24 });
        });
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            close({ rememberHours: SNOOZE_DAYS * 24 });
        });
        document.addEventListener("notifications:push-status", (event) => {
            if (event.detail?.kind === "active") close();
        });
        try {
            const config = await loadPushConfig();
            const iosMode = config.enabled ? installMode() : null;
            const mode = iosMode || (await shouldOpenPush(config) ? MODE_PUSH : null);
            if (mode) {
                renderMode(mode);
                dialog.showModal();
            }
        } catch (_error) {
            // A caixa interna continua funcionando quando o canal externo está indisponível.
        }
    }

    window.ServicesNotificationsPrompt = { init };
})(window, document);
