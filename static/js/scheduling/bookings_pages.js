(function (window, document) {
    const { fetchJson } = window.AppApi;
    const { paraIso, paraDataBr } = window.AppFormat;
    const page = document.body.dataset.schedulingPage;
    const headers = () => window.AppAuth.criarHeadersAuth();
    const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const weekNames = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    const sort = { field: page === "mine" ? "data" : "aula", direction: 1, group: false };
    const sortStorageKey = `scheduling_booking_sort_${page}`;
    let user = null;
    let reservations = [];
    let resources = [];
    let turns = [];
    let bookingStatus = "active";
    let calendarResourceId = 0;
    let selectedDate = paraIso(new Date());
    let visibleMonth = new Date();
    let currentReservation = null;
    let pendingCancelId = 0;

    const el = (id) => document.getElementById(id);
    const isAdmin = () => Boolean(user?.eh_admin) || String(user?.cargo || "").toUpperCase() === "ADMIN" || String(user?.perfil || "").toLowerCase() === "admin";
    const canCancel = (item) => item && item.data >= paraIso(new Date()) && (isAdmin() || Number(item.usuario_id) === Number(user?.id));
    const turnName = (id) => turns.find((item) => String(item.id) === String(id))?.nome || String(id || "Turno não informado");
    const isCancelled = (item) => String(item?.status || "ATIVO").toUpperCase() === "CANCELADO";
    const matchesCalendarResource = (item) => !calendarResourceId || Number(item.recurso_id) === calendarResourceId;

    function loadSort() {
        try {
            const saved = JSON.parse(window.localStorage.getItem(sortStorageKey) || "null");
            if (["data", "aula", "turno", "recurso"].includes(saved?.field)) sort.field = saved.field;
            if ([-1, 1].includes(saved?.direction)) sort.direction = saved.direction;
            sort.group = Boolean(saved?.group);
        } catch (_error) {
            window.localStorage.removeItem(sortStorageKey);
        }
    }

    function saveSort() {
        window.localStorage.setItem(sortStorageKey, JSON.stringify(sort));
    }

    function message(text, error = false) {
        const node = el("msgAgendamento");
        if (!node) return;
        node.textContent = text || "";
        node.dataset.variant = text ? (error ? "erro" : "info") : "";
    }

    function setLoading(loading) {
        el(page === "mine" ? "listaMinhasReservas" : "listaReservasDia")?.setAttribute("aria-busy", String(loading));
        el("calendarioGrid")?.setAttribute("aria-busy", String(loading));
    }

    function renderLoadError(error) {
        setLoading(false);
        const list = el(page === "mine" ? "listaMinhasReservas" : "listaReservasDia");
        if (list) {
            const empty = document.createElement("li");
            empty.className = "booking-empty empty-state";
            const copy = document.createElement("p");
            copy.textContent = "Não foi possível carregar os agendamentos.";
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "print-secondary-btn button";
            retry.textContent = "Tentar novamente";
            retry.addEventListener("click", () => window.location.reload());
            empty.append(copy, retry);
            list.replaceChildren(empty);
        }
        message(error?.message || "Não foi possível carregar os agendamentos.", true);
    }

    function monthRange(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        return {
            start: paraIso(new Date(year, month, 1)),
            end: paraIso(new Date(year, month + 1, 0)),
        };
    }

    async function loadReservations() {
        const range = monthRange(visibleMonth);
        reservations = await fetchJson(`/agendamento/reservas?data_inicio=${range.start}&data_fim=${range.end}`, { headers: headers() });
    }

    function compare(a, b) {
        const values = {
            data: [a.data, b.data],
            aula: [Number(a.aula || a.faixa_global || 0), Number(b.aula || b.faixa_global || 0)],
            turno: [turnName(a.turno), turnName(b.turno)],
            recurso: [a.recurso_nome || "", b.recurso_nome || ""],
        }[sort.field] || [a.data, b.data];
        return String(values[0]).localeCompare(String(values[1]), "pt-BR", { numeric: true }) * sort.direction;
    }

    function bookingItem(item, showProfessor) {
        const li = document.createElement("li");
        li.className = "booking-item list-item";
        const dateCell = document.createElement("div");
        dateCell.className = "booking-date-cell";
        const date = document.createElement("strong");
        date.textContent = paraDataBr(item.data);
        const lesson = document.createElement("span");
        lesson.textContent = item.aula || "Aula não informada";
        dateCell.append(date, lesson);

        const resourceCell = document.createElement("div");
        resourceCell.className = "booking-resource-cell";
        const resource = document.createElement("strong");
        resource.textContent = item.recurso_nome || "Recurso não informado";
        const turn = document.createElement("span");
        turn.textContent = turnName(item.turno);
        resourceCell.append(resource, turn);

        const classCell = document.createElement("div");
        classCell.className = "booking-class-cell";
        const className = document.createElement("strong");
        className.textContent = item.turma || "Turma não informada";
        const theme = document.createElement("span");
        theme.textContent = item.tema_aula || (showProfessor ? `Prof. ${item.professor_nome || "Não informado"}` : "Tema não informado");
        classCell.append(className, theme);

        const status = document.createElement("span");
        status.className = `booking-status ${isCancelled(item) ? "is-cancelled" : "is-active"}`;
        status.textContent = isCancelled(item) ? "Cancelado" : "Ativo";
        const actions = document.createElement("div");
        actions.className = "booking-item-actions action-group action-group--compact";
        const details = document.createElement("button");
        details.type = "button";
        details.className = "print-secondary-btn button";
        details.textContent = "Ver detalhes";
        details.addEventListener("click", () => openDetails(item));
        actions.appendChild(details);
        li.append(dateCell, resourceCell, classCell, status, actions);
        return li;
    }

    function renderList(list, items, emptyText, showProfessor, groupByTurn = false) {
        list.replaceChildren();
        list.setAttribute("aria-busy", "false");
        if (!items.length) {
            const empty = document.createElement("li");
            empty.className = "booking-empty empty-state";
            empty.textContent = emptyText;
            list.appendChild(empty);
            return;
        }
        const ordered = [...items].sort(compare);
        let lastGroup = "";
        ordered.forEach((item) => {
            const group = groupByTurn && !sort.group
                ? turnName(item.turno)
                : String(item.recurso_nome || "Recurso não informado");
            if ((sort.group || groupByTurn) && group !== lastGroup) {
                const heading = document.createElement("li");
                heading.className = groupByTurn && !sort.group ? "booking-shift-heading" : "booking-group-heading";
                heading.textContent = group;
                list.appendChild(heading);
                lastGroup = group;
            }
            list.appendChild(bookingItem(item, showProfessor));
        });
    }

    function renderMine() {
        const query = String(el("bookingSearch")?.value || "").trim().toLocaleLowerCase("pt-BR");
        const items = reservations.filter((item) => {
            const matchesOwner = Number(item.usuario_id) === Number(user?.id);
            const matchesStatus = bookingStatus === "all" || (bookingStatus === "cancelled" ? isCancelled(item) : !isCancelled(item));
            const matchesDate = bookingStatus !== "active" || item.data >= paraIso(new Date());
            const haystack = `${item.recurso_nome || ""} ${item.turma || ""} ${item.tema_aula || ""}`.toLocaleLowerCase("pt-BR");
            return matchesOwner && matchesStatus && matchesDate && (!query || haystack.includes(query));
        });
        const summary = el("myBookingsSummary");
        if (summary) summary.textContent = `${items.length} reserva${items.length === 1 ? "" : "s"} encontrada${items.length === 1 ? "" : "s"} neste mês.`;
        renderList(el("listaMinhasReservas"), items, "Nenhuma reserva corresponde aos filtros.", false);
    }

    function renderDay() {
        el("tituloDia").textContent = `Reservas de ${paraDataBr(selectedDate)}`;
        const items = reservations.filter((item) => item.data === selectedDate && matchesCalendarResource(item));
        const summary = el("calendarDaySummary");
        if (summary) summary.textContent = items.length ? `${items.length} reserva${items.length === 1 ? "" : "s"} para a seleção atual.` : "Nenhuma reserva para a seleção atual.";
        renderList(el("listaReservasDia"), items, "Sem reservas nessa data.", true, true);
    }

    function renderCalendar() {
        const year = visibleMonth.getFullYear();
        const month = visibleMonth.getMonth();
        el("mesAtual").textContent = `${monthNames[month]} ${year}`;
        const grid = el("calendarioGrid");
        grid.replaceChildren();
        weekNames.forEach((name) => {
            const label = document.createElement("div");
            label.className = "calendar-weekday";
            label.textContent = name;
            grid.appendChild(label);
        });
        for (let index = 0; index < new Date(year, month, 1).getDay(); index += 1) {
            const empty = document.createElement("div");
            empty.className = "calendar-empty";
            grid.appendChild(empty);
        }
        for (let day = 1; day <= new Date(year, month + 1, 0).getDate(); day += 1) {
            const date = paraIso(new Date(year, month, day));
            const count = reservations.filter((item) => item.data === date && matchesCalendarResource(item)).length;
            const button = document.createElement("button");
            button.type = "button";
            button.className = "calendar-day";
            button.classList.toggle("is-selected", date === selectedDate);
            button.classList.toggle("is-today", date === paraIso(new Date()));
            button.classList.toggle("has-bookings", count > 0);
            const number = document.createElement("span");
            number.className = "calendar-number";
            number.textContent = day;
            const summary = document.createElement("small");
            summary.className = "calendar-count";
            summary.textContent = count ? `${count} reserva${count === 1 ? "" : "s"}` : "Livre";
            button.append(number, summary);
            button.addEventListener("click", () => { selectedDate = date; renderCalendar(); renderDay(); });
            grid.appendChild(button);
        }
        grid.setAttribute("aria-busy", "false");
    }

    function setDetail(id, value) { if (el(id)) el(id).textContent = value || "-"; }

    function openDetails(item) {
        currentReservation = item;
        setDetail("detalheReservaRecurso", item.recurso_nome);
        setDetail("detalheReservaData", paraDataBr(item.data));
        setDetail("detalheReservaAula", item.aula);
        setDetail("detalheReservaTurma", item.turma || "Turma não informada");
        setDetail("detalheReservaProfessor", item.professor_nome || "Professor não informado");
        setDetail("detalheReservaTema", item.tema_aula || "Tema não informado");
        setDetail("detalheReservaObservacao", item.observacao || "Sem observação.");
        setDetail("detalheReservaCriadoPor", item.professor_nome || "Não informado");
        setDetail("detalheReservaStatus", String(item.status || "ATIVO").toUpperCase() === "CANCELADO" ? "Cancelado" : "Ativo");
        el("detalheReservaRecursosSecao").hidden = true;
        const cancel = el("btnAbrirConfirmacaoCancelamento");
        cancel.hidden = !canCancel(item);
        cancel.disabled = !canCancel(item);
        const drawer = el("painelDetalhesReservaAgendamento");
        drawer.classList.add("is-open");
        drawer.inert = false;
        drawer.setAttribute("aria-hidden", "false");
        document.body.classList.add("scheduler-drawer-open");
    }

    function closeDetails() {
        const drawer = el("painelDetalhesReservaAgendamento");
        drawer.classList.remove("is-open");
        drawer.inert = true;
        drawer.setAttribute("aria-hidden", "true");
        document.body.classList.remove("scheduler-drawer-open");
    }

    function openCancel() {
        pendingCancelId = Number(currentReservation?.id || 0);
        el("dialogCancelarReservaAgendamento").hidden = false;
    }

    function closeCancel() { el("dialogCancelarReservaAgendamento").hidden = true; pendingCancelId = 0; }

    async function cancelReservation() {
        try {
            await fetchJson(`/agendamento/reservas/${pendingCancelId}/cancelar`, { method: "POST", headers: headers() });
            closeCancel();
            closeDetails();
            message("Reserva cancelada com sucesso.");
            await loadReservations();
            page === "mine" ? renderMine() : (renderCalendar(), renderDay());
        } catch (error) { message(error.message || "Não foi possível cancelar.", true); }
    }

    function bindSort() {
        document.querySelectorAll(".booking-sort-field").forEach((item) => item.classList.toggle("is-active", item.dataset.sortField === sort.field));
        const orderButton = document.querySelector(".booking-sort-order");
        if (orderButton) orderButton.textContent = sort.direction > 0 ? "1º → último" : "Último → 1º";
        document.querySelector(".booking-sort-group")?.classList.toggle("is-active", sort.group);
        document.querySelectorAll(".booking-sort-field").forEach((button) => button.addEventListener("click", () => {
            sort.field = button.dataset.sortField;
            saveSort();
            document.querySelectorAll(".booking-sort-field").forEach((item) => item.classList.toggle("is-active", item === button));
            page === "mine" ? renderMine() : renderDay();
        }));
        document.querySelector(".booking-sort-order")?.addEventListener("click", (event) => {
            sort.direction *= -1;
            saveSort();
            event.currentTarget.textContent = sort.direction > 0 ? "1º → último" : "Último → 1º";
            page === "mine" ? renderMine() : renderDay();
        });
        document.querySelector(".booking-sort-group")?.addEventListener("click", (event) => {
            sort.group = !sort.group;
            saveSort();
            event.currentTarget.classList.toggle("is-active", sort.group);
            page === "mine" ? renderMine() : renderDay();
        });
    }

    function bindFilters() {
        el("bookingSearch")?.addEventListener("input", renderMine);
        document.querySelectorAll("[data-booking-status]").forEach((button) => button.addEventListener("click", () => {
            bookingStatus = button.dataset.bookingStatus;
            document.querySelectorAll("[data-booking-status]").forEach((item) => {
                const active = item === button;
                item.classList.toggle("is-active", active);
                item.setAttribute("aria-pressed", String(active));
            });
            renderMine();
        }));

        const resourceFilter = el("calendarResourceFilter");
        if (resourceFilter) {
            resources.forEach((resource) => {
                const option = document.createElement("option");
                option.value = String(resource.id);
                option.textContent = resource.nome;
                resourceFilter.appendChild(option);
            });
            resourceFilter.addEventListener("change", () => {
                calendarResourceId = Number(resourceFilter.value || 0);
                renderCalendar();
                renderDay();
            });
        }
    }

    async function changeMonth(offset) {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + offset, 1);
        selectedDate = paraIso(new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1));
        setLoading(true);
        try {
            await loadReservations();
            message("");
            renderCalendar();
            renderDay();
        } catch (error) {
            renderLoadError(error);
        }
    }

    async function init() {
        try {
            window.AppAuth.garantirToken();
            [user, { turnos: turns }, resources] = await Promise.all([
                fetchJson("/me", { headers: headers() }),
                fetchJson("/agendamento/opcoes", { headers: headers() }),
                fetchJson("/agendamento/recursos", { headers: headers() }),
            ]);
            await loadReservations();
            loadSort();
            bindSort();
            bindFilters();
            if (page === "mine") renderMine(); else { renderCalendar(); renderDay(); }
            el("btnMesAnterior")?.addEventListener("click", () => changeMonth(-1));
            el("btnMesProximo")?.addEventListener("click", () => changeMonth(1));
            el("btnMesHoje")?.addEventListener("click", async () => {
                visibleMonth = new Date();
                selectedDate = paraIso(new Date());
                setLoading(true);
                try {
                    await loadReservations();
                    message("");
                    renderCalendar();
                    renderDay();
                } catch (error) {
                    renderLoadError(error);
                }
            });
            el("btnFecharDetalhesReserva")?.addEventListener("click", closeDetails);
            document.querySelector("[data-close-scheduler-drawer='true']")?.addEventListener("click", closeDetails);
            el("btnAbrirConfirmacaoCancelamento")?.addEventListener("click", openCancel);
            el("btnFecharConfirmacaoCancelamento")?.addEventListener("click", closeCancel);
            el("btnConfirmarCancelamentoReserva")?.addEventListener("click", cancelReservation);
        } catch (error) { renderLoadError(error); }
    }

    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, { once: true }) : init();
})(window, document);
