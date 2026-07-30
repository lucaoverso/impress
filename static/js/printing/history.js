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
    let currentUser = null;
    let professors = [];
    let loadSequence = 0;

    const el = (id) => document.getElementById(id);
    const authHeaders = () => window.AppAuth.criarHeadersAuth();

    function canSelectProfessor(user) {
        const cargo = String(user?.cargo || "").trim().toUpperCase();
        const perfil = String(user?.perfil || "").trim().toLowerCase();
        return Boolean(
            user?.eh_admin
            || cargo === "ADMIN"
            || cargo === "COORDENADOR"
            || perfil === "admin"
            || perfil === "coordenador"
        );
    }

    function selectedProfessorId() {
        return Number(el("printHistoryProfessor")?.value || 0);
    }

    function selectedProfessor() {
        const professorId = selectedProfessorId();
        return professors.find((professor) => Number(professor.id) === professorId) || null;
    }

    function buildDelegatedUrl(base, { includeOwn = false } = {}) {
        const professorId = selectedProfessorId();
        if (professorId <= 0) return base;
        const params = new URLSearchParams({ professor_id: String(professorId) });
        if (includeOwn) params.set("incluir_proprios", "true");
        return `${base}?${params.toString()}`;
    }

    function showFeedback(message, isError = false) {
        const feedback = el("printHistoryFeedback");
        if (!feedback) return;
        feedback.textContent = message;
        feedback.dataset.variant = isError ? "error" : "info";
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
            await refresh();
        } catch (error) {
            showFeedback(error.message || "Não foi possível cancelar o pedido.", true);
            button.disabled = false;
            button.textContent = "Cancelar";
        }
    }

    function createJobItem(job) {
        const item = document.createElement("li");
        item.className = "print-history-item list-item";

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
        appendText(main, "p", "print-history-item-meta item-meta", `Pedido #${job?.id || "-"} · ${copies} cópia(s) · ${pages} página(s) · ${formatDate(job?.criado_em)}`);
        if (job?.origem_historico) {
            const origin = job.origem_historico === "proprio"
                ? "Seu histórico"
                : `Histórico de ${job?.origem_nome || selectedProfessor()?.nome || "professor"}`;
            appendText(main, "p", "print-history-item-origin", origin);
        }
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
        actions.className = "print-history-item-actions action-group action-group--compact";
        if (job?.pode_reutilizar) {
            const reuse = document.createElement("a");
            const params = new URLSearchParams({ reutilizar: String(job.id) });
            const professorId = selectedProfessorId();
            if (professorId > 0) params.set("professor_id", String(professorId));
            reuse.href = `/impressao?${params.toString()}`;
            reuse.className = "button button--primary";
            reuse.textContent = "Usar novamente";
            actions.appendChild(reuse);
        }
        if (normalizedStatus(job) === "PENDENTE") {
            const cancel = document.createElement("button");
            cancel.type = "button";
            cancel.className = "print-history-cancel button button--danger";
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
            const professor = selectedProfessor();
            appendText(
                list,
                "li",
                "print-history-empty empty-state",
                professor
                    ? `Você e ${professor.nome} ainda não possuem impressões neste histórico.`
                    : "Você ainda não enviou nenhuma impressão.",
            );
            return;
        }
        jobs.forEach((job) => list.appendChild(createJobItem(job)));
    }

    function renderLoadError() {
        const list = el("printHistoryList");
        const empty = document.createElement("li");
        empty.className = "print-history-empty empty-state";
        const copy = document.createElement("p");
        copy.textContent = "Não foi possível carregar seu histórico.";
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "print-secondary-btn button";
        retry.textContent = "Tentar novamente";
        retry.addEventListener("click", () => refresh({ announce: true }));
        empty.append(copy, retry);
        list.replaceChildren(empty);
        list.setAttribute("aria-busy", "false");
    }

    async function loadPage(sequence) {
        const [quota, jobs] = await Promise.all([
            window.AppApi.fetchJson(buildDelegatedUrl("/minha-cota"), { headers: authHeaders() }),
            window.AppApi.fetchJson(
                buildDelegatedUrl("/meus-jobs", { includeOwn: true }),
                { headers: authHeaders() },
            ),
        ]);
        if (sequence !== loadSequence) return false;
        el("printHistoryQuota").textContent = quota.ilimitada
            ? "Uso ilimitado"
            : `${quota.usadas} de ${quota.limite} páginas usadas`;
        renderJobs(Array.isArray(jobs) ? jobs : []);
        hasLoaded = true;
        return true;
    }

    async function refresh({ announce = false } = {}) {
        const sequence = ++loadSequence;
        const button = el("printHistoryRefresh");
        if (button) button.disabled = true;
        el("printHistoryList")?.setAttribute("aria-busy", "true");
        try {
            const rendered = await loadPage(sequence);
            if (rendered && announce) showFeedback("Histórico atualizado.");
        } catch (error) {
            if (sequence !== loadSequence) return;
            el("printHistoryList")?.setAttribute("aria-busy", "false");
            if (!hasLoaded) renderLoadError();
            showFeedback(error.message || "Não foi possível carregar seu histórico.", true);
        } finally {
            if (sequence === loadSequence && button) button.disabled = false;
        }
    }

    async function loadProfessorContext() {
        currentUser = await window.AppApi.fetchJson("/me", { headers: authHeaders() });
        if (!canSelectProfessor(currentUser)) return;

        professors = await window.AppApi.fetchJson("/agendamento/professores", {
            headers: authHeaders(),
        });
        if (!Array.isArray(professors)) professors = [];

        const owner = el("printHistoryOwner");
        const select = el("printHistoryProfessor");
        professors.forEach((professor) => {
            const option = document.createElement("option");
            option.value = String(professor.id);
            option.textContent = professor.nome;
            select.appendChild(option);
        });
        owner.hidden = false;
        select.addEventListener("change", () => {
            showFeedback("");
            refresh({ announce: true });
        });
    }

    async function init() {
        window.AppAuth.garantirToken();
        el("printHistoryRefresh")?.addEventListener("click", () => refresh({ announce: true }));
        try {
            await loadProfessorContext();
        } catch (error) {
            showFeedback(error.message || "Não foi possível carregar os professores.", true);
        }
        await refresh();
        pollTimer = window.setInterval(refresh, POLL_INTERVAL_MS);
    }

    window.addEventListener("beforeunload", () => window.clearInterval(pollTimer));
    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})(window, document);
