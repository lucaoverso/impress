(function (window, document) {
    const selected = new Map();
    let estimateTimer = null;
    let searchTimer = null;
    const el = (id) => document.getElementById(id);
    const headers = () => window.AppAuth.criarHeadersAuth();
    const jsonHeaders = () => window.AppAuth.criarHeadersJsonAuth();

    function audienceValues() {
        return [...document.querySelectorAll(".notifications-audiences input:checked")]
            .map((input) => input.value);
    }

    function audiencePayload() {
        return { audiences: audienceValues(), user_ids: [...selected.keys()] };
    }

    function feedback(message, error = false) {
        const node = el("notificationComposerFeedback");
        node.textContent = message;
        node.hidden = !message;
        node.style.background = error ? "var(--state-danger-bg)" : "var(--brand-soft)";
        node.style.color = error ? "var(--state-danger-text)" : "var(--brand-strong)";
    }

    function renderSelected() {
        const wrap = el("notificationSelectedRecipients");
        wrap.replaceChildren();
        selected.forEach((user, id) => {
            const chip = document.createElement("span");
            chip.textContent = user.nome;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.setAttribute("aria-label", `Remover ${user.nome}`);
            remove.textContent = "×";
            remove.addEventListener("click", () => {
                selected.delete(id);
                renderSelected();
                scheduleEstimate();
            });
            chip.appendChild(remove);
            wrap.appendChild(chip);
        });
    }

    async function estimate() {
        try {
            const result = await window.AppApi.fetchJson("/notifications/manage/estimate", {
                method: "POST", headers: jsonHeaders(), body: JSON.stringify(audiencePayload()),
            });
            el("notificationEstimate").textContent =
                `${result.count} ${result.count === 1 ? "destinatário" : "destinatários"}`;
            return result.count;
        } catch (_error) {
            el("notificationEstimate").textContent = "Estimativa indisponível";
            return 0;
        }
    }

    function scheduleEstimate() {
        window.clearTimeout(estimateTimer);
        estimateTimer = window.setTimeout(estimate, 180);
    }

    async function searchRecipients() {
        const term = el("notificationRecipientSearch").value.trim();
        const wrap = el("notificationRecipientResults");
        wrap.replaceChildren();
        if (term.length < 2) return;
        const result = await window.AppApi.fetchJson(
            `/notifications/manage/recipients?search=${encodeURIComponent(term)}`,
            { headers: headers() }
        );
        (result.items || []).forEach((user) => {
            if (selected.has(user.id)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = `${user.nome} · ${user.email}`;
            button.addEventListener("click", () => {
                selected.set(user.id, user);
                renderSelected();
                button.remove();
                scheduleEstimate();
            });
            wrap.appendChild(button);
        });
    }

    function payload() {
        return {
            ...audiencePayload(),
            title: el("notificationTitle").value.trim(),
            body: el("notificationBody").value.trim(),
            action_url: el("notificationUrl").value.trim() || "/",
            priority: el("notificationPriority").value,
            scheduled_at: el("notificationSchedule").value || null,
        };
    }

    function confirmSend(count) {
        const dialog = el("notificationConfirmDialog");
        const scheduled = el("notificationSchedule").value;
        el("notificationConfirmTitle").textContent = scheduled
            ? "Agendar esta notificação?"
            : "Enviar esta notificação agora?";
        el("notificationConfirmCopy").textContent =
            `${count} ${count === 1 ? "pessoa receberá" : "pessoas receberão"} o aviso. `
            + "Depois do disparo, o lote não poderá ser editado.";
        dialog.showModal();
        return new Promise((resolve) => {
            dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
        });
    }

    async function submit(event) {
        event.preventDefault();
        feedback("");
        const count = await estimate();
        if (!count) {
            feedback("Selecione ao menos um público ou usuário ativo.", true);
            return;
        }
        if (!await confirmSend(count)) return;
        const button = event.submitter || document.querySelector(".notifications-send");
        button.disabled = true;
        try {
            const result = await window.AppApi.fetchJson("/notifications/manage/batches", {
                method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload()),
            });
            feedback(`Lote criado para ${result.recipients} destinatários.`);
            event.target.reset();
            el("notificationTitleCount").textContent = "0";
            el("notificationBodyCount").textContent = "0";
            selected.clear();
            renderSelected();
            scheduleEstimate();
            await loadHistory();
        } catch (error) {
            feedback(error.message || "Não foi possível criar o lote.", true);
        } finally {
            button.disabled = false;
        }
    }

    function formatUtc(value) {
        return new Date(`${String(value || "").replace(" ", "T")}Z`).toLocaleString("pt-BR", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    }

    async function cancelBatch(batchId) {
        try {
            await window.AppApi.fetchJson(`/notifications/manage/batches/${batchId}/cancel`, {
                method: "POST", headers: headers(),
            });
            feedback("Agendamento cancelado. Ele não será disparado.");
            loadHistory();
        } catch (error) {
            feedback(error.message || "Não foi possível cancelar o agendamento.", true);
        }
    }

    async function loadHistory() {
        const result = await window.AppApi.fetchJson("/notifications/manage/batches", { headers: headers() });
        const wrap = el("notificationsBatchHistory");
        wrap.replaceChildren();
        if (!(result.items || []).length) {
            const empty = document.createElement("div");
            empty.className = "notifications-page-state";
            empty.textContent = "Nenhum envio manual ainda.";
            wrap.appendChild(empty);
            return;
        }
        result.items.forEach((batch) => {
            const item = document.createElement("article");
            item.className = "notifications-batch";
            const title = document.createElement("strong");
            title.textContent = batch.title;
            const meta = document.createElement("span");
            const status = {
                scheduled: "Agendado",
                sent: "Disparado",
                cancelled: "Cancelado",
            }[batch.status] || "Criado";
            meta.textContent = `${status} · ${batch.recipients} destinatários · ${formatUtc(batch.scheduled_at)}`;
            item.append(title, meta);
            if (batch.push_sent || batch.push_failed) {
                const delivery = document.createElement("span");
                delivery.textContent =
                    `Push: ${batch.push_sent || 0} enviados · ${batch.push_failed || 0} falhas`;
                item.appendChild(delivery);
            }
            const scheduled = parseUtc(batch.scheduled_at) > new Date() && !batch.cancelled;
            if (scheduled) {
                const cancel = document.createElement("button");
                cancel.type = "button";
                cancel.textContent = "Cancelar agendamento";
                cancel.addEventListener("click", () => cancelBatch(batch.batch_id));
                item.appendChild(cancel);
            }
            wrap.appendChild(item);
        });
    }

    function parseUtc(value) {
        return new Date(`${String(value || "").replace(" ", "T")}Z`);
    }

    async function init() {
        window.AppAuth.garantirToken();
        const user = await window.AppAuth.carregarUsuarioAtual();
        if (!user?.eh_gestor) {
            el("notificationsManageDenied").hidden = false;
            return;
        }
        el("notificationsManageContent").hidden = false;
        ["notificationTitle", "notificationBody"].forEach((id) => {
            el(id).addEventListener("input", () => {
                el(`${id}Count`).textContent = el(id).value.length;
            });
        });
        document.querySelectorAll(".notifications-audiences input")
            .forEach((input) => input.addEventListener("change", scheduleEstimate));
        el("notificationRecipientSearch").addEventListener("input", () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(() => searchRecipients().catch(() => {}), 250);
        });
        el("notificationsComposer").addEventListener("submit", submit);
        scheduleEstimate();
        loadHistory().catch(() => feedback("O histórico não pôde ser carregado.", true));
    }

    window.addEventListener("DOMContentLoaded", () => init().catch(() => {
        el("notificationsManageDenied").hidden = false;
    }));
})(window, document);
