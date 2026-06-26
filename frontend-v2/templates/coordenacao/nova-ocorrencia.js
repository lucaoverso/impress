const AUTOSAVE_DELAY_MS = 900;
const LATEST_DRAFT_KEY = "coordenacao_latest_occurrence_draft_id";

const GRAVITY_ORDER = {
    leve: 1,
    grave: 2,
    gravissima: 3,
};

const GRAVITY_LABELS = {
    leve: "Falta leve",
    grave: "Falta grave",
    gravissima: "Falta gravissima",
};

const elements = {
    form: document.querySelector("[data-draft-form]"),
    feedback: document.querySelector("[data-draft-feedback]"),
    status: document.querySelector("[data-draft-status]"),
    submit: document.querySelector("[data-draft-submit]"),
    next: document.querySelector("[data-draft-next]"),
    prev: document.querySelector("[data-draft-prev]"),
    discard: document.querySelector("[data-draft-discard]"),
    discardFooter: document.querySelector("[data-draft-discard-footer]"),
    steps: Array.from(document.querySelectorAll("[data-draft-step]")),
    stepIndicators: Array.from(document.querySelectorAll("[data-draft-step-indicator]")),
    studentId: document.querySelector("[data-draft-student-id]"),
    studentSearch: document.querySelector("[data-draft-student-search]"),
    studentResults: document.querySelector("[data-draft-student-results]"),
    classSelect: document.querySelector("[data-draft-class]"),
    professorId: document.querySelector("[data-draft-professor-id]"),
    professorSearch: document.querySelector("[data-draft-professor-search]"),
    professorResults: document.querySelector("[data-draft-professor-results]"),
    disciplineSearch: document.querySelector("[data-draft-discipline-search]"),
    disciplineResults: document.querySelector("[data-draft-discipline-results]"),
    lesson: document.querySelector("[data-draft-lesson]"),
    legalSearch: document.querySelector("[data-draft-legal-search]"),
    legalResults: document.querySelector("[data-draft-legal-results]"),
    legalSelected: document.querySelector("[data-draft-legal-selected]"),
    action: document.querySelector("[data-draft-action]"),
    actionHint: document.querySelector("[data-draft-action-hint]"),
    reviewSummary: document.querySelector("[data-draft-review-summary]"),
    reviewLegal: document.querySelector("[data-draft-review-legal]"),
};

const token = window.AppAuth?.garantirToken?.() || "";
const headers = window.AppAuth?.criarHeadersAuth?.(token) || { Authorization: `Bearer ${token}` };
const headersJson = window.AppAuth?.criarHeadersJsonAuth?.(token) || {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
};

const state = {
    user: null,
    context: null,
    draftId: null,
    legalIds: [],
    saveTimer: null,
    savePromise: null,
    searchTimer: null,
    saving: false,
    currentStep: 1,
    lastSavedPayload: "",
};

function normalizeText(value, fallback = "") {
    const text = String(value ?? "").trim();
    return text || fallback;
}

function boolValue(value) {
    return value === true || value === 1 || value === "1";
}

function setFeedback(message = "", tone = "") {
    if (!elements.feedback) return;
    if (!message) {
        elements.feedback.hidden = true;
        elements.feedback.textContent = "";
        delete elements.feedback.dataset.tone;
        return;
    }
    elements.feedback.hidden = false;
    elements.feedback.textContent = message;
    if (tone) {
        elements.feedback.dataset.tone = tone;
    } else {
        delete elements.feedback.dataset.tone;
    }
}

function setDraftStatus(message) {
    if (elements.status) elements.status.textContent = message;
}

function optionLabel(list, value, fallback = "Nao informado") {
    const match = (list || []).find((item) => String(item.id) === String(value));
    return normalizeText(match?.nome || match?.label, fallback);
}

function formatDate(value) {
    if (!value) return "Nao informada";
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
    });
}

function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

function currentStepControls() {
    const current = elements.steps.find((step) => Number(step.dataset.draftStep) === state.currentStep);
    return Array.from(current?.querySelectorAll("input, select, textarea") || []);
}

function setDraftStep(step) {
    state.currentStep = Math.min(Math.max(Number(step) || 1, 1), 3);
    elements.steps.forEach((section) => {
        section.hidden = Number(section.dataset.draftStep) !== state.currentStep;
    });
    elements.stepIndicators.forEach((indicator) => {
        const indicatorStep = Number(indicator.dataset.draftStepIndicator);
        indicator.classList.toggle("is-active", indicatorStep === state.currentStep);
        indicator.classList.toggle("is-complete", indicatorStep < state.currentStep);
    });
    if (elements.prev) elements.prev.hidden = state.currentStep === 1;
    if (elements.next) elements.next.hidden = state.currentStep === 3;
    if (elements.submit) elements.submit.hidden = state.currentStep !== 3;
    if (state.currentStep === 3) {
        updateActionByLegal({ preferSuggested: true });
        renderReview();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function validateCurrentStep() {
    setFeedback();
    const invalid = currentStepControls().find((control) => !control.checkValidity());
    if (invalid) {
        invalid.reportValidity();
        return false;
    }
    if (state.currentStep === 2 && !state.legalIds.length) {
        setFeedback("Selecione pelo menos uma base legal.", "error");
        elements.legalSearch?.focus();
        return false;
    }
    return true;
}

function nextStep() {
    if (!validateCurrentStep()) return;
    setDraftStep(state.currentStep + 1);
}

function previousStep() {
    setFeedback();
    setDraftStep(state.currentStep - 1);
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
        option.textContent = item.nome || item.label || item.artigo || item.descricao || String(item.id);
        select.appendChild(option);
    });
    if (currentValue && Array.from(select.options).some((option) => option.value === currentValue)) {
        select.value = currentValue;
    }
}

function nowDefaults() {
    const now = new Date();
    return {
        data_ocorrencia: now.toISOString().slice(0, 10),
        horario_ocorrencia: now.toTimeString().slice(0, 5),
    };
}

function populateOptions() {
    populateSelect(elements.classSelect, state.context?.turmas || [], {
        includeBlank: true,
        blankLabel: "Selecione a turma",
    });
    elements.form.elements.quem_assina.value = "responsavel";
    elements.form.elements.status.value = state.context?.status_padrao || "registrado";
    updateLessons();
    updateActionByLegal({ preferSuggested: false });
}

function updateLessons() {
    if (!elements.lesson) return;
    const classId = normalizeText(elements.classSelect?.value);
    const selectedClass = (state.context?.turmas || []).find((item) => String(item.id) === classId);
    const lessons = (selectedClass?.faixas_disponiveis || []).map((lesson) => ({
        id: lesson,
        nome: `${lesson}a aula`,
    }));
    populateSelect(elements.lesson, lessons, {
        includeBlank: true,
        blankLabel: lessons.length ? "Selecione a aula" : "Selecione a turma primeiro",
    });
    elements.lesson.disabled = lessons.length === 0;
}

function romanToInteger(value) {
    const text = normalizeText(value).toUpperCase();
    if (!text) return null;
    const values = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
    let total = 0;
    let previous = 0;
    for (let index = text.length - 1; index >= 0; index -= 1) {
        const current = values[text[index]];
        if (!current) return null;
        if (current < previous) {
            total -= current;
        } else {
            total += current;
            previous = current;
        }
    }
    return total;
}

function extractLegalReference(item) {
    const articleLabel = normalizeText(item?.artigo);
    let articleNumber = normalizeText(item?.artigo_numero).replace(/^art\.?\s*/i, "");
    let incisoNumber = normalizeText(item?.inciso_numero).toUpperCase();
    if (!articleNumber && articleLabel) {
        const matchArticle = articleLabel.match(/Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)/i);
        if (matchArticle?.[1]) articleNumber = normalizeText(matchArticle[1]).replace(/^art\.?\s*/i, "");
    }
    if (!incisoNumber && articleLabel) {
        const matchInciso = articleLabel.match(/(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)/i);
        if (matchInciso?.[1] || matchInciso?.[2]) {
            incisoNumber = normalizeText(matchInciso[1] || matchInciso[2]).toUpperCase();
        }
    }
    return { articleNumber, incisoNumber };
}

function inferLegalGravityItem(item) {
    const { articleNumber, incisoNumber } = extractLegalReference(item);
    if (!articleNumber) return "";
    if (articleNumber === "76") return "leve";
    const incisoValue = romanToInteger(incisoNumber);
    if (articleNumber === "81" || articleNumber === "82") {
        if (incisoValue === 1) return "leve";
        if (incisoValue === 2) return "grave";
        if (incisoValue === 3) return "gravissima";
        return "";
    }
    if (articleNumber !== "77" || !incisoValue) return "";
    if (incisoValue >= 1 && incisoValue <= 7) return "leve";
    if (incisoValue >= 8 && incisoValue <= 13) return "grave";
    if (incisoValue >= 14 && incisoValue <= 26) return "gravissima";
    return "";
}

function selectedLegalItems() {
    const selected = new Set(state.legalIds.map(Number));
    return (state.context?.regimento_itens || []).filter((item) => selected.has(Number(item.id)));
}

function inferGravity() {
    return selectedLegalItems().reduce((selectedGravity, item) => {
        const itemGravity = inferLegalGravityItem(item);
        return (GRAVITY_ORDER[itemGravity] || 0) > (GRAVITY_ORDER[selectedGravity] || 0)
            ? itemGravity
            : selectedGravity;
    }, "");
}

function studentActions(currentAction = "") {
    const actions = Array.isArray(state.context?.acoes_aplicadas) ? state.context.acoes_aplicadas : [];
    const detailed = actions.filter((item) => {
        const recordTypes = Array.isArray(item?.tipos_registro) ? item.tipos_registro : [];
        return (recordTypes.length === 0 || recordTypes.includes("estudante")) && !boolValue(item?.legado);
    });
    const current = actions.find((item) => normalizeText(item?.id) === normalizeText(currentAction));
    if (current && !detailed.some((item) => normalizeText(item?.id) === normalizeText(currentAction))) {
        return [...detailed, current];
    }
    return detailed;
}

function updateActionByLegal({ preferSuggested = true } = {}) {
    if (!elements.action) return;
    const currentValue = normalizeText(elements.action.value);
    const gravity = inferGravity();
    const actions = studentActions(currentValue);
    const suggested = gravity ? actions.find((item) => item?.gravidade === gravity) : null;
    populateSelect(elements.action, actions, {
        includeBlank: true,
        blankLabel: "Selecione a acao",
    });
    const currentStillAvailable = currentValue && actions.some((item) => normalizeText(item.id) === currentValue);
    if (currentStillAvailable && (!preferSuggested || !gravity)) {
        elements.action.value = currentValue;
    } else if (preferSuggested && suggested) {
        elements.action.value = String(suggested.id);
    }
    if (!elements.actionHint) return;
    if (gravity) {
        elements.actionHint.textContent = `Gravidade automatica: ${GRAVITY_LABELS[gravity] || gravity}. A acao sugerida foi preenchida, mas voce pode altera-la.`;
    } else if (state.legalIds.length) {
        elements.actionHint.textContent = "Gravidade ainda nao identificada. Escolha a acao manualmente.";
    } else {
        elements.actionHint.textContent = "Selecione a base legal para sugerir automaticamente a acao.";
    }
    renderReview();
}

function collectPayload() {
    const form = elements.form;
    return {
        tipo_registro: "estudante",
        quem_assina: form.elements.quem_assina.value,
        nome_estudante: normalizeText(form.elements.nome_estudante.value),
        estudante_id: Number(form.elements.estudante_id.value) || null,
        turma_id: Number(form.elements.turma_id.value) || null,
        professor_requerente: normalizeText(form.elements.professor_requerente.value),
        professor_requerente_id: Number(form.elements.professor_requerente_id.value) || null,
        disciplina: normalizeText(form.elements.disciplina.value),
        data_ocorrencia: form.elements.data_ocorrencia.value,
        aula: form.elements.aula.value,
        horario_ocorrencia: form.elements.horario_ocorrencia.value,
        descricao: normalizeText(form.elements.descricao.value),
        regimento_item_ids: state.legalIds,
        acao_aplicada: form.elements.acao_aplicada.value,
        status: form.elements.status.value,
    };
}

function reviewRow(icon, label, value, detail = "") {
    const row = createElement("div", "coordenacao-draft-review-row");
    row.appendChild(createElement("span", "ui-icon", icon));
    const content = createElement("div");
    content.appendChild(createElement("small", "", label));
    content.appendChild(createElement("strong", "", normalizeText(value, "Nao informado")));
    if (detail) content.appendChild(createElement("span", "", detail));
    row.appendChild(content);
    return row;
}

function renderReview() {
    const payload = collectPayload();
    if (elements.reviewSummary) {
        elements.reviewSummary.innerHTML = "";
        elements.reviewSummary.appendChild(reviewRow(
            "person",
            "Estudante",
            payload.nome_estudante,
            optionLabel(state.context?.turmas, payload.turma_id, "")
        ));
        elements.reviewSummary.appendChild(reviewRow(
            "event",
            "Data e horario",
            formatDate(payload.data_ocorrencia),
            [payload.horario_ocorrencia, payload.aula ? `${payload.aula}a aula` : ""].filter(Boolean).join(" - ")
        ));
        elements.reviewSummary.appendChild(reviewRow(
            "school",
            "Professor e disciplina",
            payload.disciplina,
            payload.professor_requerente
        ));
    }

    if (!elements.reviewLegal) return;
    elements.reviewLegal.innerHTML = "";
    const items = selectedLegalItems();
    if (!items.length) {
        elements.reviewLegal.appendChild(createElement("p", "coordenacao-empty-state", "Nenhuma base legal vinculada."));
        return;
    }
    items.forEach((item) => {
        const pill = createElement("span", "coordenacao-draft-review-pill");
        pill.appendChild(createElement("span", "ui-icon", "gavel"));
        pill.appendChild(createElement("span", "", createSuggestionTitle(item)));
        elements.reviewLegal.appendChild(pill);
    });
}

function applyPayload(payload = {}) {
    const defaults = nowDefaults();
    elements.form.elements.nome_estudante.value = normalizeText(payload.nome_estudante);
    elements.form.elements.estudante_id.value = normalizeText(payload.estudante_id);
    elements.form.elements.turma_id.value = normalizeText(payload.turma_id);
    updateLessons();
    elements.form.elements.professor_requerente.value = normalizeText(payload.professor_requerente);
    elements.form.elements.professor_requerente_id.value = normalizeText(payload.professor_requerente_id);
    elements.form.elements.disciplina.value = normalizeText(payload.disciplina);
    elements.form.elements.data_ocorrencia.value = normalizeText(payload.data_ocorrencia, defaults.data_ocorrencia);
    elements.form.elements.horario_ocorrencia.value = normalizeText(payload.horario_ocorrencia, defaults.horario_ocorrencia);
    elements.form.elements.aula.value = normalizeText(payload.aula);
    elements.form.elements.descricao.value = normalizeText(payload.descricao);
    elements.form.elements.quem_assina.value = normalizeText(payload.quem_assina, "responsavel");
    elements.form.elements.status.value = normalizeText(payload.status, state.context?.status_padrao || "registrado");
    state.legalIds = Array.isArray(payload.regimento_item_ids) ? payload.regimento_item_ids.map(Number).filter(Boolean) : [];
    renderLegalSelected();
    updateActionByLegal({ preferSuggested: false });
    elements.form.elements.acao_aplicada.value = normalizeText(payload.acao_aplicada);
    renderReview();
    state.lastSavedPayload = JSON.stringify(collectPayload());
}

function createSuggestionTitle(item) {
    return normalizeText(item?.label || item?.nome || item?.name || item?.artigo || item?.referencia);
}

function createSuggestionDescription(item) {
    return normalizeText(item?.turma_nome || item?.class_name || item?.email || item?.descricao);
}

function filterLocalSuggestions(items, term, fields = ["label", "nome", "name", "artigo", "descricao"]) {
    const needle = normalizeText(term).toLowerCase();
    return (items || []).filter((item) => {
        if (!needle) return true;
        return fields.some((field) => normalizeText(item?.[field]).toLowerCase().includes(needle));
    }).slice(0, 12);
}

function renderSuggestions(container, items, onSelect, emptyText = "Nenhum resultado encontrado.") {
    if (!container) return;
    container.innerHTML = "";
    if (!items.length) {
        container.appendChild(createElement("div", "coordenacao-autocomplete-empty", emptyText));
        container.hidden = false;
        return;
    }
    items.forEach((item) => {
        const button = createElement("button", "coordenacao-autocomplete-item");
        button.type = "button";
        button.appendChild(createElement("strong", "", createSuggestionTitle(item)));
        const description = createSuggestionDescription(item);
        if (description) button.appendChild(createElement("span", "", description));
        button.addEventListener("pointerdown", (event) => {
            event.preventDefault();
            onSelect(item);
            container.hidden = true;
        });
        container.appendChild(button);
    });
    container.hidden = false;
}

function hideSuggestions() {
    [elements.studentResults, elements.professorResults, elements.disciplineResults, elements.legalResults].forEach((container) => {
        if (!container) return;
        container.innerHTML = "";
        container.hidden = true;
    });
}

async function searchStudents(term = "") {
    const params = new URLSearchParams({ q: normalizeText(term), limite: "12" });
    const items = await window.AppApi.fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers });
    renderSuggestions(elements.studentResults, Array.isArray(items) ? items : [], (student) => {
        elements.studentId.value = normalizeText(student.id);
        elements.studentSearch.value = normalizeText(student.nome || student.label);
        if (student.turma_id) {
            elements.classSelect.value = String(student.turma_id);
            updateLessons();
        }
        scheduleSave();
    });
}

async function searchProfessors(term = "") {
    const params = new URLSearchParams({ q: normalizeText(term), limite: "12" });
    const items = await window.AppApi.fetchJson(`/ocorrencias/busca/professores?${params.toString()}`, { headers });
    renderSuggestions(elements.professorResults, Array.isArray(items) ? items : [], (professor) => {
        elements.professorId.value = normalizeText(professor.id);
        elements.professorSearch.value = normalizeText(professor.label || professor.nome);
        scheduleSave();
    });
}

function searchDisciplines(term = "") {
    const items = filterLocalSuggestions(state.context?.disciplinas || [], term);
    renderSuggestions(elements.disciplineResults, items, (discipline) => {
        elements.disciplineSearch.value = createSuggestionTitle(discipline);
        scheduleSave();
    }, "Nenhuma disciplina encontrada.");
}

function legalAvailable() {
    const selected = new Set(state.legalIds);
    return (state.context?.regimento_itens || []).filter((item) => boolValue(item.ativo) && !selected.has(Number(item.id)));
}

function searchLegal(term = "") {
    const items = filterLocalSuggestions(legalAvailable(), term, ["artigo", "descricao", "label"]);
    renderSuggestions(elements.legalResults, items, (item) => {
        const id = Number(item?.id || 0);
        if (id > 0 && !state.legalIds.includes(id)) state.legalIds.push(id);
        elements.legalSearch.value = "";
        renderLegalSelected();
        updateActionByLegal();
        scheduleSave();
    }, "Nenhuma base legal encontrada.");
}

function renderLegalSelected() {
    if (!elements.legalSelected) return;
    elements.legalSelected.innerHTML = "";
    if (!state.legalIds.length) {
        elements.legalSelected.appendChild(createElement("p", "coordenacao-empty-state", "Nenhuma base legal vinculada."));
        return;
    }
    const byId = new Map((state.context?.regimento_itens || []).map((item) => [Number(item.id), item]));
    state.legalIds.forEach((id) => {
        const item = byId.get(id);
        const chip = createElement("div", "coordenacao-create-selected-item");
        chip.appendChild(createElement("span", "", createSuggestionTitle(item) || `Item ${id}`));
        const remove = createElement("button", "coordenacao-icon-action", "close");
        remove.type = "button";
        remove.setAttribute("aria-label", "Remover base legal");
        remove.addEventListener("click", () => {
            state.legalIds = state.legalIds.filter((value) => value !== id);
            renderLegalSelected();
            updateActionByLegal();
            scheduleSave();
        });
        chip.appendChild(remove);
        elements.legalSelected.appendChild(chip);
    });
}

async function createDraft() {
    const draft = await window.AppApi.fetchJson("/ocorrencias/rascunhos", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({ payload: collectPayload() }),
    });
    state.draftId = draft.id;
    localStorage.setItem(LATEST_DRAFT_KEY, String(state.draftId));
    const url = new URL(window.location.href);
    url.searchParams.set("rascunho", String(state.draftId));
    window.history.replaceState(null, "", url.toString());
    state.lastSavedPayload = JSON.stringify(collectPayload());
    setDraftStatus("Rascunho salvo agora.");
}

async function loadDraft(draftId) {
    const draft = await window.AppApi.fetchJson(`/ocorrencias/rascunhos/${draftId}`, { headers });
    if (draft.status !== "draft") {
        localStorage.removeItem(LATEST_DRAFT_KEY);
        await createDraft();
        return;
    }
    state.draftId = draft.id;
    localStorage.setItem(LATEST_DRAFT_KEY, String(state.draftId));
    applyPayload(draft.payload || {});
    setDraftStatus(draft.atualizado_em ? `Rascunho salvo em ${draft.atualizado_em}` : "Rascunho carregado.");
}

async function saveDraftNow() {
    if (!state.draftId) return;
    if (state.saving && state.savePromise) return state.savePromise;
    const payload = collectPayload();
    const serialized = JSON.stringify(payload);
    if (serialized === state.lastSavedPayload) return;
    state.saving = true;
    setDraftStatus("Salvando rascunho...");
    state.savePromise = (async () => {
        const draft = await window.AppApi.fetchJson(`/ocorrencias/rascunhos/${state.draftId}`, {
            method: "PATCH",
            headers: headersJson,
            body: JSON.stringify({ payload }),
        });
        state.lastSavedPayload = serialized;
        setDraftStatus(draft.atualizado_em ? `Rascunho salvo em ${draft.atualizado_em}` : "Rascunho salvo.");
    })();
    try {
        await state.savePromise;
    } catch (error) {
        setDraftStatus("Falha ao salvar rascunho.");
        throw error;
    } finally {
        state.saving = false;
        state.savePromise = null;
    }
}

function scheduleSave() {
    renderReview();
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(() => {
        saveDraftNow().catch((error) => {
            setFeedback(error.message || "Nao foi possivel salvar o rascunho.", "error");
        });
    }, AUTOSAVE_DELAY_MS);
}

async function submitDraft(event) {
    event.preventDefault();
    setFeedback();
    if (state.currentStep < 3) {
        nextStep();
        return;
    }
    if (!elements.form.checkValidity()) {
        elements.form.reportValidity();
        return;
    }
    if (!state.legalIds.length) {
        setFeedback("Selecione pelo menos uma base legal.", "error");
        elements.legalSearch?.focus();
        return;
    }
    elements.submit.disabled = true;
    try {
        window.clearTimeout(state.saveTimer);
        await saveDraftNow();
        await saveDraftNow();
        const occurrence = await window.AppApi.fetchJson(`/ocorrencias/rascunhos/${state.draftId}/finalizar`, {
            method: "POST",
            headers: headersJson,
        });
        localStorage.removeItem(LATEST_DRAFT_KEY);
        window.location.href = occurrence?.id ? `/coordenacao#ocorrencias` : "/coordenacao";
    } catch (error) {
        setFeedback(error.message || "Nao foi possivel salvar a ocorrencia.", "error");
    } finally {
        elements.submit.disabled = false;
    }
}

async function discardDraft() {
    if (!state.draftId) {
        window.location.href = "/coordenacao";
        return;
    }
    elements.discard.disabled = true;
    try {
        await window.AppApi.fetchJson(`/ocorrencias/rascunhos/${state.draftId}`, {
            method: "DELETE",
            headers,
        });
        localStorage.removeItem(LATEST_DRAFT_KEY);
        window.location.href = "/coordenacao";
    } catch (error) {
        elements.discard.disabled = false;
        setFeedback(error.message || "Nao foi possivel descartar o rascunho.", "error");
    }
}

function bindEvents() {
    elements.form?.addEventListener("input", scheduleSave);
    elements.form?.addEventListener("change", scheduleSave);
    elements.form?.addEventListener("submit", submitDraft);
    elements.discard?.addEventListener("click", discardDraft);
    elements.discardFooter?.addEventListener("click", discardDraft);
    elements.next?.addEventListener("click", nextStep);
    elements.prev?.addEventListener("click", previousStep);
    elements.classSelect?.addEventListener("change", () => {
        updateLessons();
        scheduleSave();
    });
    elements.studentSearch?.addEventListener("input", () => {
        elements.studentId.value = "";
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => searchStudents(elements.studentSearch.value), 180);
    });
    elements.studentSearch?.addEventListener("focus", () => searchStudents(elements.studentSearch.value));
    elements.professorSearch?.addEventListener("input", () => {
        elements.professorId.value = "";
        window.clearTimeout(state.searchTimer);
        state.searchTimer = window.setTimeout(() => searchProfessors(elements.professorSearch.value), 180);
    });
    elements.professorSearch?.addEventListener("focus", () => searchProfessors(elements.professorSearch.value));
    elements.disciplineSearch?.addEventListener("input", () => searchDisciplines(elements.disciplineSearch.value));
    elements.disciplineSearch?.addEventListener("focus", () => searchDisciplines(elements.disciplineSearch.value));
    elements.legalSearch?.addEventListener("input", () => searchLegal(elements.legalSearch.value));
    elements.legalSearch?.addEventListener("focus", () => searchLegal(elements.legalSearch.value));
    document.addEventListener("pointerdown", (event) => {
        if (!event.target.closest(".ui-field")) hideSuggestions();
    });
}

async function init() {
    state.user = await window.AppAuth.carregarUsuarioAtual({ forcar: true });
    const allowedModules = window.AppAuth?.modulosPermitidos?.(state.user) || new Set();
    if (!allowedModules.has("coordenacao")) {
        window.location.href = "/servicos";
        return;
    }
    if (window.AppAuth?.usuarioEhProfessor?.(state.user)) {
        window.location.href = "/coordenacao#fluxo-professor";
        return;
    }

    state.context = await window.AppApi.fetchJson("/ocorrencias/opcoes", { headers });
    populateOptions();
    applyPayload(nowDefaults());
    bindEvents();

    const draftId = new URLSearchParams(window.location.search).get("rascunho")
        || localStorage.getItem(LATEST_DRAFT_KEY);
    if (draftId) {
        try {
            await loadDraft(draftId);
        } catch (_error) {
            localStorage.removeItem(LATEST_DRAFT_KEY);
            await createDraft();
        }
    } else {
        await createDraft();
    }
    setDraftStep(1);
}

init().catch((error) => {
    setFeedback(error.message || "Nao foi possivel carregar o formulario.", "error");
    setDraftStatus("Erro ao preparar rascunho.");
});
