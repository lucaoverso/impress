const SEARCH_DEBOUNCE_MS = 220;
const OCCURRENCES_PAGE_SIZE = 10;

const STATUS_LABELS = {
    registrado: "Registrado",
    em_acompanhamento: "Em acompanhamento",
    aguardando_responsavel: "Aguardando responsavel",
    resolvido: "Resolvido",
};

const PRE_REGISTRATION_STATUS_LABELS = {
    pending: "Pendente",
    completed: "Concluido",
    cancelled: "Cancelado",
};

const RESPONSIBLE_CONTACT_LABELS = {
    none: "Sem solicitacao de contato",
    communicate: "Comunicar responsavel",
    summon: "Convocar responsavel",
};

const SIGNATURE_LABELS = {
    estudante: "Estudante",
    responsavel: "Responsavel",
};

const elements = {
    body: document.body,
    panelLinks: Array.from(document.querySelectorAll("[data-panel-link]")),
    panels: Array.from(document.querySelectorAll("[data-panel]")),
    managerOnly: Array.from(document.querySelectorAll("[data-manager-only]")),
    searchForm: document.querySelector("[data-top-navbar-search]"),
    searchInput: document.querySelector("[data-top-navbar-search-input]"),
    contextCopy: document.querySelector("[data-context-copy]"),
    heroCopy: document.querySelector("[data-hero-copy]"),
    roleSummary: document.querySelector("[data-role-summary]"),
    profileName: document.querySelector("[data-profile-name]"),
    profileRole: document.querySelector("[data-profile-role]"),
    profileInitials: document.querySelector("[data-profile-initials]"),
    occurrenceCreateAction: document.querySelector("[data-occurrence-create-action]"),
    primaryAction: document.querySelector("[data-primary-action]"),
    primaryActionIcon: document.querySelector("[data-primary-action-icon]"),
    primaryActionLabel: document.querySelector("[data-primary-action-label]"),
    fabAction: document.querySelector("[data-fab-action]"),
    fabIcon: document.querySelector("[data-fab-icon]"),
    fabLabel: document.querySelector("[data-fab-label]"),
    logout: document.querySelector("[data-app-logout]"),

    metricTotal: document.querySelector("[data-metric-total]"),
    metricPending: document.querySelector("[data-metric-pending]"),
    metricResolved: document.querySelector("[data-metric-resolved]"),

    occurrenceFeedback: document.querySelector("[data-occurrence-feedback]"),
    occurrenceFilters: document.querySelector("[data-coordenacao-filters]"),
    clearOccurrenceFilters: document.querySelector("[data-clear-occurrence-filters]"),
    occurrenceList: document.querySelector("[data-occurrence-list]"),
    occurrenceModal: document.querySelector("[data-occurrence-modal]"),
    occurrenceModalClose: document.querySelector("[data-occurrence-modal-close]"),
    occurrenceModalTitle: document.querySelector("[data-occurrence-modal-title]"),
    occurrenceModalSubtitle: document.querySelector("[data-occurrence-modal-subtitle]"),
    occurrenceModalFeedback: document.querySelector("[data-occurrence-modal-feedback]"),
    occurrenceDetail: document.querySelector("[data-occurrence-detail]"),
    occurrencePaginationSummary: document.querySelector("[data-occurrence-pagination-summary]"),
    occurrencePagination: document.querySelector("[data-occurrence-pagination]"),

    legalForm: document.querySelector("[data-base-legal-form]"),
    legalCancel: document.querySelector("[data-legal-cancel]"),
    legalFeedback: document.querySelector("[data-legal-feedback]"),
    legalSubmitLabel: document.querySelector("[data-legal-submit-label] span:last-child"),
    legalTableBody: document.querySelector("[data-legal-table-body]"),

    studentForm: document.querySelector("[data-student-form]"),
    studentCancel: document.querySelector("[data-student-cancel]"),
    studentFeedback: document.querySelector("[data-student-feedback]"),
    studentSubmitLabel: document.querySelector("[data-student-submit-label] span:last-child"),
    studentSearchForm: document.querySelector("[data-student-search-form]"),
    studentTableBody: document.querySelector("[data-student-table-body]"),
    studentClassSelect: document.querySelector("[data-student-class-select]"),
    studentFilterClass: document.querySelector("[data-student-filter-class]"),

    reportRepeatRate: document.querySelector("[data-report-repeat-rate]"),
    reportCompletionTime: document.querySelector("[data-report-completion-time]"),
    reportTopClass: document.querySelector("[data-report-top-class]"),

    teacherFlow: document.querySelector("[data-teacher-flow]"),
    teacherPreRegistrationForm: document.querySelector("[data-teacher-pre-registration-form]"),
    teacherStudentSearch: document.querySelector("[data-teacher-student-search]"),
    teacherStudentResults: document.querySelector("[data-teacher-student-results]"),
    teacherSelectedStudents: document.querySelector("[data-teacher-selected-students]"),
    teacherReasons: document.querySelector("[data-teacher-reasons]"),
    teacherFeedback: document.querySelector("[data-teacher-feedback]"),
    teacherPreRegistrations: document.querySelector("[data-teacher-pre-registrations]"),

    managerFlow: document.querySelector("[data-manager-flow]"),
    managerFlowFeedback: document.querySelector("[data-manager-flow-feedback]"),
    preRegistrationQueue: document.querySelector("[data-pre-registration-queue]"),
    preRegistrationCount: document.querySelector("[data-pre-registration-count]"),
    reasonForm: document.querySelector("[data-teacher-reason-form]"),
    reasonFeedback: document.querySelector("[data-reason-feedback]"),
    reasonList: document.querySelector("[data-reason-list]"),
};

const token = window.AppAuth?.garantirToken?.() || "";
const headers = window.AppAuth?.criarHeadersAuth?.(token) || { Authorization: `Bearer ${token}` };
const headersJson = window.AppAuth?.criarHeadersJsonAuth?.(token) || {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
};

const state = {
    user: null,
    isManager: false,
    isTeacher: false,
    currentPanel: "ocorrencias",
    occurrenceContext: null,
    occurrences: [],
    occurrencePage: 1,
    selectedOccurrenceId: null,
    occurrenceDetails: new Map(),
    occurrenceDetailLoading: false,
    legalItems: [],
    students: [],
    preRegistrationContext: null,
    preRegistrations: [],
    teacherSelectedStudents: [],
    teacherSearchTimer: null,
};

function query(selector, scope = document) {
    return scope.querySelector(selector);
}

function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

function boolValue(value) {
    return value === true || value === 1 || value === "1";
}

function escapePanelFallback() {
    return elements.panelLinks.find((link) => !link.hidden)?.dataset.panelLink || "fluxo-professor";
}

function setFeedback(target, message = "", tone = "") {
    if (!target) return;
    if (!message) {
        target.hidden = true;
        target.textContent = "";
        delete target.dataset.tone;
        return;
    }
    target.hidden = false;
    target.textContent = message;
    if (tone) {
        target.dataset.tone = tone;
    } else {
        delete target.dataset.tone;
    }
}

function formatShortDate(value) {
    if (!value) return "Nao informado";
    const date = new Date(`${String(value).trim()}T00:00:00`);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString("pt-BR");
}

function formatDateTime(value) {
    if (!value) return "Nao informado";
    const text = String(value).trim().replace(" ", "T");
    const date = new Date(`${text}Z`);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString("pt-BR");
}

function formatDurationDays(value) {
    if (!Number.isFinite(value) || value <= 0) return "-";
    if (value < 1) {
        return `${Math.max(1, Math.round(value * 24))} h`;
    }
    return `${value.toFixed(1).replace(".", ",")} dias`;
}

function initialsFromName(value) {
    const parts = String(value || "")
        .trim()
        .split(/\s+/)
        .filter(Boolean);
    if (!parts.length) return "SE";
    return parts.slice(0, 2).map((item) => item[0]?.toUpperCase() || "").join("");
}

function normalizeText(value, fallback = "") {
    const text = String(value || "").trim();
    return text || fallback;
}

function truncateText(value, limit = 180) {
    const text = normalizeText(value);
    if (text.length <= limit) return text;
    return `${text.slice(0, limit - 1).trimEnd()}...`;
}

function optionLabel(list, value, fallback = "Nao informado") {
    const match = (list || []).find((item) => String(item.id) === String(value));
    return normalizeText(match?.nome, fallback);
}

function statusBadgeVariant(status) {
    if (status === "resolvido" || status === "completed") return "ui-badge--success";
    if (status === "em_acompanhamento") return "ui-badge--warning";
    if (status === "aguardando_responsavel") return "ui-badge--danger";
    if (status === "pending") return "ui-badge--warning";
    return "ui-badge--info";
}

function occurrenceTypeLabel(type) {
    return optionLabel(state.occurrenceContext?.tipos_registro, type, normalizeText(type, "Nao informado"));
}

function occurrenceStatusLabel(status) {
    return optionLabel(
        state.occurrenceContext?.status,
        status,
        STATUS_LABELS[status] || normalizeText(status, "Nao informado")
    );
}

function occurrenceActionLabel(action) {
    return optionLabel(
        state.occurrenceContext?.acoes_aplicadas,
        action,
        normalizeText(action, "Nao informada")
    );
}

function occurrenceSignatureLabel(value) {
    return optionLabel(
        state.occurrenceContext?.quem_assina,
        value,
        SIGNATURE_LABELS[value] || normalizeText(value, "Nao informado")
    );
}

function feedbackTargetForCurrentPanel() {
    if (!state.isManager) return elements.teacherFeedback;
    if (state.currentPanel === "base-legal") return elements.legalFeedback;
    if (state.currentPanel === "estudantes") return elements.studentFeedback;
    if (state.currentPanel === "fluxo-professor") return elements.managerFlowFeedback;
    return elements.occurrenceFeedback;
}

function occurrenceReferenceValue(occurrence) {
    return normalizeText(
        occurrence?.nome_estudante,
        normalizeText(occurrence?.professor_requerente, normalizeText(occurrence?.turma_nome))
    );
}

function seedOccurrenceDetails(items = []) {
    items.forEach((item) => {
        state.occurrenceDetails.set(Number(item.id), item);
    });
}

function isOccurrenceModalOpen() {
    return Boolean(elements.occurrenceModal?.open || elements.occurrenceModal?.hasAttribute("open"));
}

function openOccurrenceModal() {
    if (!elements.occurrenceModal) return;
    if (typeof elements.occurrenceModal.showModal === "function") {
        if (!elements.occurrenceModal.open) {
            elements.occurrenceModal.showModal();
        }
    } else {
        elements.occurrenceModal.setAttribute("open", "");
    }
    elements.body.classList.add("coordenacao-modal-open");
}

function closeOccurrenceModal() {
    setFeedback(elements.occurrenceModalFeedback);
    if (!elements.occurrenceModal) return;
    if (typeof elements.occurrenceModal.close === "function" && elements.occurrenceModal.open) {
        elements.occurrenceModal.close();
    } else {
        elements.occurrenceModal.removeAttribute("open");
    }
    elements.body.classList.remove("coordenacao-modal-open");
}

function setPanel(targetId, { updateHash = true } = {}) {
    const available = new Set(
        elements.panelLinks
            .filter((link) => !link.hidden)
            .map((link) => link.dataset.panelLink)
    );
    const nextPanel = available.has(targetId) ? targetId : escapePanelFallback();
    state.currentPanel = nextPanel;

    elements.panelLinks.forEach((link) => {
        const active = link.dataset.panelLink === nextPanel;
        link.classList.toggle("is-active", active);
        if (active) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });

    elements.panels.forEach((panel) => {
        const active = panel.dataset.panel === nextPanel;
        panel.hidden = !active;
        panel.classList.toggle("is-active", active);
    });

    if (updateHash) {
        window.history.replaceState(null, "", `#${nextPanel}`);
    }
}

function renderRoleShell() {
    const userName = normalizeText(state.user?.nome || state.user?.email, "Usuario");
    const cargo = window.AppAuth?.normalizarCargoUsuario?.(state.user) || "USUARIO";

    elements.profileName.textContent = userName;
    elements.profileRole.textContent = state.isManager ? "Gestao do modulo" : "Fluxo de pre-registro";
    elements.profileInitials.textContent = initialsFromName(userName);
    elements.contextCopy.textContent = state.isManager ? "Modulo de coordenacao" : "Fluxo docente";

    if (state.isManager) {
        elements.heroCopy.textContent = "Gestao de ocorrencias, pendencias docentes e cadastros auxiliares em uma experiencia unica.";
        elements.roleSummary.textContent = `${cargo} com acesso de gestao. Ocorrencias, base legal, estudantes e fila docente ficam concentrados nesta interface.`;
        elements.searchInput.placeholder = "Buscar estudante, motivo ou registro...";
        elements.primaryAction.href = "#fluxo-professor";
        elements.primaryAction.dataset.panelTarget = "fluxo-professor";
        elements.primaryActionIcon.textContent = "notifications_active";
        elements.primaryActionLabel.textContent = "Abrir pendencias";
        elements.fabAction.href = "#fluxo-professor";
        elements.fabAction.dataset.panelTarget = "fluxo-professor";
        elements.fabIcon.textContent = "notifications";
        elements.fabLabel.textContent = "Abrir fila da coordenacao";
    } else {
        elements.heroCopy.textContent = "Encaminhe casos para a coordenacao com o fluxo de pre-registro ja conectado ao backend.";
        elements.roleSummary.textContent = `${cargo} com acesso ao modulo. O envio de pre-registros ja funciona nesta interface.`;
        elements.searchInput.placeholder = "Buscar estudante para o pre-registro...";
        elements.primaryAction.href = "#teacher-pre-registration-form";
        delete elements.primaryAction.dataset.panelTarget;
        elements.primaryActionIcon.textContent = "send";
        elements.primaryActionLabel.textContent = "Novo pre-registro";
        elements.fabAction.href = "#teacher-pre-registration-form";
        delete elements.fabAction.dataset.panelTarget;
        elements.fabIcon.textContent = "send";
        elements.fabLabel.textContent = "Enviar pre-registro";
    }

    elements.managerOnly.forEach((item) => {
        item.hidden = !state.isManager;
    });

    if (elements.teacherFlow) {
        elements.teacherFlow.hidden = state.isManager;
    }
    if (elements.managerFlow) {
        elements.managerFlow.hidden = !state.isManager;
    }
}

function createBadge(label, variant = "") {
    const badge = createElement("span", `ui-badge ${variant}`.trim(), label);
    return badge;
}

function serializeForm(form) {
    const params = new URLSearchParams();
    if (!form) return params;
    const formData = new FormData(form);
    formData.forEach((value, key) => {
        const text = normalizeText(value);
        if (text) params.set(key, text);
    });
    return params;
}

function renderOccurrenceMetrics() {
    const total = state.occurrences.length;
    const resolved = state.occurrences.filter((item) => item.status === "resolvido").length;
    const pending = total - resolved;
    elements.metricTotal.textContent = String(total);
    elements.metricPending.textContent = String(pending);
    elements.metricResolved.textContent = String(resolved);
}

function occurrencePageItems() {
    const start = (state.occurrencePage - 1) * OCCURRENCES_PAGE_SIZE;
    return state.occurrences.slice(start, start + OCCURRENCES_PAGE_SIZE);
}

function ensureSelectedOccurrence() {
    if (!state.occurrences.length) {
        state.selectedOccurrenceId = null;
        return;
    }
    const current = state.occurrences.find((item) => Number(item.id) === Number(state.selectedOccurrenceId));
    if (!current) {
        state.selectedOccurrenceId = Number(state.occurrences[0].id);
    }
}

async function openOccurrencePdf(occurrence) {
    const response = await window.AppApi.fetchResposta(`/ocorrencias/${occurrence.id}/pdf`, { headers });
    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.target = "_blank";
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60_000);
}

function createActionButton(label, { primary = false, variant = "ghost", onClick } = {}) {
    const resolvedVariant = primary ? "primary" : variant;
    const className = {
        primary: "ui-button ui-button--primary",
        subtle: "ui-button ui-button--subtle",
        ghost: "ui-button ui-button--ghost",
    }[resolvedVariant] || "ui-button ui-button--ghost";
    const button = createElement("button", className);
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
}

function renderOccurrenceDetail() {
    const occurrenceId = Number(state.selectedOccurrenceId || 0);
    const occurrence = state.occurrenceDetails.get(occurrenceId)
        || state.occurrences.find((item) => Number(item.id) === occurrenceId);
    elements.occurrenceDetail.innerHTML = "";

    if (state.occurrenceDetailLoading && !occurrence) {
        elements.occurrenceModalTitle.textContent = "Carregando detalhes";
        elements.occurrenceModalSubtitle.textContent = "Buscando o registro completo para montar o resumo.";
        elements.occurrenceDetail.innerHTML = `
            <div class="coordenacao-detail-skeleton" aria-hidden="true">
                <section class="coordenacao-detail-skeleton__card">
                    <span class="coordenacao-detail-skeleton__line is-title"></span>
                    <span class="coordenacao-detail-skeleton__line is-medium"></span>
                    <span class="coordenacao-detail-skeleton__line"></span>
                </section>
                <section class="coordenacao-detail-grid">
                    <div class="coordenacao-detail-skeleton__card">
                        <span class="coordenacao-detail-skeleton__line is-short"></span>
                        <span class="coordenacao-detail-skeleton__line"></span>
                        <span class="coordenacao-detail-skeleton__line"></span>
                        <span class="coordenacao-detail-skeleton__line is-medium"></span>
                    </div>
                    <div class="coordenacao-detail-skeleton__card">
                        <span class="coordenacao-detail-skeleton__line is-short"></span>
                        <span class="coordenacao-detail-skeleton__line"></span>
                        <span class="coordenacao-detail-skeleton__line is-medium"></span>
                    </div>
                </section>
            </div>
        `;
        return;
    }

    if (!occurrence) {
        elements.occurrenceModalTitle.textContent = "Detalhes da ocorrencia";
        elements.occurrenceModalSubtitle.textContent = "Contexto completo, descricao e base legal do registro selecionado.";
        const empty = createElement("p", "coordenacao-empty-state", "Selecione um registro para ver os detalhes.");
        elements.occurrenceDetail.appendChild(empty);
        return;
    }

    const headerReference = occurrenceReferenceValue(occurrence);
    elements.occurrenceModalTitle.textContent = headerReference || `Ocorrencia #${occurrence.id}`;
    elements.occurrenceModalSubtitle.textContent = `Registro #${occurrence.id} atualizado em ${formatDateTime(occurrence.atualizado_em)}.`;

    const shell = createElement("div", "coordenacao-detail-shell");

    const highlight = createElement("section", "coordenacao-detail-highlight");
    const highlightTop = createElement("div", "coordenacao-detail-highlight__top");
    const highlightTitle = createElement("div", "coordenacao-detail-highlight__title");
    const highlightContext = [
        normalizeText(occurrence.turma_nome),
        normalizeText(occurrence.professor_requerente),
    ].filter(Boolean).join(" · ") || "Contexto nao informado";
    highlightTitle.appendChild(createElement("p", "", `Ocorrencia #${occurrence.id}`));
    highlightTitle.appendChild(createElement("h3", "", headerReference || "Registro sem referencia"));
    highlightTitle.appendChild(createElement("p", "", highlightContext));

    const badges = createElement("div", "coordenacao-chip-list");
    badges.appendChild(createBadge(occurrenceStatusLabel(occurrence.status), statusBadgeVariant(occurrence.status)));
    badges.appendChild(createBadge(occurrenceTypeLabel(occurrence.tipo_registro)));
    badges.appendChild(createBadge(occurrenceActionLabel(occurrence.acao_aplicada), "ui-badge--info"));
    highlightTop.append(highlightTitle, badges);
    highlight.appendChild(highlightTop);

    const highlightMeta = createElement(
        "p",
        "",
        `Data ${formatShortDate(occurrence.data_ocorrencia)} · Horario ${normalizeText(occurrence.horario_ocorrencia, "Nao informado")} · Status ${occurrenceStatusLabel(occurrence.status)}`
    );
    highlight.appendChild(highlightMeta);

    const detailGrid = createElement("section", "coordenacao-detail-grid");

    const contextCard = createElement("article", "coordenacao-detail-card");
    contextCard.appendChild(createElement("h3", "", "Contexto do registro"));
    const meta = createElement("dl", "coordenacao-detail-meta");
    [
        ["Turma", occurrence.turma_nome || "Sem turma"],
        ["Professor requerente", occurrence.professor_requerente || "Nao informado"],
        ["Disciplina", occurrence.disciplina || "Nao informada"],
        ["Data da ocorrencia", formatShortDate(occurrence.data_ocorrencia)],
        ["Horario", occurrence.horario_ocorrencia || "Nao informado"],
        ["Aula", occurrence.aula || "Nao informada"],
        ["Acao aplicada", occurrenceActionLabel(occurrence.acao_aplicada)],
        ["Quem assina", occurrenceSignatureLabel(occurrence.quem_assina)],
    ].forEach(([label, value]) => {
        const wrapper = createElement("div");
        wrapper.appendChild(createElement("dt", "", label));
        wrapper.appendChild(createElement("dd", "", value));
        meta.appendChild(wrapper);
    });
    contextCard.appendChild(meta);

    const narrativeCard = createElement("article", "coordenacao-detail-card");
    narrativeCard.appendChild(createElement("h3", "", "Descricao"));
    const description = createElement("p", "coordenacao-detail-rich-text", normalizeText(occurrence.descricao, "Sem descricao."));
    narrativeCard.appendChild(description);

    detailGrid.append(contextCard, narrativeCard);

    const legalCard = createElement("article", "coordenacao-detail-card");
    legalCard.appendChild(createElement("h3", "", "Base legal vinculada"));
    const legalList = createElement("ul", "coordenacao-detail-list");
    const legalItems = Array.isArray(occurrence.regimento_itens) ? occurrence.regimento_itens : [];
    if (legalItems.length) {
        legalItems.forEach((item) => {
            const row = createElement("li");
            row.appendChild(createElement("strong", "", item.artigo || "Referencia"));
            row.appendChild(createElement("span", "", item.descricao || "Sem descricao"));
            if (item.lei_nome) {
                row.appendChild(createElement("span", "", item.lei_nome));
            }
            legalList.appendChild(row);
        });
    } else {
        legalList.appendChild(createElement("li", "", "Nenhuma base legal vinculada."));
    }
    legalCard.appendChild(legalList);

    const actions = createElement("div", "coordenacao-detail-actions");
    actions.appendChild(createActionButton("Fechar", {
        onClick: () => {
            closeOccurrenceModal();
        },
    }));

    const referenceFilter = occurrenceReferenceValue(occurrence);
    if (referenceFilter) {
        actions.appendChild(createActionButton("Filtrar referencia", {
            variant: "subtle",
            onClick: () => {
                filterOccurrencesByReference(referenceFilter);
            },
        }));
    }

    actions.appendChild(createActionButton("Abrir PDF", {
        primary: true,
        onClick: () => {
            openOccurrencePdf(occurrence).catch((error) => {
                setFeedback(elements.occurrenceModalFeedback, error.message || "Nao foi possivel abrir o PDF.", "error");
            });
        },
    }));

    shell.append(highlight, detailGrid, legalCard, actions);
    elements.occurrenceDetail.appendChild(shell);
}

async function loadOccurrenceDetail(occurrenceId, { force = false } = {}) {
    const id = Number(occurrenceId || 0);
    if (!id) return;
    if (!force && state.occurrenceDetails.has(id)) {
        renderOccurrenceDetail();
    }

    state.occurrenceDetailLoading = true;
    renderOccurrenceDetail();
    setFeedback(elements.occurrenceModalFeedback);

    try {
        const occurrence = await window.AppApi.fetchJson(`/ocorrencias/${id}`, { headers });
        state.occurrenceDetails.set(id, occurrence);
        if (Number(state.selectedOccurrenceId) === id) {
            renderOccurrenceDetail();
        }
    } finally {
        state.occurrenceDetailLoading = false;
        if (Number(state.selectedOccurrenceId) === id) {
            renderOccurrenceDetail();
        }
    }
}

function openOccurrenceDetail(occurrenceId) {
    state.selectedOccurrenceId = Number(occurrenceId);
    openOccurrenceModal();
    renderOccurrenceDetail();
    loadOccurrenceDetail(occurrenceId).catch((error) => {
        state.occurrenceDetailLoading = false;
        renderOccurrenceDetail();
        setFeedback(elements.occurrenceModalFeedback, error.message || "Nao foi possivel carregar os detalhes da ocorrencia.", "error");
    });
}

function filterOccurrencesByReference(reference) {
    const value = normalizeText(reference);
    if (!value || !elements.occurrenceFilters) return;

    setPanel("ocorrencias");
    query('[name="nome_estudante"]', elements.occurrenceFilters).value = value;
    closeOccurrenceModal();
    loadOccurrences().catch((error) => {
        setFeedback(elements.occurrenceFeedback, error.message || "Nao foi possivel aplicar o filtro.", "error");
    });
}

async function refreshCurrentPanel() {
    if (state.isManager) {
        if (state.currentPanel === "base-legal") {
            await loadLegalItems();
            return;
        }
        if (state.currentPanel === "estudantes") {
            await loadStudents();
            return;
        }
        if (state.currentPanel === "fluxo-professor") {
            await Promise.all([loadPreRegistrationContext(), loadPreRegistrations()]);
            return;
        }
        await Promise.all([
            loadOccurrences({ resetPage: false }),
            loadPreRegistrations(),
        ]);
        if (isOccurrenceModalOpen() && state.selectedOccurrenceId) {
            await loadOccurrenceDetail(state.selectedOccurrenceId, { force: true });
        }
        return;
    }

    await Promise.all([
        loadPreRegistrationContext(),
        loadPreRegistrations(),
    ]);
}

function renderOccurrencePagination() {
    const totalItems = state.occurrences.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / OCCURRENCES_PAGE_SIZE));
    if (state.occurrencePage > totalPages) {
        state.occurrencePage = totalPages;
    }

    const start = totalItems ? (state.occurrencePage - 1) * OCCURRENCES_PAGE_SIZE + 1 : 0;
    const end = Math.min(totalItems, state.occurrencePage * OCCURRENCES_PAGE_SIZE);
    elements.occurrencePaginationSummary.textContent = totalItems
        ? `Mostrando ${start}-${end} de ${totalItems} registros`
        : "Nenhum registro encontrado.";

    elements.occurrencePagination.innerHTML = "";
    if (totalPages <= 1) return;

    const pages = [];
    for (let page = 1; page <= totalPages; page += 1) {
        if (
            page === 1
            || page === totalPages
            || Math.abs(page - state.occurrencePage) <= 1
        ) {
            pages.push(page);
        }
    }

    const normalizedPages = pages.filter((page, index, list) => list.indexOf(page) === index);
    normalizedPages.forEach((page, index) => {
        if (index > 0 && page - normalizedPages[index - 1] > 1) {
            const spacer = createElement("span", "coordenacao-page-button", "...");
            spacer.setAttribute("aria-hidden", "true");
            elements.occurrencePagination.appendChild(spacer);
        }

        const button = createElement("button", `coordenacao-page-button${page === state.occurrencePage ? " is-active" : ""}`, String(page));
        button.type = "button";
        if (page === state.occurrencePage) {
            button.setAttribute("aria-current", "page");
        }
        button.addEventListener("click", () => {
            state.occurrencePage = page;
            renderOccurrenceCards();
        });
        elements.occurrencePagination.appendChild(button);
    });
}

function renderOccurrenceCards() {
    elements.occurrenceList.innerHTML = "";
    const items = occurrencePageItems();

    if (!items.length) {
        elements.occurrenceList.appendChild(
            createElement("p", "coordenacao-empty-state", "Nenhum registro encontrado com os filtros atuais.")
        );
        renderOccurrencePagination();
        if (isOccurrenceModalOpen()) {
            closeOccurrenceModal();
        }
        return;
    }

    items.forEach((occurrence) => {
        const card = createElement(
            "article",
            `coordenacao-record${occurrence.status === "resolvido" ? " is-resolved" : ""}`
        );
        card.dataset.status = occurrence.status;

        const main = createElement("div", "coordenacao-record__main");
        const avatar = createElement("span", `coordenacao-record__avatar${occurrence.status === "resolvido" ? " is-muted" : ""}`);
        const icon = createElement("span", "ui-icon", occurrence.tipo_registro === "professor" ? "school" : "person");
        avatar.appendChild(icon);

        const content = createElement("div", "coordenacao-record__content");
        const titleRow = createElement("div", "coordenacao-record__title-row");
        titleRow.appendChild(createElement("h2", "", occurrence.nome_estudante || "Registro"));
        titleRow.appendChild(createBadge(occurrenceStatusLabel(occurrence.status), statusBadgeVariant(occurrence.status)));

        const meta = createElement("dl", "coordenacao-record__meta");
        [
            ["Turma", occurrence.turma_nome || "Sem turma", "school", ""],
            ["Data", formatShortDate(occurrence.data_ocorrencia), "calendar_today", ""],
            ["Tipo", occurrenceTypeLabel(occurrence.tipo_registro), occurrence.tipo_registro === "estudante" ? "warning" : "book", occurrence.tipo_registro === "estudante" ? "is-primary" : "is-tertiary"],
        ].forEach(([label, value, iconName, className]) => {
            const wrapper = createElement("div");
            wrapper.appendChild(createElement("dt", "", label));
            const dd = createElement("dd", className);
            dd.appendChild(createElement("span", "ui-icon", iconName));
            dd.appendChild(document.createTextNode(value));
            wrapper.appendChild(dd);
            meta.appendChild(wrapper);
        });

        const description = createElement("p", "", truncateText(occurrence.descricao, 220));
        content.append(titleRow, meta, description);
        main.append(avatar, content);

        const actions = createElement("div", "coordenacao-record__actions");
        actions.appendChild(createActionButton("Ver detalhes", {
            primary: true,
            onClick: () => {
                openOccurrenceDetail(occurrence.id);
            },
        }));
        actions.appendChild(createActionButton("Abrir PDF", {
            onClick: () => {
                openOccurrencePdf(occurrence).catch((error) => {
                    setFeedback(elements.occurrenceFeedback, error.message || "Nao foi possivel abrir o PDF.", "error");
                });
            },
        }));
        const referenceFilter = occurrenceReferenceValue(occurrence);
        if (referenceFilter) {
            actions.appendChild(createActionButton("Filtrar referencia", {
                variant: "subtle",
                onClick: () => {
                    filterOccurrencesByReference(referenceFilter);
                },
            }));
        }

        card.append(main, actions);
        elements.occurrenceList.appendChild(card);
    });

    renderOccurrencePagination();
    if (isOccurrenceModalOpen()) {
        renderOccurrenceDetail();
    }
}

function populateSelect(select, items, { includeBlank = false, blankLabel = "Selecione" } = {}) {
    if (!select) return;
    const currentValue = select.value;
    select.innerHTML = "";

    if (includeBlank) {
        const blank = document.createElement("option");
        blank.value = "";
        blank.textContent = blankLabel;
        select.appendChild(blank);
    }

    (items || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.id);
        option.textContent = item.nome;
        select.appendChild(option);
    });

    if (currentValue && Array.from(select.options).some((option) => option.value === currentValue)) {
        select.value = currentValue;
    }
}

function populateManagerFilters() {
    populateSelect(query("[data-filter-turma]"), state.occurrenceContext?.turmas || [], {
        includeBlank: true,
        blankLabel: "Todas as turmas",
    });
    populateSelect(query("[data-filter-tipo]"), state.occurrenceContext?.tipos_registro || [], {
        includeBlank: true,
        blankLabel: "Todos os tipos",
    });
    populateSelect(query("[data-filter-status]"), state.occurrenceContext?.status || [], {
        includeBlank: true,
        blankLabel: "Todos os status",
    });

    const classes = (state.occurrenceContext?.turmas || []).map((item) => ({ id: item.id, nome: item.nome }));
    populateSelect(elements.studentClassSelect, classes, {
        includeBlank: true,
        blankLabel: "Selecione uma turma",
    });
    populateSelect(elements.studentFilterClass, classes, {
        includeBlank: true,
        blankLabel: "Todas as turmas",
    });
}

async function loadOccurrences({ resetPage = true } = {}) {
    const params = serializeForm(elements.occurrenceFilters);
    const queryString = params.toString();
    const url = queryString ? `/ocorrencias?${queryString}` : "/ocorrencias";
    const items = await window.AppApi.fetchJson(url, { headers });
    state.occurrences = Array.isArray(items) ? items : [];
    seedOccurrenceDetails(state.occurrences);
    if (resetPage) {
        state.occurrencePage = 1;
    }
    ensureSelectedOccurrence();
    renderOccurrenceMetrics();
    renderOccurrenceCards();
    renderReports();
    setFeedback(elements.occurrenceFeedback);
}

function legalFormPayload() {
    const formData = new FormData(elements.legalForm);
    return {
        lei_nome: normalizeText(formData.get("lei_nome"), "Base legal"),
        artigo_numero: normalizeText(formData.get("artigo_numero")),
        artigo_descricao: normalizeText(formData.get("artigo_descricao")),
        inciso_numero: normalizeText(formData.get("inciso_numero")),
        inciso_descricao: normalizeText(formData.get("inciso_descricao")),
        alinea_identificador: normalizeText(formData.get("alinea_identificador")),
        alinea_descricao: normalizeText(formData.get("alinea_descricao")),
    };
}

function resetLegalForm() {
    elements.legalForm.reset();
    query('[name="item_id"]', elements.legalForm).value = "";
    elements.legalSubmitLabel.textContent = "Salvar referencia";
    elements.legalCancel.hidden = true;
    setFeedback(elements.legalFeedback);
}

function fillLegalForm(item) {
    query('[name="item_id"]', elements.legalForm).value = String(item.id);
    query('[name="lei_nome"]', elements.legalForm).value = item.lei_nome || "";
    query('[name="artigo_numero"]', elements.legalForm).value = item.artigo_numero || item.artigo || "";
    query('[name="artigo_descricao"]', elements.legalForm).value = item.artigo_descricao || item.descricao || "";
    query('[name="inciso_numero"]', elements.legalForm).value = item.inciso_numero || "";
    query('[name="inciso_descricao"]', elements.legalForm).value = item.inciso_descricao || "";
    query('[name="alinea_identificador"]', elements.legalForm).value = item.alinea_identificador || "";
    query('[name="alinea_descricao"]', elements.legalForm).value = item.alinea_descricao || "";
    elements.legalSubmitLabel.textContent = "Salvar alteracoes";
    elements.legalCancel.hidden = false;
    const details = query("details", elements.legalForm);
    if (details) {
        details.open = Boolean(item.inciso_numero || item.alinea_identificador);
    }
}

function renderLegalTable() {
    elements.legalTableBody.innerHTML = "";
    if (!state.legalItems.length) {
        const row = createElement("tr");
        const cell = createElement("td", "", "Nenhuma referencia cadastrada.");
        cell.colSpan = 5;
        row.appendChild(cell);
        elements.legalTableBody.appendChild(row);
        return;
    }

    state.legalItems.forEach((item) => {
        const row = createElement("tr");
        row.appendChild(createElement("td", "", normalizeText(item.tipo, "Artigo")));
        row.appendChild(createElement("td", "", normalizeText(item.lei_nome, "Base legal")));
        row.appendChild(createElement("td", "", normalizeText(item.artigo, item.artigo_numero || "Sem referencia")));

        const statusCell = createElement("td");
        statusCell.appendChild(createBadge(boolValue(item.ativo) ? "Ativo" : "Inativo", boolValue(item.ativo) ? "ui-badge--success" : "ui-badge--info"));
        row.appendChild(statusCell);

        const actionsCell = createElement("td");
        const actions = createElement("div", "coordenacao-table__actions");
        actions.appendChild(createActionButton("Editar", {
            onClick: () => {
                fillLegalForm(item);
                elements.legalForm.scrollIntoView({ behavior: "smooth", block: "start" });
            },
        }));
        actions.appendChild(createActionButton(boolValue(item.ativo) ? "Inativar" : "Ativar", {
            onClick: () => {
                toggleLegalStatus(item).catch((error) => {
                    setFeedback(elements.legalFeedback, error.message || "Nao foi possivel atualizar a referencia.", "error");
                });
            },
        }));
        actionsCell.appendChild(actions);
        row.appendChild(actionsCell);

        elements.legalTableBody.appendChild(row);
    });
}

async function loadLegalItems() {
    const items = await window.AppApi.fetchJson("/regimento-itens?incluir_inativos=true", { headers });
    state.legalItems = Array.isArray(items) ? items : [];
    renderLegalTable();
}

async function submitLegalForm(event) {
    event.preventDefault();
    const itemId = Number(query('[name="item_id"]', elements.legalForm).value || 0);
    const payload = legalFormPayload();
    const url = itemId > 0 ? `/regimento-itens/${itemId}` : "/regimento-itens";
    const method = itemId > 0 ? "PUT" : "POST";

    await window.AppApi.fetchJson(url, {
        method,
        headers: headersJson,
        body: JSON.stringify(payload),
    });

    setFeedback(elements.legalFeedback, itemId > 0 ? "Referencia atualizada com sucesso." : "Referencia criada com sucesso.", "success");
    resetLegalForm();
    await loadLegalItems();
}

async function toggleLegalStatus(item) {
    await window.AppApi.fetchJson(`/regimento-itens/${item.id}/status`, {
        method: "PUT",
        headers: headersJson,
        body: JSON.stringify({ ativo: !boolValue(item.ativo) }),
    });
    setFeedback(elements.legalFeedback, "Status da referencia atualizado.", "success");
    await loadLegalItems();
}

function resetStudentForm() {
    elements.studentForm.reset();
    query('[name="id"]', elements.studentForm).value = "";
    elements.studentSubmitLabel.textContent = "Salvar estudante";
    elements.studentCancel.hidden = true;
    setFeedback(elements.studentFeedback);
}

function fillStudentForm(student) {
    query('[name="id"]', elements.studentForm).value = String(student.id);
    query('[name="nome"]', elements.studentForm).value = student.nome || "";
    query('[name="turma_id"]', elements.studentForm).value = String(student.turma_id || "");
    query('[name="ativo"]', elements.studentForm).checked = boolValue(student.ativo);
    elements.studentSubmitLabel.textContent = "Salvar alteracoes";
    elements.studentCancel.hidden = false;
}

function renderStudents() {
    elements.studentTableBody.innerHTML = "";
    if (!state.students.length) {
        const row = createElement("tr");
        const cell = createElement("td", "", "Nenhum estudante encontrado.");
        cell.colSpan = 4;
        row.appendChild(cell);
        elements.studentTableBody.appendChild(row);
        return;
    }

    state.students.forEach((student) => {
        const row = createElement("tr");
        row.appendChild(createElement("td", "", student.nome));
        row.appendChild(createElement("td", "", student.turma_nome || "Sem turma"));

        const statusCell = createElement("td");
        statusCell.appendChild(createBadge(boolValue(student.ativo) ? "Ativo" : "Inativo", boolValue(student.ativo) ? "ui-badge--success" : "ui-badge--info"));
        row.appendChild(statusCell);

        const actionsCell = createElement("td");
        const actions = createElement("div", "coordenacao-table__actions");
        actions.appendChild(createActionButton("Editar", {
            onClick: () => {
                fillStudentForm(student);
                elements.studentForm.scrollIntoView({ behavior: "smooth", block: "start" });
            },
        }));
        actions.appendChild(createActionButton(boolValue(student.ativo) ? "Inativar" : "Ativar", {
            onClick: () => {
                toggleStudentStatus(student).catch((error) => {
                    setFeedback(elements.studentFeedback, error.message || "Nao foi possivel atualizar o estudante.", "error");
                });
            },
        }));
        actionsCell.appendChild(actions);
        row.appendChild(actionsCell);
        elements.studentTableBody.appendChild(row);
    });
}

async function loadStudents() {
    const params = serializeForm(elements.studentSearchForm);
    params.set("incluir_inativos", "true");
    const items = await window.AppApi.fetchJson(`/estudantes?${params.toString()}`, { headers });
    state.students = Array.isArray(items) ? items : [];
    renderStudents();
}

async function submitStudentForm(event) {
    event.preventDefault();
    const formData = new FormData(elements.studentForm);
    const id = Number(formData.get("id") || 0);
    const payload = {
        nome: normalizeText(formData.get("nome")),
        turma_id: Number(formData.get("turma_id") || 0),
        ativo: formData.get("ativo") === "on",
    };
    const url = id > 0 ? `/estudantes/${id}` : "/estudantes";
    const method = id > 0 ? "PUT" : "POST";

    await window.AppApi.fetchJson(url, {
        method,
        headers: headersJson,
        body: JSON.stringify(payload),
    });

    setFeedback(elements.studentFeedback, id > 0 ? "Estudante atualizado com sucesso." : "Estudante criado com sucesso.", "success");
    resetStudentForm();
    await loadStudents();
}

async function toggleStudentStatus(student) {
    await window.AppApi.fetchJson(`/estudantes/${student.id}/status`, {
        method: "PUT",
        headers: headersJson,
        body: JSON.stringify({ ativo: !boolValue(student.ativo) }),
    });
    setFeedback(elements.studentFeedback, "Status do estudante atualizado.", "success");
    await loadStudents();
}

function renderReports() {
    const byStudent = new Map();
    const byClass = new Map();

    state.occurrences.forEach((item) => {
        const nameKey = normalizeText(item.nome_estudante, "__sem_nome__");
        byStudent.set(nameKey, (byStudent.get(nameKey) || 0) + 1);
        const classKey = normalizeText(item.turma_nome, "Sem turma");
        byClass.set(classKey, (byClass.get(classKey) || 0) + 1);
    });

    const repeatedStudents = Array.from(byStudent.values()).filter((count) => count > 1).length;
    const repeatRate = byStudent.size ? Math.round((repeatedStudents / byStudent.size) * 100) : 0;
    elements.reportRepeatRate.textContent = `${repeatRate}%`;

    let topClass = "-";
    let topClassCount = 0;
    byClass.forEach((count, className) => {
        if (count > topClassCount) {
            topClass = className;
            topClassCount = count;
        }
    });
    elements.reportTopClass.textContent = topClass;

    const completed = state.preRegistrations.filter((item) => item.completed_at && item.created_at);
    if (!completed.length) {
        elements.reportCompletionTime.textContent = "-";
        return;
    }

    const totalDays = completed.reduce((sum, item) => {
        const created = new Date(String(item.created_at).replace(" ", "T") + "Z");
        const finished = new Date(String(item.completed_at).replace(" ", "T") + "Z");
        if (Number.isNaN(created.getTime()) || Number.isNaN(finished.getTime())) return sum;
        return sum + ((finished.getTime() - created.getTime()) / 86_400_000);
    }, 0);
    elements.reportCompletionTime.textContent = formatDurationDays(totalDays / completed.length);
}

function renderPreRegistrationCount() {
    if (!elements.preRegistrationCount) return;
    const pendingCount = state.preRegistrations.filter((item) => item.status === "pending").length;
    elements.preRegistrationCount.textContent = String(pendingCount);
    elements.preRegistrationCount.hidden = pendingCount <= 0;
}

function preRegistrationTitle(item) {
    const students = Array.isArray(item.students) ? item.students : [];
    if (students.length) {
        return students.map((student) => student.name).join(", ");
    }
    return normalizeText(item.student_name, "Pre-registro");
}

function preRegistrationMetaLines(item, { includeProfessor = false } = {}) {
    const students = Array.isArray(item.students) ? item.students : [];
    const reasons = Array.isArray(item.reasons) ? item.reasons : [];
    const classes = [...new Set(students.map((student) => normalizeText(student.class_name)).filter(Boolean))];
    return [
        classes.length ? `Turma(s): ${classes.join(", ")}` : normalizeText(item.class_name) ? `Turma: ${item.class_name}` : "",
        reasons.length ? `Motivo(s): ${reasons.map((reason) => reason.name).join(", ")}` : normalizeText(item.reason_name) ? `Motivo: ${item.reason_name}` : "",
        item.discipline ? `Disciplina: ${item.discipline}` : "",
        item.lesson ? `Aula: ${item.lesson}` : "",
        RESPONSIBLE_CONTACT_LABELS[item.responsible_contact] || "",
        includeProfessor ? `Professor: ${normalizeText(item.professor_name, "Nao informado")}` : "",
        `Registrado em: ${formatDateTime(item.occurred_at || item.created_at)}`,
    ].filter(Boolean);
}

function renderTeacherPreRegistrations() {
    elements.teacherPreRegistrations.innerHTML = "";
    if (!state.preRegistrations.length) {
        elements.teacherPreRegistrations.appendChild(
            createElement("p", "coordenacao-empty-state", "Nenhum pre-registro enviado ainda.")
        );
        return;
    }

    state.preRegistrations.forEach((item) => {
        const card = createElement("article", "coordenacao-queue-item");
        const copy = createElement("div");
        copy.appendChild(createElement("strong", "", preRegistrationTitle(item)));
        preRegistrationMetaLines(item).forEach((line) => {
            copy.appendChild(createElement("p", "", line));
        });
        card.appendChild(copy);
        card.appendChild(createBadge(
            PRE_REGISTRATION_STATUS_LABELS[item.status] || item.status,
            statusBadgeVariant(item.status)
        ));
        elements.teacherPreRegistrations.appendChild(card);
    });
}

function renderManagerQueue() {
    elements.preRegistrationQueue.innerHTML = "";
    const pending = state.preRegistrations.filter((item) => item.status === "pending");

    if (!pending.length) {
        elements.preRegistrationQueue.appendChild(
            createElement("p", "coordenacao-empty-state", "Nenhuma pendencia enviada pelos professores.")
        );
        return;
    }

    pending.forEach((item) => {
        const card = createElement("article", "coordenacao-queue-item");
        const copy = createElement("div");
        copy.appendChild(createElement("strong", "", preRegistrationTitle(item)));
        preRegistrationMetaLines(item, { includeProfessor: true }).forEach((line) => {
            copy.appendChild(createElement("p", "", line));
        });

        const actions = createElement("div", "coordenacao-table__actions");
        actions.appendChild(createBadge("Pendente", "ui-badge--warning"));
        const queueReference = normalizeText(
            Array.isArray(item.students) && item.students.length === 1
                ? item.students[0]?.name
                : item.student_name
        );
        actions.appendChild(createActionButton(queueReference ? "Ver historico" : "Abrir ocorrencias", {
            variant: "subtle",
            onClick: () => {
                if (queueReference) {
                    filterOccurrencesByReference(queueReference);
                    return;
                }
                setPanel("ocorrencias");
            },
        }));

        card.append(copy, actions);
        elements.preRegistrationQueue.appendChild(card);
    });
}

function renderReasonOptions() {
    if (elements.teacherReasons) {
        elements.teacherReasons.innerHTML = "";
        const reasons = (state.preRegistrationContext?.reasons || []).filter((item) => boolValue(item.active));
        if (!reasons.length) {
            elements.teacherReasons.appendChild(
                createElement("p", "coordenacao-empty-state", "Nenhum motivo ativo disponivel.")
            );
        } else {
            reasons.forEach((reason) => {
                const label = createElement("label");
                const input = document.createElement("input");
                input.type = "checkbox";
                input.name = "reason_id";
                input.value = String(reason.id);
                const text = createElement("span", "", reason.name);
                label.append(input, text);
                elements.teacherReasons.appendChild(label);
            });
        }
    }

    if (elements.reasonList) {
        elements.reasonList.innerHTML = "";
        const reasons = state.preRegistrationContext?.reasons || [];
        if (!reasons.length) {
            elements.reasonList.appendChild(
                createElement("p", "coordenacao-empty-state", "Nenhum motivo cadastrado.")
            );
            return;
        }

        reasons.forEach((reason) => {
            const chip = createElement("div");
            chip.dataset.inactive = boolValue(reason.active) ? "false" : "true";
            chip.appendChild(createElement("span", "", reason.name));
            chip.appendChild(createActionButton(boolValue(reason.active) ? "Inativar" : "Ativar", {
                onClick: () => {
                    toggleReason(reason).catch((error) => {
                        setFeedback(elements.reasonFeedback, error.message || "Nao foi possivel atualizar o motivo.", "error");
                    });
                },
            }));
            elements.reasonList.appendChild(chip);
        });
    }
}

function renderTeacherSelectedStudents() {
    elements.teacherSelectedStudents.innerHTML = "";
    if (!state.teacherSelectedStudents.length) {
        elements.teacherSelectedStudents.appendChild(
            createElement("p", "coordenacao-empty-state", "Nenhum estudante selecionado.")
        );
        return;
    }

    state.teacherSelectedStudents.forEach((student) => {
        const item = createElement("div", "coordenacao-selection-item");
        const copy = createElement("div");
        copy.appendChild(createElement("strong", "", student.nome));
        copy.appendChild(createElement("span", "", student.turma_nome || "Sem turma"));
        item.appendChild(copy);
        item.appendChild(createActionButton("Remover", {
            onClick: () => {
                state.teacherSelectedStudents = state.teacherSelectedStudents.filter(
                    (selected) => Number(selected.id) !== Number(student.id)
                );
                renderTeacherSelectedStudents();
            },
        }));
        elements.teacherSelectedStudents.appendChild(item);
    });
}

function renderTeacherStudentResults(items) {
    elements.teacherStudentResults.innerHTML = "";
    if (!items.length) {
        elements.teacherStudentResults.appendChild(
            createElement("p", "coordenacao-empty-state", "Nenhum estudante encontrado.")
        );
    } else {
        items.forEach((student) => {
            const button = createElement("button", "coordenacao-autocomplete-item");
            button.type = "button";
            const copy = createElement("div");
            copy.appendChild(createElement("strong", "", student.nome));
            copy.appendChild(createElement("span", "", student.turma_nome || "Sem turma"));
            button.appendChild(copy);
            button.addEventListener("click", () => {
                if (!state.teacherSelectedStudents.some((item) => Number(item.id) === Number(student.id))) {
                    state.teacherSelectedStudents.push(student);
                    renderTeacherSelectedStudents();
                }
                elements.teacherStudentSearch.value = "";
                elements.teacherStudentResults.hidden = true;
            });
            elements.teacherStudentResults.appendChild(button);
        });
    }
    elements.teacherStudentResults.hidden = false;
}

async function searchTeacherStudents(term = "") {
    const params = new URLSearchParams({
        q: normalizeText(term),
        limit: "20",
    });
    const items = await window.AppApi.fetchJson(`/occurrences/students?${params.toString()}`, { headers });
    renderTeacherStudentResults(Array.isArray(items) ? items : []);
}

async function loadPreRegistrationContext() {
    const context = await window.AppApi.fetchJson("/occurrences/context", { headers });
    state.preRegistrationContext = context || { reasons: [] };
    renderReasonOptions();
}

async function loadPreRegistrations() {
    const items = await window.AppApi.fetchJson("/occurrences/pre-registrations", { headers });
    state.preRegistrations = Array.isArray(items) ? items : [];
    renderPreRegistrationCount();
    renderReports();
    if (state.isManager) {
        renderManagerQueue();
    } else {
        renderTeacherPreRegistrations();
    }
}

async function submitTeacherPreRegistration(event) {
    event.preventDefault();
    const reasonIds = Array.from(
        elements.teacherPreRegistrationForm.querySelectorAll('input[name="reason_id"]:checked')
    ).map((input) => Number(input.value));
    const contact = elements.teacherPreRegistrationForm.querySelector('input[name="responsible_contact"]:checked')?.value || "none";
    const studentIds = state.teacherSelectedStudents.map((student) => Number(student.id));

    if (!studentIds.length) {
        throw new Error("Selecione pelo menos um estudante.");
    }
    if (!reasonIds.length) {
        throw new Error("Selecione pelo menos um motivo.");
    }

    await window.AppApi.fetchJson("/occurrences/pre-registrations", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            student_ids: studentIds,
            reason_ids: reasonIds,
            responsible_contact: contact,
        }),
    });

    elements.teacherPreRegistrationForm.reset();
    state.teacherSelectedStudents = [];
    renderTeacherSelectedStudents();
    setFeedback(elements.teacherFeedback, "Pre-registro enviado para a coordenacao.", "success");
    await loadPreRegistrations();
}

async function submitReasonForm(event) {
    event.preventDefault();
    const formData = new FormData(elements.reasonForm);
    const name = normalizeText(formData.get("motivo"));
    await window.AppApi.fetchJson("/occurrences/reasons", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({ name }),
    });
    elements.reasonForm.reset();
    setFeedback(elements.reasonFeedback, "Motivo cadastrado com sucesso.", "success");
    await loadPreRegistrationContext();
}

async function toggleReason(reason) {
    await window.AppApi.fetchJson(`/occurrences/reasons/${reason.id}`, {
        method: "PATCH",
        headers: headersJson,
        body: JSON.stringify({ active: !boolValue(reason.active) }),
    });
    setFeedback(elements.reasonFeedback, "Motivo atualizado com sucesso.", "success");
    await loadPreRegistrationContext();
}

function registerGeneralEvents() {
    elements.logout?.addEventListener("click", () => {
        window.AppAuth?.encerrarSessao?.();
    });

    [elements.occurrenceCreateAction, elements.primaryAction, elements.fabAction].forEach((action) => {
        action?.addEventListener("click", (event) => {
            const target = action.dataset.panelTarget;
            if (!target) return;
            event.preventDefault();
            setPanel(target);
        });
    });

    elements.panelLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            event.preventDefault();
            setPanel(link.dataset.panelLink);
        });
    });

    elements.searchForm?.addEventListener("submit", (event) => {
        event.preventDefault();
        const queryValue = normalizeText(elements.searchInput.value);
        if (state.isManager) {
            setPanel("ocorrencias");
            const field = query('[name="nome_estudante"]', elements.occurrenceFilters);
            field.value = queryValue;
            loadOccurrences().catch((error) => {
                setFeedback(elements.occurrenceFeedback, error.message || "Nao foi possivel filtrar os registros.", "error");
            });
            return;
        }
        setPanel("fluxo-professor");
        elements.teacherStudentSearch.value = queryValue;
        searchTeacherStudents(queryValue).catch((error) => {
            setFeedback(elements.teacherFeedback, error.message || "Nao foi possivel buscar estudantes.", "error");
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-teacher-student-results]") && !event.target.closest("[data-teacher-student-search]")) {
            elements.teacherStudentResults.hidden = true;
        }
    });

    query("[data-top-navbar-refresh]")?.addEventListener("click", () => {
        refreshCurrentPanel().catch((error) => {
            setFeedback(
                feedbackTargetForCurrentPanel(),
                error.message || "Nao foi possivel atualizar os dados do modulo.",
                "error"
            );
        });
    });

    query("[data-top-navbar-profile]")?.addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    elements.occurrenceModalClose?.addEventListener("click", () => {
        closeOccurrenceModal();
    });

    elements.occurrenceModal?.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeOccurrenceModal();
    });

    elements.occurrenceModal?.addEventListener("click", (event) => {
        if (event.target === elements.occurrenceModal) {
            closeOccurrenceModal();
        }
    });
}

function registerManagerEvents() {
    elements.occurrenceFilters?.addEventListener("submit", (event) => {
        event.preventDefault();
        loadOccurrences().catch((error) => {
            setFeedback(elements.occurrenceFeedback, error.message || "Nao foi possivel carregar as ocorrencias.", "error");
        });
    });

    elements.clearOccurrenceFilters?.addEventListener("click", () => {
        elements.occurrenceFilters.reset();
        loadOccurrences().catch((error) => {
            setFeedback(elements.occurrenceFeedback, error.message || "Nao foi possivel limpar os filtros.", "error");
        });
    });

    elements.legalForm?.addEventListener("submit", (event) => {
        submitLegalForm(event).catch((error) => {
            setFeedback(elements.legalFeedback, error.message || "Nao foi possivel salvar a referencia.", "error");
        });
    });

    elements.legalCancel?.addEventListener("click", () => {
        resetLegalForm();
    });

    elements.studentForm?.addEventListener("submit", (event) => {
        submitStudentForm(event).catch((error) => {
            setFeedback(elements.studentFeedback, error.message || "Nao foi possivel salvar o estudante.", "error");
        });
    });

    elements.studentCancel?.addEventListener("click", () => {
        resetStudentForm();
    });

    elements.studentSearchForm?.addEventListener("submit", (event) => {
        event.preventDefault();
        loadStudents().catch((error) => {
            setFeedback(elements.studentFeedback, error.message || "Nao foi possivel carregar os estudantes.", "error");
        });
    });

    elements.reasonForm?.addEventListener("submit", (event) => {
        submitReasonForm(event).catch((error) => {
            setFeedback(elements.reasonFeedback, error.message || "Nao foi possivel salvar o motivo.", "error");
        });
    });
}

function registerTeacherEvents() {
    renderTeacherSelectedStudents();

    elements.teacherPreRegistrationForm?.addEventListener("submit", (event) => {
        submitTeacherPreRegistration(event).catch((error) => {
            setFeedback(elements.teacherFeedback, error.message || "Nao foi possivel enviar o pre-registro.", "error");
        });
    });

    elements.teacherStudentSearch?.addEventListener("input", () => {
        window.clearTimeout(state.teacherSearchTimer);
        state.teacherSearchTimer = window.setTimeout(() => {
            searchTeacherStudents(elements.teacherStudentSearch.value).catch((error) => {
                setFeedback(elements.teacherFeedback, error.message || "Nao foi possivel buscar estudantes.", "error");
            });
        }, SEARCH_DEBOUNCE_MS);
    });

    elements.teacherStudentSearch?.addEventListener("focus", () => {
        searchTeacherStudents(elements.teacherStudentSearch.value).catch((error) => {
            setFeedback(elements.teacherFeedback, error.message || "Nao foi possivel buscar estudantes.", "error");
        });
    });
}

async function bootstrapManager() {
    state.occurrenceContext = await window.AppApi.fetchJson("/ocorrencias/opcoes", { headers });
    populateManagerFilters();
    await Promise.all([
        loadOccurrences(),
        loadLegalItems(),
        loadStudents(),
        loadPreRegistrationContext(),
        loadPreRegistrations(),
    ]);
}

async function bootstrapTeacher() {
    await Promise.all([
        loadPreRegistrationContext(),
        loadPreRegistrations(),
    ]);
}

async function init() {
    registerGeneralEvents();

    state.user = await window.AppAuth.carregarUsuarioAtual({ forcar: true });
    const allowedModules = window.AppAuth?.modulosPermitidos?.(state.user) || new Set();
    if (!allowedModules.has("coordenacao")) {
        window.location.href = "/servicos";
        return;
    }

    state.isTeacher = Boolean(window.AppAuth?.usuarioEhProfessor?.(state.user));
    state.isManager = !state.isTeacher;
    renderRoleShell();
    const initialPanel = window.location.hash.slice(1) || (state.isManager ? "ocorrencias" : "fluxo-professor");
    setPanel(initialPanel, { updateHash: false });

    if (state.isManager) {
        registerManagerEvents();
        await bootstrapManager();
    } else {
        registerTeacherEvents();
        await bootstrapTeacher();
    }
}

init().catch((error) => {
    const message = error?.message || "Nao foi possivel carregar o modulo de coordenacao.";
    if (state.isManager) {
        setFeedback(elements.occurrenceFeedback, message, "error");
    } else {
        setFeedback(elements.teacherFeedback, message, "error");
    }
});

window.SuiteEscolarV2 = {
    ...(window.SuiteEscolarV2 || {}),
    setActiveSideNav: setPanel,
};
