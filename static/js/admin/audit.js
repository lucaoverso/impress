const AUDIT_CATEGORY_LABELS = {
    auth: "Login",
    password: "Senha",
    printing: "Impressão",
    scheduling: "Agendamento",
    attachments: "Anexos"
};
const AUDIT_ACTION_LABELS = {
    "login.attempt": "Tentativa de login",
    "login.success": "Login realizado",
    "password.reset": "Redefinicao de senha",
    "password.reset.admin": "Senha redefinida pelo admin",
    "print.submitted": "Impressão enviada",
    "reservation.create": "Agendamento",
    "attachment.submitted": "Anexo enviado"
};
let auditCurrentPage = 1;
let auditTotalPages = 0;

function auditFormatDateTime(value) {
    if (!value) return "Data não informada";
    const parsed = new Date(`${String(value).replace(" ", "T")}Z`);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString("pt-BR", {
        dateStyle: "short",
        timeStyle: "short"
    });
}

function auditCreateText(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.innerText = text || "";
    return element;
}

function auditMetadataSummary(metadata) {
    if (!metadata || typeof metadata !== "object") return "";
    const parts = [];
    if (metadata.date) parts.push(`Data: ${metadata.date}`);
    if (metadata.class) parts.push(`Turma: ${metadata.class}`);
    if (metadata.pages_consumed != null) {
        parts.push(`${metadata.pages_consumed} página(s)`);
    }
    if (metadata.file_size != null) {
        const sizeKb = Math.max(1, Math.round(Number(metadata.file_size) / 1024));
        parts.push(`${sizeKb} KB`);
    }
    return parts.join(" · ");
}

function renderAuditEvent(event) {
    const item = document.createElement("article");
    item.className = `audit-event audit-event-${event.outcome}`;
    const status = auditCreateText(
        "span",
        `audit-status audit-status-${event.outcome}`,
        event.outcome === "success" ? "Sucesso" : "Falha"
    );
    const category = auditCreateText(
        "span",
        "audit-category",
        AUDIT_CATEGORY_LABELS[event.category] || event.category
    );
    const title = auditCreateText(
        "strong",
        "audit-event-title",
        AUDIT_ACTION_LABELS[event.action] || event.action
    );
    const description = auditCreateText(
        "p",
        "audit-event-description",
        event.description
    );
    const identity = event.actor_name || event.actor_email || "Usuário não identificado";
    const meta = auditCreateText(
        "small",
        "audit-event-meta",
        `${auditFormatDateTime(event.created_at)} · ${identity}`
    );

    const header = document.createElement("div");
    header.className = "audit-event-header";
    const labels = document.createElement("div");
    labels.className = "audit-event-labels";
    labels.append(category, status);
    header.append(title, labels);
    item.append(header, description, meta);

    const detail = auditMetadataSummary(event.metadata);
    if (detail) item.append(auditCreateText("small", "audit-event-detail", detail));
    return item;
}

function renderAuditEvents(payload) {
    const container = el("auditEventList");
    container.innerHTML = "";
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (items.length === 0) {
        container.appendChild(auditCreateText(
            "div",
            "audit-empty",
            "Nenhuma atividade encontrada para os filtros selecionados."
        ));
    } else {
        items.forEach((event) => container.appendChild(renderAuditEvent(event)));
    }

    const total = Number(payload?.total || 0);
    auditTotalPages = Number(payload?.pages || 0);
    el("auditTotal").innerText = `${total} evento${total === 1 ? "" : "s"}`;
    el("auditPageInfo").innerText = auditTotalPages
        ? `Página ${auditCurrentPage} de ${auditTotalPages}`
        : "Sem páginas";
    el("btnAuditPrevious").disabled = auditCurrentPage <= 1;
    el("btnAuditNext").disabled = auditTotalPages === 0 || auditCurrentPage >= auditTotalPages;
}

function auditBuildQuery() {
    const params = new URLSearchParams({
        page: String(auditCurrentPage),
        page_size: "30"
    });
    const filters = {
        date_from: el("auditDateFrom").value,
        date_to: el("auditDateTo").value,
        category: el("auditCategory").value,
        outcome: el("auditOutcome").value,
        search: el("auditSearch").value.trim()
    };
    Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, value);
    });
    return params.toString();
}

async function loadAuditEvents({ resetPage = false } = {}) {
    if (!usuarioEhAdmin || !el("auditEventList")) return;
    if (resetPage) auditCurrentPage = 1;
    el("auditMessage").innerText = "Carregando atividades...";
    try {
        const payload = await fetchJson(
            `/admin/audit/events?${auditBuildQuery()}`,
            { headers }
        );
        renderAuditEvents(payload);
        el("auditMessage").innerText = "";
    } catch (err) {
        el("auditMessage").innerText = err.message;
        el("auditEventList").innerHTML = "";
    }
}

function clearAuditFilters() {
    el("formAuditFilters").reset();
    loadAuditEvents({ resetPage: true });
}

function registerAuditEvents() {
    el("formAuditFilters")?.addEventListener("submit", (event) => {
        event.preventDefault();
        loadAuditEvents({ resetPage: true });
    });
    el("btnClearAuditFilters")?.addEventListener("click", clearAuditFilters);
    el("btnAuditPrevious")?.addEventListener("click", () => {
        if (auditCurrentPage <= 1) return;
        auditCurrentPage -= 1;
        loadAuditEvents();
    });
    el("btnAuditNext")?.addEventListener("click", () => {
        if (auditCurrentPage >= auditTotalPages) return;
        auditCurrentPage += 1;
        loadAuditEvents();
    });
}
