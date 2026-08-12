(function (window, document) {
    function makeItem(item, options) {
        const row = document.createElement("article");
        row.className = "app-notification-item app-notification-item--dismissible";
        if (!item.read_at) row.classList.add("is-unread");
        if (item.priority === "urgent") row.classList.add("is-urgent");
        const open = document.createElement("button");
        open.type = "button";
        open.className = "app-notification-open";
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
        time.textContent = options.formatTime(item.available_at);
        copy.append(title, body, time);
        open.append(dot, copy);
        open.addEventListener("click", async () => {
            await window.AppApi.fetchJson(`/notifications/${item.id}/read`, {
                method: "POST", headers: options.headers(),
            }).catch(() => null);
            window.location.href = item.action_url || "/notificacoes";
        });
        const complete = document.createElement("button");
        complete.type = "button";
        complete.className = "app-notification-complete";
        complete.title = "Marcar como lida";
        complete.setAttribute("aria-label", `Marcar "${item.title}" como lida`);
        const check = document.createElement("i");
        check.className = "bi bi-check2";
        check.setAttribute("aria-hidden", "true");
        complete.appendChild(check);
        complete.addEventListener("click", async () => {
            complete.disabled = true;
            try {
                const result = await window.AppApi.fetchJson(`/notifications/${item.id}/read`, {
                    method: "POST", headers: options.headers(),
                });
                options.setBadge(result.unread_count);
                row.classList.add("is-completing");
                const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
                await new Promise((resolve) => window.setTimeout(resolve, reduced ? 0 : 160));
                await options.reload();
            } catch (_error) {
                complete.disabled = false;
                complete.classList.add("has-error");
                complete.title = "Não foi possível marcar como lida";
            }
        });
        row.append(open, complete);
        return row;
    }

    window.AppNotificationsDrawer = { makeItem };
})(window, document);
