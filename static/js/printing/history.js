(function (window, document) {
    const STATUS_LABELS = {
        PENDENTE: "Na fila",
        IMPRIMINDO: "Imprimindo",
        CONCLUIDO: "Concluído",
        FINALIZADO: "Concluído",
        CANCELADO: "Cancelado",
        ERRO: "Erro",
    };
    const POLL_INTERVAL_MS = 6000;
    let pollTimer = null;
    let hasLoaded = false;

    const el = (id) => document.getElementById(id);
    const authHeaders = () => window.AppAuth.criarHeadersAuth();

    function showFeedback(message, isError = false) {
        const feedback = el("printHistoryFeedback");
        if (!feedback) return;
        feedback.textContent = message;
        feedback.classList.toggle("is-error", isError);
        feedback.hidden = !message;
    }

    function normalizedStatus(job) {
        return String(job?.status || "").trim().toUpperCase();
    }

    function formatDate(value) {
        if (!value) return "Data não informada";
        const normalized = String(value).replace(" ", "T");
        const date = new Date(/(?:Z|[+-]\d\d:?\d\d)$/.test(normalized) ? normalized : `${normalized}Z`);
        if (Number.isNaN(date.getTime())) return String(value);
        return new Intl.DateTimeFormat("pt-BR", {
            dateStyle: "short",
            timeStyle: "short",
        }).format(date);
    }

    function appendText(parent, tag, className, text) {
        const node = document.createElement(tag);
        node.className = className;
        node.textContent = text;
        parent.appendChild(node);
        return node;
    }

    async function cancelJob(jobId, button) {
        if (!window.confirm("Cancelar este pedido? A cota será estornada se ele ainda estiver pendente.")) return;
        button.disabled = true;
        button.textContent = "Cancelando...";
        try {
            const data = await window.AppApi.fetchJson(`/jobs/${jobId}/cancelar`, {
                method: "POST",
                headers: authHeaders(),
            });
            const refunded = Number(data?.paginas_estornadas || 0);
            showFeedback(refunded > 0
                ? `Pedido cancelado. ${refunded} página(s) foram devolvidas à sua cota.`
                : "Pedido cancelado com sucesso.");
            await loadPage();
        } catch (error) {
            showFeedback(error.message || "Não foi possível cancelar o pedido.", true);
            button.disabled = false;
            button.textContent = "Cancelar";
        }
    }

    function createJobItem(job) {
        const item = document.createElement("li");
        item.className = "print-history-item";

        const main = document.createElement("div");
        main.className = "print-history-item-main";
        const title = document.createElement("div");
        title.className = "print-history-item-title";
        appendText(title, "strong", "", String(job?.arquivo || "Arquivo sem nome"));
        const status = appendText(title, "span", "print-history-status", STATUS_LABELS[normalizedStatus(job)] || "Desconhecido");
        status.dataset.status = normalizedStatus(job);
        main.appendChild(title);

        const copies = Number(job?.copias || 1);
        const pages = Number(job?.paginas_totais || 0);
        appendText(main, "p", "print-history-item-meta", `Pedido #${job?.id || "-"} · ${copies} cópia(s) · ${pages} página(s) · ${formatDate(job?.criado_em)}`);
        if (Array.isArray(job?.tags) && job.tags.length) {
            appendText(main, "p", "print-history-item-note", `Tipo de material: ${job.tags.join(", ")}`);
        }
        if (job?.erro_mensagem) {
            appendText(main, "p", "print-history-item-note is-error", String(job.erro_mensagem));
        } else if (job?.motivo_reuso_indisponivel && ["CONCLUIDO", "FINALIZADO"].includes(normalizedStatus(job))) {
            appendText(main, "p", "print-history-item-note", String(job.motivo_reuso_indisponivel));
        }
        item.appendChild(main);

        const actions = document.createElement("div");
        actions.className = "print-history-item-actions";
        if (job?.pode_reutilizar) {
            const reuse = document.createElement("a");
            reuse.href = `/impressao?reutilizar=${encodeURIComponent(job.id)}`;
            reuse.textContent = "Usar novamente";
            actions.appendChild(reuse);
        }
        if (normalizedStatus(job) === "PENDENTE") {
            const cancel = document.createElement("button");
            cancel.type = "button";
            cancel.className = "print-history-cancel";
            cancel.textContent = "Cancelar";
            cancel.addEventListener("click", () => cancelJob(job.id, cancel));
            actions.appendChild(cancel);
        }
        if (actions.childElementCount) item.appendChild(actions);
        return item;
    }

    function renderJobs(jobs) {
        const list = el("printHistoryList");
        list.replaceChildren();
        list.setAttribute("aria-busy", "false");
        if (!jobs.length) {
            appendText(list, "li", "print-history-empty", "Você ainda não enviou nenhuma impressão.");
            return;
        }
        jobs.forEach((job) => list.appendChild(createJobItem(job)));
    }

    function renderLoadError() {
        const list = el("printHistoryList");
        const empty = document.createElement("li");
        empty.className = "print-history-empty";
        const copy = document.createElement("p");
        copy.textContent = "Não foi possível carregar seu histórico.";
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "print-secondary-btn";
        retry.textContent = "Tentar novamente";
        retry.addEventListener("click", () => refresh({ announce: true }));
        empty.append(copy, retry);
        list.replaceChildren(empty);
        list.setAttribute("aria-busy", "false");
    }

    async function loadPage() {
        const [quota, jobs] = await Promise.all([
            window.AppApi.fetchJson("/minha-cota", { headers: authHeaders() }),
            window.AppApi.fetchJson("/meus-jobs", { headers: authHeaders() }),
        ]);
        el("printHistoryQuota").textContent = quota.ilimitada
            ? "Cota ilimitada"
            : `${quota.restante} de ${quota.limite} páginas disponíveis`;
        renderJobs(Array.isArray(jobs) ? jobs : []);
        hasLoaded = true;
    }

    async function refresh({ announce = false } = {}) {
        const button = el("printHistoryRefresh");
        if (button) button.disabled = true;
        el("printHistoryList")?.setAttribute("aria-busy", "true");
        try {
            await loadPage();
            if (announce) showFeedback("Histórico atualizado.");
        } catch (error) {
            el("printHistoryList")?.setAttribute("aria-busy", "false");
            if (!hasLoaded) renderLoadError();
            showFeedback(error.message || "Não foi possível carregar seu histórico.", true);
        } finally {
            if (button) button.disabled = false;
        }
    }

    function init() {
        window.AppAuth.garantirToken();
        el("printHistoryRefresh")?.addEventListener("click", () => refresh({ announce: true }));
        refresh();
        pollTimer = window.setInterval(refresh, POLL_INTERVAL_MS);
    }

    window.addEventListener("beforeunload", () => window.clearInterval(pollTimer));
    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})(window, document);
