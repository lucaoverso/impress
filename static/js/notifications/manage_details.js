(function (window, document) {
    const el = (id) => document.getElementById(id);
    const headers = () => window.AppAuth.criarHeadersAuth();
    let activeBatch = null;

    function formatUtc(value) {
        if (!value) return "Não lido";
        return `Lido em ${new Date(`${String(value).replace(" ", "T")}Z`).toLocaleString("pt-BR", {
            day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
        })}`;
    }

    function roleName(value) {
        return {
            ADMIN: "Administração",
            COORDENADOR: "Coordenação",
            PROFESSOR: "Professor(a)",
        }[String(value || "").toUpperCase()] || "Usuário(a)";
    }

    function statusCell(text, active) {
        const cell = document.createElement("td");
        cell.dataset.label = "Push";
        const status = document.createElement("span");
        status.className = `notifications-recipient-push ${active ? "is-active" : "is-inactive"}`;
        const dot = document.createElement("span");
        dot.setAttribute("aria-hidden", "true");
        status.append(dot, text);
        cell.appendChild(status);
        return cell;
    }

    function render(result) {
        const body = el("notificationBatchRecipientsBody");
        body.replaceChildren();
        result.items.forEach((item) => {
            const row = document.createElement("tr");
            const person = document.createElement("td");
            person.dataset.label = "Pessoa";
            const name = document.createElement("strong");
            name.textContent = item.nome;
            const meta = document.createElement("span");
            meta.textContent = `${roleName(item.cargo)} · ${item.email}`;
            person.append(name, meta);
            const read = document.createElement("td");
            read.dataset.label = "Leitura";
            read.textContent = formatUtc(item.read_at);
            if (item.read_at) read.className = "is-read";
            const devices = document.createElement("td");
            devices.dataset.label = "Dispositivos";
            devices.textContent = String(item.active_devices);
            row.append(
                person,
                read,
                statusCell(item.push_active ? "Ativo" : "Inativo", item.push_active),
                devices
            );
            body.appendChild(row);
        });
        el("notificationBatchRecipientsTitle").textContent = result.title;
        el("notificationBatchRecipientsSummary").textContent =
            `${result.read_count} de ${result.total} leram · `
            + `${result.push_active_count} com notificações em dispositivo`;
        el("notificationBatchRecipientsState").hidden = true;
        el("notificationBatchRecipientsTableWrap").hidden = false;
    }

    function showError(message) {
        const state = el("notificationBatchRecipientsState");
        state.replaceChildren();
        const copy = document.createElement("p");
        copy.textContent = message;
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "button";
        retry.textContent = "Tentar novamente";
        retry.addEventListener("click", () => open(activeBatch));
        state.append(copy, retry);
        state.hidden = false;
        el("notificationBatchRecipientsTableWrap").hidden = true;
    }

    async function open(batch) {
        activeBatch = batch;
        const section = el("notificationBatchRecipients");
        section.hidden = false;
        el("notificationBatchRecipientsTitle").textContent = batch.title;
        el("notificationBatchRecipientsSummary").textContent = "Consultando leitura e dispositivos...";
        el("notificationBatchRecipientsState").hidden = false;
        el("notificationBatchRecipientsState").textContent = "Carregando destinatários...";
        el("notificationBatchRecipientsTableWrap").hidden = true;
        const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "auto" : "smooth";
        section.scrollIntoView({ behavior, block: "start" });
        try {
            const result = await window.AppApi.fetchJson(
                `/notifications/manage/batches/${batch.batch_id}/recipients`,
                { headers: headers() }
            );
            render(result);
        } catch (error) {
            showError(error.message || "Não foi possível consultar os destinatários.");
        }
    }

    function close() {
        el("notificationBatchRecipients").hidden = true;
        activeBatch = null;
    }

    function init() {
        el("notificationBatchRecipientsClose")?.addEventListener("click", close);
    }

    window.NotificationsManageDetails = { init, open };
})(window, document);
