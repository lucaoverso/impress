(function (window, document) {
    const state = { transactions: [], editingId: null, cancelId: null };
    const byId = (id) => document.getElementById(id);
    const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

    function currentMonth() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    }

    function today() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    }

    function dateBr(value) {
        const [year, month, day] = String(value || "").split("-");
        return day ? `${day}/${month}/${year}` : String(value || "-");
    }

    function setMessage(text = "", error = false) {
        const target = byId("financeMessage");
        target.textContent = text;
        target.classList.toggle("is-error", error);
        if (text) target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function button(label, className, onClick, icon = "") {
        const element = document.createElement("button");
        element.type = "button";
        element.className = className;
        if (icon) {
            const iconElement = document.createElement("i");
            iconElement.className = `bi ${icon}`;
            iconElement.setAttribute("aria-hidden", "true");
            element.append(iconElement);
        }
        element.append(document.createTextNode(label));
        element.addEventListener("click", onClick);
        return element;
    }

    function renderSummary(summary) {
        byId("financeIncome").textContent = money.format(Number(summary.income_cents || 0) / 100);
        byId("financeExpense").textContent = money.format(Number(summary.expense_cents || 0) / 100);
        const balance = Number(summary.balance_cents || 0);
        const balanceTarget = byId("financeBalance");
        balanceTarget.textContent = money.format(balance / 100);
        balanceTarget.classList.toggle("is-negative", balance < 0);
        const active = Number(summary.active_count || 0);
        const canceled = Number(summary.canceled_count || 0);
        byId("financeSummaryMeta").textContent = active || canceled
            ? `${active} lançamento(s) ativo(s) e ${canceled} cancelado(s).`
            : "Nenhum lançamento neste mês.";
    }

    function attachmentList(transaction) {
        const list = document.createElement("div");
        list.className = "finance-attachments";
        (transaction.attachments || []).forEach((attachment) => {
            const item = document.createElement("span");
            item.append(button(
                attachment.original_name,
                "finance-attachment-link",
                () => run(() => window.FinanceApi.downloadAttachment(attachment)),
                "bi-paperclip"
            ));
            if (transaction.status === "ACTIVE") {
                const remove = button("Remover", "finance-attachment-remove", () => removeAttachment(transaction, attachment));
                remove.setAttribute("aria-label", `Remover comprovante ${attachment.original_name}`);
                item.append(remove);
            }
            list.append(item);
        });
        return list;
    }

    function cell(label, content, className = "") {
        const td = document.createElement("td");
        td.dataset.label = label;
        if (className) td.className = className;
        if (content instanceof Node) td.append(content);
        else td.textContent = content;
        return td;
    }

    function renderTransactions(transactions) {
        const tbody = byId("financeTransactions");
        tbody.replaceChildren();
        transactions.forEach((item) => {
            const row = document.createElement("tr");
            if (item.status === "CANCELED") row.className = "is-canceled";

            const description = document.createElement("div");
            description.className = "finance-description";
            const strong = document.createElement("strong");
            strong.textContent = item.description;
            description.append(strong);
            if (item.counterparty) {
                const counterparty = document.createElement("small");
                counterparty.textContent = item.counterparty;
                description.append(counterparty);
            }
            if ((item.attachments || []).length) description.append(attachmentList(item));
            if (item.status === "CANCELED") {
                const reason = document.createElement("small");
                reason.className = "finance-cancellation-reason";
                reason.textContent = `Cancelado: ${item.cancellation_reason}`;
                description.append(reason);
            }

            const badge = document.createElement("span");
            badge.className = `finance-type is-${item.transaction_type.toLowerCase()}`;
            badge.textContent = item.transaction_type === "INCOME" ? "Entrada" : "Gasto";

            const actions = document.createElement("div");
            actions.className = "finance-row-actions";
            if (item.status === "ACTIVE") {
                actions.append(
                    button("Editar", "button button--quiet", () => openForm(item), "bi-pencil"),
                    button("Cancelar", "button button--quiet is-danger", () => openCancel(item), "bi-x-circle")
                );
            } else {
                const canceled = document.createElement("span");
                canceled.className = "finance-status";
                canceled.textContent = "Cancelado";
                actions.append(canceled);
            }

            row.append(
                cell("Data", dateBr(item.occurred_on)),
                cell("Descrição", description),
                cell("Categoria", item.category),
                cell("Tipo", badge),
                cell("Valor", money.format(item.amount_cents / 100), "finance-value"),
                cell("Ações", actions, "finance-actions-cell")
            );
            tbody.append(row);
        });

        byId("financeLoading").hidden = true;
        byId("financeTableWrap").hidden = transactions.length === 0;
        byId("financeEmpty").hidden = transactions.length !== 0;
    }

    async function load() {
        byId("financeLoading").hidden = false;
        byId("financeTableWrap").hidden = true;
        byId("financeEmpty").hidden = true;
        const month = byId("financeMonth").value;
        const status = byId("financeStatusFilter").value;
        const [summary, transactions] = await Promise.all([
            window.FinanceApi.summary(month),
            window.FinanceApi.list(month, status)
        ]);
        state.transactions = transactions;
        renderSummary(summary);
        renderTransactions(transactions);
    }

    function resetForm() {
        state.editingId = null;
        byId("financeForm").reset();
        byId("financeType").value = "EXPENSE";
        byId("financeDate").value = today();
        byId("financeFormTitle").textContent = "Novo lançamento";
        byId("financeSaveButton").textContent = "Salvar lançamento";
    }

    function openForm(transaction = null) {
        resetForm();
        if (transaction) {
            state.editingId = transaction.id;
            byId("financeType").value = transaction.transaction_type;
            byId("financeDate").value = transaction.occurred_on;
            byId("financeDescription").value = transaction.description;
            byId("financeCategory").value = transaction.category;
            byId("financeAmount").value = (transaction.amount_cents / 100).toFixed(2);
            byId("financeCounterparty").value = transaction.counterparty || "";
            byId("financeNotes").value = transaction.notes || "";
            byId("financeFormTitle").textContent = "Editar lançamento";
            byId("financeSaveButton").textContent = "Salvar alterações";
        }
        byId("financeFormPanel").hidden = false;
        byId("financeDescription").focus();
        byId("financeFormPanel").scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function closeForm() {
        byId("financeFormPanel").hidden = true;
        resetForm();
        byId("financeNewButton").focus();
    }

    function payloadFromForm() {
        const amountCents = Math.round(Number(byId("financeAmount").value) * 100);
        if (!Number.isSafeInteger(amountCents) || amountCents <= 0) {
            throw new Error("Informe um valor maior que zero.");
        }
        return {
            transaction_type: byId("financeType").value,
            occurred_on: byId("financeDate").value,
            description: byId("financeDescription").value.trim(),
            category: byId("financeCategory").value.trim(),
            amount_cents: amountCents,
            counterparty: byId("financeCounterparty").value.trim(),
            notes: byId("financeNotes").value.trim()
        };
    }

    async function save(event) {
        event.preventDefault();
        const saveButton = byId("financeSaveButton");
        saveButton.disabled = true;
        try {
            const payload = payloadFromForm();
            const item = state.editingId
                ? await window.FinanceApi.update(state.editingId, payload)
                : await window.FinanceApi.create(payload);
            const file = byId("financeAttachment").files[0];
            let message = state.editingId ? "Lançamento atualizado." : "Lançamento registrado.";
            if (file) {
                try {
                    await window.FinanceApi.upload(item.id, file);
                    message += " Comprovante anexado.";
                } catch (error) {
                    message += ` O comprovante não foi anexado: ${error.message}`;
                }
            }
            byId("financeMonth").value = payload.occurred_on.slice(0, 7);
            closeForm();
            await load();
            setMessage(message);
        } finally {
            saveButton.disabled = false;
        }
    }

    function openCancel(transaction) {
        state.cancelId = transaction.id;
        byId("financeCancellationReason").value = "";
        byId("financeCancelDialog").showModal();
        byId("financeCancellationReason").focus();
    }

    async function confirmCancel(event) {
        event.preventDefault();
        if (event.submitter?.value !== "confirm") {
            byId("financeCancelDialog").close();
            return;
        }
        const reason = byId("financeCancellationReason").value.trim();
        if (!reason) return byId("financeCancellationReason").focus();
        await window.FinanceApi.cancel(state.cancelId, reason);
        byId("financeCancelDialog").close();
        await load();
        setMessage("Lançamento cancelado e mantido no histórico.");
    }

    async function removeAttachment(transaction, attachment) {
        if (!window.confirm(`Remover o comprovante “${attachment.original_name}”?`)) return;
        await window.FinanceApi.removeAttachment(transaction.id, attachment.id);
        await load();
        setMessage("Comprovante removido.");
    }

    async function run(action) {
        try {
            setMessage();
            await action();
        } catch (error) {
            setMessage(error.message || "Não foi possível concluir a operação.", true);
        }
    }

    async function init() {
        try {
            const user = await window.AppAuth.carregarUsuarioAtual({ forcar: true });
            if (window.AppAuth.normalizarCargoUsuario(user) !== "ADMIN") {
                window.location.replace("/servicos");
                return;
            }
            byId("financeMonth").value = currentMonth();
            resetForm();
            byId("financeNewButton").addEventListener("click", () => openForm());
            byId("financeEmptyAction").addEventListener("click", () => openForm());
            byId("financeCloseForm").addEventListener("click", closeForm);
            byId("financeCancelForm").addEventListener("click", closeForm);
            byId("financeForm").addEventListener("submit", (event) => run(() => save(event)));
            byId("financeCancelDialogForm").addEventListener("submit", (event) => run(() => confirmCancel(event)));
            byId("financeMonth").addEventListener("change", () => run(load));
            byId("financeStatusFilter").addEventListener("change", () => run(load));
            byId("financeReportButton").addEventListener("click", () => run(async () => {
                await window.FinanceApi.downloadReport(byId("financeMonth").value);
                setMessage("Prestação de contas gerada.");
            }));
            await load();
        } catch (error) {
            byId("financeLoading").hidden = true;
            setMessage(error.message || "Não foi possível abrir a gestão financeira.", true);
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})(window, document);
