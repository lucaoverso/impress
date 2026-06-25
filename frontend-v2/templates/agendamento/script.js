const searchForm = document.querySelector("[data-top-navbar-search]");
const sideNavLinks = Array.from(document.querySelectorAll(".side-navbar__link[href^='#']"));
const sideNavPrimaryAction = document.querySelector("[data-side-nav-primary]");
const sideNavPanels = sideNavLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

const feedback = document.querySelector("[data-booking-feedback]");
const stepPanels = Array.from(document.querySelectorAll("[data-booking-step-panel]"));
const stepper = document.querySelector("[data-booking-stepper]");
const stepperItems = Array.from(document.querySelectorAll("[data-stepper-item]"));
const stage = document.querySelector("[data-booking-stage]");
const stageBreadcrumbs = document.querySelector("[data-booking-stage-breadcrumbs]");
const stageCopy = document.querySelector("[data-booking-stage-copy]");
const stageTitle = document.querySelector("[data-booking-stage-title]");
const stageSubtitle = document.querySelector("[data-booking-stage-subtitle]");
const backButton = document.querySelector("[data-booking-back]");
const nextButton = document.querySelector("[data-booking-next]");
const equipmentControls = Array.from(document.querySelectorAll("[data-equipment-control]"));
const descriptionField = document.querySelector("[data-booking-description]");
const notesField = document.querySelector("[data-booking-notes]");
const extraControls = Array.from(document.querySelectorAll("[data-booking-extra]"));
const dayBoard = document.querySelector("[data-booking-day-board]");
const dayTitle = document.querySelector("[data-booking-day-title]");
const calendarGrid = document.querySelector("[data-calendar-grid]");
const calendarMonthLabel = document.querySelector("[data-calendar-month]");
const calendarNavButtons = Array.from(document.querySelectorAll("[data-calendar-nav]"));
const slotGroups = document.querySelector("[data-booking-slot-groups]");
const slotTitle = document.querySelector("[data-booking-slot-title]");

const bookingSummaries = {
    slotEquipment: document.querySelector("[data-booking-slot-equipment]"),
};

const reviewFields = {
    equipment: document.querySelector("[data-review-equipment]"),
    equipmentStatus: document.querySelector("[data-review-equipment-status]"),
    date: document.querySelector("[data-review-date]"),
    month: document.querySelector("[data-review-month]"),
    day: document.querySelector("[data-review-day]"),
    weekday: document.querySelector("[data-review-weekday]"),
    slot: document.querySelector("[data-review-slot]"),
    extras: document.querySelector("[data-review-extras]"),
    description: document.querySelector("[data-review-description]"),
    notes: document.querySelector("[data-review-notes]"),
};

const equipmentCatalog = {
    projector: {
        name: "Projetor",
        reviewName: "Projetor Multimídia Epson",
        status: "Disponível",
        tone: "success",
        reservations: {
            "2026-10-07": [
                { turn: "Matutino", period: "1ª aula", location: "Sala de tecnologia", owner: "Prof. Kleber" },
                { turn: "Matutino", period: "2ª aula", location: "Sala 14", owner: "Profa. Ana Paula" },
                { turn: "Vespertino", period: "4ª aula", location: "Auditório", owner: "Prof. Marcio" },
            ],
            "2026-10-08": [
                { turn: "Matutino", period: "2ª aula", location: "Sala 21", owner: "Prof. Victor" },
            ],
            "2026-11-04": [
                { turn: "Matutino", period: "1ª aula", location: "Laboratório 1", owner: "Profa. Juliana" },
            ],
        },
    },
    notebook: {
        name: "Notebook",
        reviewName: "Notebook Dell Educacional",
        status: "Disponível",
        tone: "success",
        reservations: {
            "2026-10-07": [
                { turn: "Matutino", period: "1ª aula", location: "Laboratório 2", owner: "Prof. Bruno" },
                { turn: "Vespertino", period: "5ª aula", location: "Sala maker", owner: "Profa. Camila" },
            ],
            "2026-10-09": [
                { turn: "Matutino", period: "3ª aula", location: "Sala 7", owner: "Profa. Renata" },
            ],
        },
    },
    speaker: {
        name: "Caixa de som",
        reviewName: "Caixa de Som Portátil",
        status: "Limitado",
        tone: "warning",
        reservations: {
            "2026-10-07": [
                { turn: "Matutino", period: "3ª aula", location: "Quadra coberta", owner: "Prof. Danilo" },
            ],
            "2026-10-15": [
                { turn: "Matutino", period: "1ª aula", location: "Pátio central", owner: "Prof. Sergio" },
            ],
        },
    },
    lab: {
        name: "Laboratório Móvel",
        reviewName: "Laboratório Móvel de Tablets",
        status: "Disponível",
        tone: "success",
        reservations: {
            "2026-10-07": [
                { turn: "Matutino", period: "2ª aula", location: "1º ano B", owner: "Profa. Silvia" },
                { turn: "Vespertino", period: "6ª aula", location: "2º ano A", owner: "Prof. Diego" },
            ],
            "2026-11-06": [
                { turn: "Vespertino", period: "4ª aula", location: "3º ano C", owner: "Prof. Leandro" },
            ],
        },
    },
};

const scheduleData = {
    "2026-10-07": [
        {
            label: "Matutino",
            slots: [
                { id: "2026-10-07-1", name: "1ª aula", time: "07:00 - 07:50", available: false, action: "Indisponível" },
                { id: "2026-10-07-2", name: "2ª aula", time: "07:50 - 08:40", available: true, action: "Selecionado" },
                { id: "2026-10-07-3", name: "3ª aula", time: "09:00 - 09:50", available: true, action: "Reservar" },
            ],
        },
        {
            label: "Vespertino",
            slots: [
                { id: "2026-10-07-4", name: "4ª aula", time: "13:00 - 13:50", available: true, action: "Reservar" },
                { id: "2026-10-07-5", name: "5ª aula", time: "13:50 - 14:40", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-10-08": [
        {
            label: "Matutino",
            slots: [
                { id: "2026-10-08-1", name: "1ª aula", time: "07:00 - 07:50", available: true, action: "Reservar" },
                { id: "2026-10-08-2", name: "2ª aula", time: "07:50 - 08:40", available: true, action: "Reservar" },
            ],
        },
        {
            label: "Vespertino",
            slots: [
                { id: "2026-10-08-3", name: "4ª aula", time: "13:00 - 13:50", available: false, action: "Indisponível" },
                { id: "2026-10-08-4", name: "5ª aula", time: "13:50 - 14:40", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-10-09": [
        {
            label: "Matutino",
            slots: [
                { id: "2026-10-09-1", name: "2ª aula", time: "07:50 - 08:40", available: true, action: "Reservar" },
                { id: "2026-10-09-2", name: "3ª aula", time: "09:00 - 09:50", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-10-14": [
        {
            label: "Vespertino",
            slots: [
                { id: "2026-10-14-1", name: "4ª aula", time: "13:00 - 13:50", available: true, action: "Reservar" },
                { id: "2026-10-14-2", name: "5ª aula", time: "13:50 - 14:40", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-10-15": [
        {
            label: "Matutino",
            slots: [
                { id: "2026-10-15-1", name: "1ª aula", time: "07:00 - 07:50", available: false, action: "Indisponível" },
                { id: "2026-10-15-2", name: "3ª aula", time: "09:00 - 09:50", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-11-04": [
        {
            label: "Matutino",
            slots: [
                { id: "2026-11-04-1", name: "1ª aula", time: "07:00 - 07:50", available: true, action: "Reservar" },
                { id: "2026-11-04-2", name: "2ª aula", time: "07:50 - 08:40", available: true, action: "Reservar" },
            ],
        },
    ],
    "2026-11-06": [
        {
            label: "Vespertino",
            slots: [
                { id: "2026-11-06-1", name: "4ª aula", time: "13:00 - 13:50", available: true, action: "Reservar" },
                { id: "2026-11-06-2", name: "5ª aula", time: "13:50 - 14:40", available: false, action: "Indisponível" },
            ],
        },
    ],
};

const calendarMonths = [
    { year: 2026, month: 9 },
    { year: 2026, month: 10 },
];

const availabilityByDate = Object.fromEntries(
    Object.keys(scheduleData).map((dateKey) => {
        const slots = scheduleData[dateKey].flatMap((group) => group.slots);
        const availableCount = slots.filter((slot) => slot.available).length;
        const unavailableCount = slots.length - availableCount;

        if (availableCount > 0 && unavailableCount > 0) {
            return [dateKey, "limited"];
        }

        return [dateKey, availableCount > 0 ? "available" : "unavailable"];
    }),
);

const state = {
    currentPanel: "calendario",
    currentStep: 1,
    selectedEquipment: "projector",
    selectedDate: "2026-10-07",
    selectedSlotId: "2026-10-07-2",
    monthIndex: 0,
    description: "",
    notes: "",
    extras: [],
};

function preventFrontendOnly(event) {
    event.preventDefault();
}

function setFeedback(message = "", tone = "danger") {
    if (!feedback) return;
    if (!message) {
        feedback.hidden = true;
        feedback.textContent = "";
        feedback.removeAttribute("data-tone");
        return;
    }

    feedback.hidden = false;
    feedback.textContent = message;
    feedback.dataset.tone = tone;
}

function formatLongDate(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    const formatted = date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
    });
    return formatted.replace(/ de ([a-zà-ú])/i, (_, letter) => ` de ${letter.toUpperCase()}`);
}

function formatShortDate(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    const formatted = date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
    });
    return formatted.replace(/ de ([a-zà-ú])/i, (_, letter) => ` de ${letter.toUpperCase()}`);
}

function getDateParts(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    return {
        month: date.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "").toUpperCase(),
        day: String(day).padStart(2, "0"),
        weekday: date.toLocaleDateString("pt-BR", { weekday: "long" }).replace(/^\w/, (letter) => letter.toUpperCase()),
    };
}

function getSelectedSlot() {
    const groups = scheduleData[state.selectedDate] || [];
    for (const group of groups) {
        const match = group.slots.find((slot) => slot.id === state.selectedSlotId);
        if (match) {
            return { ...match, group: group.label };
        }
    }

    return null;
}

function ensureSelectedSlot() {
    const slot = getSelectedSlot();
    if (slot?.available) return;

    const groups = scheduleData[state.selectedDate] || [];
    const nextAvailable = groups.flatMap((group) => group.slots).find((item) => item.available);
    state.selectedSlotId = nextAvailable?.id || "";
}

function renderDayBoard() {
    if (!dayBoard || !dayTitle) return;

    const equipment = equipmentCatalog[state.selectedEquipment];
    const reservations = equipment?.reservations?.[state.selectedDate] || [];
    const grouped = reservations.reduce((accumulator, item) => {
        accumulator[item.turn] ||= [];
        accumulator[item.turn].push(item);
        return accumulator;
    }, {});

    dayTitle.textContent = `Agendamentos do Dia - ${formatShortDate(state.selectedDate)}`;

    if (!reservations.length) {
        dayBoard.innerHTML = '<p class="booking-day-empty">Nenhuma reserva encontrada para este recurso na data selecionada.</p>';
        return;
    }

    dayBoard.innerHTML = Object.entries(grouped)
        .map(([turn, items]) => `
            <section class="booking-day-group" aria-label="${turn}">
                <h3 class="booking-day-group__title">${turn}</h3>
                <div class="booking-day-list">
                    ${items
                        .map(
                            (item) => `
                                <article class="booking-day-item">
                                    <span class="booking-day-item__icon" aria-hidden="true">
                                        <span class="ui-icon">schedule</span>
                                    </span>
                                    <div class="booking-day-item__content">
                                        <strong>${item.period} • ${item.location}</strong>
                                        <span>${item.owner}</span>
                                    </div>
                                </article>
                            `,
                        )
                        .join("")}
                </div>
            </section>
        `)
        .join("");
}

function renderCalendar() {
    if (!calendarGrid || !calendarMonthLabel) return;

    const monthConfig = calendarMonths[state.monthIndex];
    const firstDay = new Date(monthConfig.year, monthConfig.month, 1);
    const startOffset = firstDay.getDay();
    const daysInMonth = new Date(monthConfig.year, monthConfig.month + 1, 0).getDate();

    calendarMonthLabel.textContent = firstDay.toLocaleDateString("pt-BR", {
        month: "long",
        year: "numeric",
    });

    calendarNavButtons.forEach((button) => {
        const isPrev = button.dataset.calendarNav === "prev";
        button.disabled = isPrev ? state.monthIndex === 0 : state.monthIndex === calendarMonths.length - 1;
    });

    const cells = [];
    for (let index = 0; index < startOffset; index += 1) {
        cells.push('<span class="booking-calendar__day is-outside" aria-hidden="true"></span>');
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
        const dateKey = `${monthConfig.year}-${String(monthConfig.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const availability = availabilityByDate[dateKey];
        const selected = dateKey === state.selectedDate;
        const isUnavailable = !availability || availability === "unavailable";
        const classes = [
            "booking-calendar__day",
            selected ? "is-selected" : "",
            availability === "limited" ? "is-limited" : "",
        ]
            .filter(Boolean)
            .join(" ");
        const disabled = isUnavailable ? "disabled" : "";
        const label = !isUnavailable
            ? `Selecionar ${day} de ${calendarMonthLabel.textContent}`
            : `${day} indisponivel`;

        cells.push(
            `<button class="${classes}" type="button" data-calendar-day="${dateKey}" aria-label="${label}" ${disabled}>${day}</button>`,
        );
    }

    calendarGrid.innerHTML = cells.join("");

    calendarGrid.querySelectorAll("[data-calendar-day]").forEach((button) => {
        button.addEventListener("click", () => {
            state.selectedDate = button.dataset.calendarDay;
            ensureSelectedSlot();
            renderCalendar();
            renderSlotGroups();
            renderDayBoard();
            syncSummaries();
            setFeedback("");
        });
    });
}

function renderSlotGroups() {
    if (!slotGroups) return;

    const groups = scheduleData[state.selectedDate] || [];
    const slotDateLabel = formatShortDate(state.selectedDate);
    if (slotTitle) {
        slotTitle.textContent = `Horários para ${slotDateLabel}`;
    }

    slotGroups.innerHTML = groups
        .map(
            (group) => `
                <section class="booking-slot-group" aria-label="${group.label}">
                    <h3 class="booking-slot-group__title">${group.label}</h3>
                    <div class="booking-slot-list">
                        ${group.slots
                            .map((slot) => {
                                const selected = slot.id === state.selectedSlotId;
                                const stateClass = selected ? "is-selected" : slot.available ? "" : "is-unavailable";
                                const toneClass = slot.available ? (selected ? "ui-button--primary" : "") : "ui-button--ghost";
                                const actionLabel = slot.available ? (selected ? "Desfazer" : "Selecionar") : "Indisponível";
                                const periodLabel = slot.name.replace("ª aula", "º");
                                const statusLabel = slot.available
                                    ? selected
                                        ? "Selecionado"
                                        : "Disponível"
                                    : "Ocupado por Prof. João";

                                return `
                                    <article class="booking-slot ${stateClass}">
                                        <div class="booking-slot__meta">
                                            <span class="booking-slot__period">${periodLabel}</span>
                                            <div class="booking-slot__copy">
                                                <strong>${slot.time}</strong>
                                                <span>${statusLabel}</span>
                                            </div>
                                        </div>
                                        <button
                                            class="ui-button booking-slot__action ${toneClass}"
                                            type="button"
                                            data-slot-id="${slot.id}"
                                            ${slot.available ? "" : "disabled"}
                                        >
                                            ${actionLabel}
                                        </button>
                                    </article>
                                `;
                            })
                            .join("")}
                    </div>
                </section>
            `,
        )
        .join("");

    slotGroups.querySelectorAll("[data-slot-id]").forEach((button) => {
        button.addEventListener("click", () => {
            state.selectedSlotId = state.selectedSlotId === button.dataset.slotId ? "" : button.dataset.slotId;
            renderSlotGroups();
            syncSummaries();
            setFeedback("");
        });
    });
}

function syncSummaries() {
    const equipment = equipmentCatalog[state.selectedEquipment];
    const slot = getSelectedSlot();

    if (bookingSummaries.slotEquipment) bookingSummaries.slotEquipment.textContent = equipment?.name || "Recurso";

    if (reviewFields.equipment) reviewFields.equipment.textContent = equipment?.reviewName || equipment?.name || "Recurso";
    if (reviewFields.equipmentStatus) reviewFields.equipmentStatus.textContent = equipment?.status || "Disponível";
    if (reviewFields.date) reviewFields.date.textContent = formatShortDate(state.selectedDate);
    if (reviewFields.month || reviewFields.day || reviewFields.weekday) {
        const dateParts = getDateParts(state.selectedDate);
        if (reviewFields.month) reviewFields.month.textContent = dateParts.month;
        if (reviewFields.day) reviewFields.day.textContent = dateParts.day;
        if (reviewFields.weekday) reviewFields.weekday.textContent = dateParts.weekday;
    }
    if (reviewFields.slot) reviewFields.slot.textContent = slot ? `${slot.name} (${slot.time})` : "Selecione um horário";
    if (reviewFields.description) {
        reviewFields.description.textContent = state.description || "Aguardando preenchimento.";
    }
    if (reviewFields.notes) {
        reviewFields.notes.textContent = state.notes || "Sem observacoes adicionais.";
    }

    if (reviewFields.extras) {
        if (!state.extras.length) {
            reviewFields.extras.innerHTML = '<span class="booking-review__note">Nenhum recurso adicional selecionado.</span>';
        } else {
            reviewFields.extras.innerHTML = state.extras
                .map((item) => `<span class="ui-badge ui-badge--info">${item}</span>`)
                .join("");
        }
    }
}

function validateStep(step) {
    if (step === 1 && !state.selectedEquipment) {
        setFeedback("Selecione um equipamento para continuar.", "danger");
        return false;
    }

    if (step === 2) {
        if (!state.selectedDate || !state.selectedSlotId) {
            setFeedback("Escolha uma data com disponibilidade e um horário para continuar.", "danger");
            return false;
        }
    }

    if (step === 3) {
        state.description = descriptionField?.value.trim() || "";
        state.notes = notesField?.value.trim() || "";
        if (!state.description) {
            setFeedback("Descreva a aula ou atividade para concluir o agendamento.", "danger");
            descriptionField?.focus();
            return false;
        }
    }

    return true;
}

function updateStepUI() {
    const maxStep = stepPanels.length;
    const ratio = maxStep > 1 ? (state.currentStep - 1) / (maxStep - 1) : 0;
    stepper?.style.setProperty("--stepper-progress-ratio", String(ratio));
    if (stepper) stepper.hidden = state.currentStep === 1;

    stepPanels.forEach((panel) => {
        const panelStep = Number(panel.dataset.bookingStepPanel);
        panel.hidden = panelStep !== state.currentStep;
    });

    stepperItems.forEach((item) => {
        const itemStep = Number(item.dataset.stepperItem);
        item.classList.remove("is-complete", "is-upcoming");
        item.removeAttribute("aria-current");

        if (itemStep < state.currentStep) {
            item.classList.add("is-complete");
            const marker = item.querySelector(".stepper__marker");
            if (marker) marker.innerHTML = '<span class="ui-icon" aria-hidden="true">check</span>';
            return;
        }

        const marker = item.querySelector(".stepper__marker");
        if (marker) marker.textContent = String(itemStep);

        if (itemStep === state.currentStep) {
            item.setAttribute("aria-current", "step");
            return;
        }

        item.classList.add("is-upcoming");
    });

    if (backButton) backButton.hidden = state.currentStep === 1;
    if (backButton) backButton.classList.toggle("booking-flow__back-link", state.currentStep === maxStep);
    if (nextButton) {
        nextButton.textContent = state.currentStep === maxStep ? "Confirmar Agendamento" : "Próximo Passo";
    }

    if (stage && stageBreadcrumbs && stageCopy && stageTitle && stageSubtitle) {
        stage.hidden = false;
        stageBreadcrumbs.hidden = true;
        stageCopy.hidden = false;

        if (state.currentStep === 1) {
            stageTitle.textContent = "Agendar Equipamento";
            stageSubtitle.textContent = "Selecione o equipamento que deseja reservar.";
        }

        if (state.currentStep === 2) {
            stageTitle.textContent = "Novo Agendamento";
            stageSubtitle.textContent = "Selecione a data e o horário desejados para o equipamento selecionado.";
        }

        if (state.currentStep === 3) {
            stage.hidden = true;
        }

        if (state.currentStep === 4) {
            stageBreadcrumbs.hidden = false;
            stageCopy.hidden = true;
            stageBreadcrumbs.innerHTML = `
                <span>Dashboard</span>
                <span><span class="ui-icon" aria-hidden="true">chevron_right</span>Equipamentos</span>
                <span><span class="ui-icon" aria-hidden="true">chevron_right</span>Novo Agendamento</span>
            `;
        }
    }
}

function setCurrentStep(nextStep) {
    const boundedStep = Math.min(Math.max(nextStep, 1), stepPanels.length);
    state.currentStep = boundedStep;
    updateStepUI();
    syncSummaries();
}

function setActiveSideNav(targetId) {
    const fallbackId = sideNavLinks[0]?.getAttribute("href")?.slice(1);
    const activePanel = document.getElementById(targetId) || document.getElementById(fallbackId);
    if (!activePanel) return;

    const activePanelId = activePanel.id;
    state.currentPanel = activePanelId;

    sideNavLinks.forEach((link) => {
        const isActive = link.getAttribute("href") === `#${activePanelId}`;
        link.classList.toggle("is-active", isActive);
        if (isActive) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });

    sideNavPanels.forEach((panel) => {
        const isActive = panel.id === activePanelId;
        panel.hidden = !isActive;
        panel.classList.toggle("is-active", isActive);
    });
}

function handleNextAction() {
    const maxStep = stepPanels.length;

    if (!validateStep(state.currentStep)) return;

    state.description = descriptionField?.value.trim() || "";
    state.notes = notesField?.value.trim() || "";
    state.extras = extraControls.filter((control) => control.checked).map((control) => control.dataset.extraLabel);
    syncSummaries();
    setFeedback("");

    if (state.currentStep === maxStep) {
        setFeedback("Resumo confirmado. O próximo passo é conectar a submissão ao backend do módulo de agendamento.", "success");
        document.body.dataset.bookingConfirmed = "true";
        return;
    }

    setCurrentStep(state.currentStep + 1);
}

searchForm?.addEventListener("submit", preventFrontendOnly);

sideNavLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        const targetId = link.getAttribute("href")?.slice(1);
        if (!targetId) return;
        setActiveSideNav(targetId);
        history.replaceState(null, "", `#${targetId}`);
    });
});

sideNavPrimaryAction?.addEventListener("click", (event) => {
    event.preventDefault();
    setActiveSideNav("calendario");
    setCurrentStep(1);
    history.replaceState(null, "", "#calendario");
});

equipmentControls.forEach((control) => {
    control.addEventListener("change", () => {
        state.selectedEquipment = control.value;
        renderDayBoard();
        syncSummaries();
        setFeedback("");
    });
});

calendarNavButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const delta = button.dataset.calendarNav === "next" ? 1 : -1;
        const nextIndex = state.monthIndex + delta;
        if (nextIndex < 0 || nextIndex >= calendarMonths.length) return;
        state.monthIndex = nextIndex;

        const monthConfig = calendarMonths[state.monthIndex];
        const monthPrefix = `${monthConfig.year}-${String(monthConfig.month + 1).padStart(2, "0")}`;
        if (!state.selectedDate.startsWith(monthPrefix)) {
            const nextAvailableDate = Object.keys(scheduleData).find((dateKey) => dateKey.startsWith(monthPrefix));
            if (nextAvailableDate) state.selectedDate = nextAvailableDate;
        }

        ensureSelectedSlot();
        renderCalendar();
        renderSlotGroups();
        renderDayBoard();
        syncSummaries();
        setFeedback("");
    });
});

descriptionField?.addEventListener("input", () => {
    state.description = descriptionField.value.trim();
    syncSummaries();
});

notesField?.addEventListener("input", () => {
    state.notes = notesField.value.trim();
    syncSummaries();
});

extraControls.forEach((control) => {
    control.addEventListener("change", () => {
        state.extras = extraControls.filter((item) => item.checked).map((item) => item.dataset.extraLabel);
        syncSummaries();
    });
});

backButton?.addEventListener("click", () => {
    setFeedback("");
    setCurrentStep(state.currentStep - 1);
});

nextButton?.addEventListener("click", handleNextAction);

document.querySelector("[data-app-logout]")?.addEventListener("click", () => {
    document.body.dataset.logoutRequested = "true";
});

const initialPanelId = location.hash.slice(1) || sideNavLinks[0]?.getAttribute("href")?.slice(1);
if (initialPanelId) setActiveSideNav(initialPanelId);

ensureSelectedSlot();
renderCalendar();
renderSlotGroups();
renderDayBoard();
syncSummaries();
updateStepUI();

window.SuiteEscolarV2 = {
    ...(window.SuiteEscolarV2 || {}),
    setActiveSideNav,
    setCurrentBookingStep: setCurrentStep,
};
