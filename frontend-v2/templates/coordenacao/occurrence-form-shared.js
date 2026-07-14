export const GRAVITY_LABELS = {
    leve: "Falta leve",
    grave: "Falta grave",
    gravissima: "Falta gravissima",
};

const GRAVITY_ORDER = {
    leve: 1,
    grave: 2,
    gravissima: 3,
};

export function normalizeText(value, fallback = "") {
    const text = String(value ?? "").trim();
    return text || fallback;
}

export function boolValue(value) {
    return value === true || value === 1 || value === "1";
}

export function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
}

export function optionLabel(list, value, fallback = "Nao informado") {
    const match = (list || []).find((item) => String(item.id) === String(value));
    return normalizeText(match?.nome || match?.label, fallback);
}

export function populateSelect(select, items, { includeBlank = false, blankLabel = "Selecione" } = {}) {
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

export function createSuggestionTitle(item) {
    return normalizeText(item?.label || item?.nome || item?.name || item?.artigo || item?.referencia);
}

export function createSuggestionDescription(item) {
    return normalizeText(item?.turma_nome || item?.class_name || item?.email || item?.descricao);
}

export function filterLocalSuggestions(items, term, fields = ["label", "nome", "name", "artigo", "descricao"]) {
    const needle = normalizeText(term).toLowerCase();
    return (items || []).filter((item) => {
        if (!needle) return true;
        return fields.some((field) => normalizeText(item?.[field]).toLowerCase().includes(needle));
    }).slice(0, 12);
}

export function renderAutocompleteSuggestions(
    container,
    items,
    onSelect,
    emptyText = "Nenhum resultado encontrado."
) {
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

export function romanToInteger(value) {
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

export function extractLegalReference(item) {
    const articleLabel = normalizeText(item?.artigo);
    let articleNumber = normalizeText(item?.artigo_numero).replace(/^art\.?\s*/i, "");
    let incisoNumber = normalizeText(item?.inciso_numero).toUpperCase();
    if (!articleNumber && articleLabel) {
        const matchArticle = articleLabel.match(/Art\.?\s*([^\s,;:-]+(?:[-A-Za-z0-9.]+)?)/i);
        if (matchArticle?.[1]) {
            articleNumber = normalizeText(matchArticle[1]).replace(/^art\.?\s*/i, "");
        }
    }
    if (!incisoNumber && articleLabel) {
        const matchInciso = articleLabel.match(/(?:inciso\s+([IVXLCDM]+)|-\s*([IVXLCDM]+)\b)/i);
        if (matchInciso?.[1] || matchInciso?.[2]) {
            incisoNumber = normalizeText(matchInciso[1] || matchInciso[2]).toUpperCase();
        }
    }
    return { articleNumber, incisoNumber };
}

export function inferLegalGravityItem(item) {
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

export function selectedItemsByIds(ids, items) {
    const selected = new Set((ids || []).map(Number));
    return (items || []).filter((item) => selected.has(Number(item.id)));
}

export function inferSelectedLegalGravity(ids, items) {
    return selectedItemsByIds(ids, items).reduce((selectedGravity, item) => {
        const itemGravity = inferLegalGravityItem(item);
        return (GRAVITY_ORDER[itemGravity] || 0) > (GRAVITY_ORDER[selectedGravity] || 0)
            ? itemGravity
            : selectedGravity;
    }, "");
}

export function filterStudentRecordActions(actions, currentAction = "") {
    const availableActions = Array.isArray(actions) ? actions : [];
    const currentValue = normalizeText(currentAction);
    const filtered = availableActions.filter((item) => {
        const recordTypes = Array.isArray(item?.tipos_registro) ? item.tipos_registro : [];
        return (recordTypes.length === 0 || recordTypes.includes("estudante")) && !boolValue(item?.legado);
    });
    const current = availableActions.find((item) => normalizeText(item?.id) === currentValue);
    if (current && !filtered.some((item) => normalizeText(item?.id) === currentValue)) {
        return [...filtered, current];
    }
    return filtered;
}

export function findSuggestedAction(actions, gravity) {
    if (!gravity) return null;
    return (actions || []).find((item) => item?.gravidade === gravity) || null;
}

export function availableLegalItems(ids, items) {
    const selected = new Set((ids || []).map(Number));
    return (items || []).filter((item) => boolValue(item?.ativo) && !selected.has(Number(item.id)));
}

export function legalActionHint(
    gravity,
    ids,
    {
        emptyHint = "Selecione a base legal para sugerir automaticamente a acao.",
        unresolvedHint = "Gravidade ainda nao identificada. Escolha a acao manualmente.",
    } = {}
) {
    if (gravity) {
        return `Gravidade automatica: ${GRAVITY_LABELS[gravity] || gravity}. A acao sugerida foi preenchida, mas voce pode altera-la.`;
    }
    return (ids || []).length ? unresolvedHint : emptyHint;
}

export function syncLegalActionSelect({
    select,
    hintElement,
    ids,
    legalItems,
    availableActions,
    preferSuggested = true,
    emptyHint,
    unresolvedHint,
} = {}) {
    if (!select) {
        return { gravity: "", actions: [], suggestedAction: null };
    }
    const currentValue = normalizeText(select.value);
    const gravity = inferSelectedLegalGravity(ids, legalItems);
    const actions = filterStudentRecordActions(availableActions, currentValue);
    const suggestedAction = findSuggestedAction(actions, gravity);

    populateSelect(select, actions, {
        includeBlank: true,
        blankLabel: "Selecione a acao",
    });

    const currentStillAvailable = currentValue
        && actions.some((item) => normalizeText(item?.id) === currentValue);
    if (currentStillAvailable && (!preferSuggested || !gravity)) {
        select.value = currentValue;
    } else if (preferSuggested && suggestedAction) {
        select.value = String(suggestedAction.id);
    }

    if (hintElement) {
        hintElement.textContent = legalActionHint(gravity, ids, { emptyHint, unresolvedHint });
    }

    return { gravity, actions, suggestedAction };
}

export function renderSelectedLegalItems({
    container,
    ids,
    items,
    onRemove,
    emptyText = "Nenhuma base legal vinculada.",
    itemClassName = "coordenacao-create-selected-item",
    removeButtonClassName = "coordenacao-icon-action",
    removeButtonText = "close",
    removeIconClassName = "",
    removeAriaLabel = "Remover base legal",
} = {}) {
    if (!container) return;
    container.innerHTML = "";
    if (!(ids || []).length) {
        container.appendChild(createElement("p", "coordenacao-empty-state", emptyText));
        return;
    }

    const byId = new Map((items || []).map((item) => [Number(item.id), item]));
    (ids || []).forEach((rawId) => {
        const id = Number(rawId);
        const item = byId.get(id);
        const chip = createElement("div", itemClassName);
        chip.appendChild(createElement("span", "", createSuggestionTitle(item) || `Item ${id}`));

        const remove = createElement("button", removeButtonClassName);
        remove.type = "button";
        remove.setAttribute("aria-label", removeAriaLabel);
        if (removeIconClassName) {
            remove.appendChild(createElement("span", removeIconClassName, removeButtonText));
        } else {
            remove.textContent = removeButtonText;
        }
        remove.addEventListener("click", () => onRemove?.(id));
        chip.appendChild(remove);
        container.appendChild(chip);
    });
}
