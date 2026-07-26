self.addEventListener("push", (event) => {
    let payload = {};
    try {
        payload = event.data?.json() || {};
    } catch (_error) {
        payload = {};
    }
    const id = Number(payload.id || 0);
    const action = new URL(payload.action_url || "/notificacoes", self.location.origin);
    if (id > 0) action.searchParams.set("notification_id", String(id));
    const options = {
        body: payload.body || "Você recebeu um novo aviso.",
        icon: "/static/img/notification-icon-192.png",
        badge: "/static/img/notification-icon-192.png",
        tag: payload.tag || `notification-${id || Date.now()}`,
        renotify: payload.priority === "urgent",
        data: { url: action.href, id },
    };
    event.waitUntil(Promise.all([
        self.registration.showNotification(payload.title || "Sistema EEPJD", options),
        self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
            clients.forEach((client) => client.postMessage({
                type: "notification-received",
                notificationId: id,
            }));
        }),
    ]));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const targetUrl = event.notification.data?.url || `${self.location.origin}/notificacoes`;
    event.waitUntil(
        self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (clients) => {
            const sameOrigin = clients.find((client) => new URL(client.url).origin === self.location.origin);
            if (sameOrigin) {
                await sameOrigin.navigate(targetUrl);
                return sameOrigin.focus();
            }
            return self.clients.openWindow(targetUrl);
        })
    );
});
