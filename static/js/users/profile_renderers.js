(function (window, document) {
    const DAY_BY_INDEX = ["", "SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"];
    const SUCCESS_STATUSES = new Set(["APROVADO", "IMPRESSO", "CONCLUIDO", "FINALIZADO", "ATIVO"]);
    const WARNING_STATUSES = new Set(["PENDENTE", "AGUARDANDO", "PROCESSANDO", "IMPRIMINDO", "AJUSTES"]);

    const el = (id) => document.getElementById(id);

    function node(tag, className, text) {
        const item = document.createElement(tag);
        if (className) item.className = className;
        if (text !== undefined) item.textContent = text;
        return item;
    }

    function initials(name) {
        const parts = String(name || "U").trim().split(/\s+/).filter(Boolean);
        return `${parts[0]?.[0] || "U"}${parts.length > 1 ? parts.at(-1)[0] : ""}`.toUpperCase();
    }

    function roleLabel(role) {
        const labels = { PROFESSOR: "Perfil do docente", COORDENADOR: "Perfil da coordenação", ADMIN: "Perfil da gestão" };
        return labels[String(role || "").toUpperCase()] || "Perfil do usuário";
    }

    function formatDate(value, includeTime = false) {
        if (!value) return "";
        const source = String(value).trim();
        const normalized = /^\d{4}-\d{2}-\d{2}$/.test(source)
            ? `${source}T12:00:00`
            : (source.includes("T") ? source : source.replace(" ", "T"));
        const parsed = new Date(normalized);
        if (Number.isNaN(parsed.getTime())) return source;
        return new Intl.DateTimeFormat("pt-BR", includeTime
            ? { dateStyle: "short", timeStyle: "short" }
            : { dateStyle: "short" }).format(parsed);
    }

    function renderIdentity(user) {
        el("profileAvatar").textContent = initials(user.nome);
        el("profileRole").textContent = roleLabel(user.cargo);
        el("profileName").textContent = user.nome;
        el("profileEmail").textContent = user.email;
        const chips = el("profileChips");
        chips.replaceChildren();
        const groups = [
            ["bi-book", user.disciplinas || []],
            ["bi-people", user.turmas || []],
        ];
        groups.forEach(([icon, values]) => values.forEach((value) => {
            const chip = node("span", "profile-chip");
            const symbol = node("i", `bi ${icon}`);
            symbol.setAttribute("aria-hidden", "true");
            chip.append(symbol, document.createTextNode(value));
            chips.appendChild(chip);
        }));
        if (!chips.childElementCount) chips.appendChild(node("span", "profile-chip", "Sem vínculos escolares"));
    }

    function renderStudentPreview(students, target) {
        target.replaceChildren();
        if (!students.length) {
            target.appendChild(node("div", "profile-empty", "Nenhum estudante com apoio pedagógico ativo nas suas turmas."));
            return;
        }
        students.forEach((student) => {
            const card = node("article", "profile-student-card");
            const avatar = node("span", "profile-student-initials", initials(student.nome));
            avatar.setAttribute("aria-hidden", "true");
            const detail = node("div");
            detail.append(node("strong", "", student.nome));
            detail.append(node("span", "", `${student.turma_nome} · ${student.resumo_apoio}`));
            card.append(avatar, detail);
            target.appendChild(card);
        });
    }

    function renderStudentFull(students, target) {
        target.replaceChildren();
        students.forEach((student) => {
            const row = node("article", "profile-student-row");
            const identity = node("div");
            identity.append(node("strong", "", student.nome), node("p", "", student.turma_nome));
            const support = node("div");
            support.append(
                node("strong", "", student.apoios?.length ? student.resumo_apoio : "Recomendação pedagógica"),
                node("p", "", student.recomendacoes?.join(" · ") || "Sem recomendação adicional.")
            );
            row.append(identity, support);
            target.appendChild(row);
        });
    }

    function isCurrent(day, slot) {
        const now = new Date();
        if (DAY_BY_INDEX[now.getDay()] !== day) return false;
        const current = now.getHours() * 60 + now.getMinutes();
        const minutes = (value) => {
            const [hour, minute] = String(value || "").split(":").map(Number);
            return Number.isFinite(hour) && Number.isFinite(minute) ? hour * 60 + minute : -1;
        };
        const start = minutes(slot.horario_inicio);
        const end = minutes(slot.horario_fim);
        return start >= 0 && end >= 0 && current >= start && current < end;
    }

    function itemFor(schedule, day, slot) {
        return schedule.itens.find((item) =>
            item.dia_semana === day &&
            (item.faixa_global === slot.aula_numero || item.aula_numero === slot.aula_numero)
        );
    }

    function scheduleTime(slot) {
        return [slot.horario_inicio, slot.horario_fim].filter(Boolean).join("–");
    }

    function scheduleTimeCell(slot, className) {
        const time = node("div", className);
        const number = Number(slot.aula_numero);
        time.appendChild(node("strong", "", number > 0 ? `${number}ª aula` : (slot.nome || "Aula")));
        const range = scheduleTime(slot);
        if (range) time.appendChild(node("span", "", range));
        return time;
    }

    function classSlot(item, current) {
        const slot = node("div", "profile-class-slot");
        if (item.tem_estudante_apoio) slot.classList.add("has-support");
        if (current) {
            slot.classList.add("is-current");
            slot.appendChild(node("span", "profile-now", "Agora"));
        }
        slot.appendChild(node("strong", "", item.turma_nome));
        slot.appendChild(node("span", "", item.disciplina_nome));
        if (item.tem_estudante_apoio) {
            const marker = node("span", "profile-support-marker", " Apoio pedagógico");
            const icon = node("i", "bi bi-person-heart");
            icon.setAttribute("aria-hidden", "true");
            marker.prepend(icon);
            slot.appendChild(marker);
        }
        return slot;
    }

    function renderScheduleTable(schedule) {
        const head = el("profileScheduleHead");
        const body = el("profileScheduleBody");
        head.replaceChildren(node("th", "", "Aula / horário"));
        head.firstChild.scope = "col";
        schedule.dias_semana.forEach((day) => {
            const th = node("th", "", day.nome);
            th.scope = "col";
            head.appendChild(th);
        });
        body.replaceChildren();
        schedule.faixas.filter((slot) =>
            schedule.dias_semana.some((day) => itemFor(schedule, day.id, slot))
        ).forEach((slot) => {
            const row = node("tr");
            const time = node("td");
            time.appendChild(scheduleTimeCell(slot, "profile-schedule-time"));
            row.appendChild(time);
            schedule.dias_semana.forEach((day) => {
                const cell = node("td");
                const item = itemFor(schedule, day.id, slot);
                if (item) cell.appendChild(classSlot(item, isCurrent(day.id, slot)));
                row.appendChild(cell);
            });
            body.appendChild(row);
        });
    }

    function renderMobileDay(schedule, dayId) {
        const target = el("profileDayLessons");
        target.replaceChildren();
        schedule.faixas.forEach((slot) => {
            const item = itemFor(schedule, dayId, slot);
            if (!item) return;
            const lesson = node("article", "profile-mobile-lesson");
            if (item.tem_estudante_apoio) lesson.classList.add("has-support");
            if (isCurrent(dayId, slot)) lesson.classList.add("is-current");
            const time = scheduleTimeCell(slot, "profile-mobile-time");
            const detail = classSlot(item, isCurrent(dayId, slot));
            lesson.append(time, detail);
            target.appendChild(lesson);
        });
        if (!target.childElementCount) target.appendChild(node("div", "profile-empty", "Nenhuma aula cadastrada neste dia."));
    }

    function renderSchedule(schedule) {
        const hasSchedule = Boolean(schedule.faixas?.length && schedule.itens?.length);
        el("profileScheduleYear").textContent = `Ano letivo ${schedule.ano_letivo}`;
        el("profileScheduleEmpty").hidden = hasSchedule;
        el("profileScheduleDesktop").hidden = !hasSchedule;
        el("profileScheduleMobile").hidden = !hasSchedule;
        if (!hasSchedule) return;
        renderScheduleTable(schedule);
        const tabs = el("profileDayTabs");
        tabs.replaceChildren();
        const today = DAY_BY_INDEX[new Date().getDay()];
        const initial = schedule.dias_semana.some((day) => day.id === today) ? today : schedule.dias_semana[0].id;
        schedule.dias_semana.forEach((day) => {
            const button = node("button", "button profile-day-tab", day.nome);
            button.type = "button";
            button.role = "tab";
            button.setAttribute("aria-selected", String(day.id === initial));
            button.addEventListener("click", () => {
                tabs.querySelectorAll("[role=tab]").forEach((tab) => tab.setAttribute("aria-selected", "false"));
                button.setAttribute("aria-selected", "true");
                renderMobileDay(schedule, day.id);
            });
            tabs.appendChild(button);
        });
        renderMobileDay(schedule, initial);
    }

    function statusClass(status) {
        if (SUCCESS_STATUSES.has(status)) return "is-success";
        if (WARNING_STATUSES.has(status)) return "is-warning";
        return "";
    }

    function renderActivity(items, target, emptyMessage, detail) {
        target.replaceChildren();
        if (!items.length) {
            const empty = node("li", "profile-empty", emptyMessage);
            target.appendChild(empty);
            return;
        }
        items.forEach((item) => {
            const row = node("li", "profile-activity-item");
            const main = node("div");
            main.append(node("strong", "", item.title), node("span", "", detail(item)));
            const badge = node("span", `profile-status ${statusClass(item.status)}`, item.status_label);
            row.append(main, badge);
            target.appendChild(row);
        });
    }

    function renderDashboard(dashboard) {
        renderStudentPreview(dashboard.estudantes.itens, el("profileStudentsPreview"));
        const toggle = el("profileStudentsToggle");
        toggle.hidden = dashboard.estudantes.total <= dashboard.estudantes.itens.length;
        renderSchedule(dashboard.horario);
        renderActivity(dashboard.envios_apc.map((item) => ({ ...item, title: item.arquivo })),
            el("profileSubmissions"), "Nenhum envio recente na APC.",
            (item) => [item.turma_nome, item.disciplina_nome, formatDate(item.enviado_em, true)].filter(Boolean).join(" · "));
        renderActivity(dashboard.impressoes.map((item) => ({ ...item, title: item.arquivo })),
            el("profilePrintJobs"), "Nenhuma solicitação de impressão recente.",
            (item) => `${item.paginas_totais} página(s) · ${item.copias} cópia(s) · ${formatDate(item.criado_em, true)}`);
        renderActivity(dashboard.agendamentos.map((item) => ({ ...item, title: item.recurso_nome })),
            el("profileBookings"), "Nenhum agendamento futuro.",
            (item) => [formatDate(item.data), [item.horario_inicio, item.horario_fim].filter(Boolean).join("–"), item.turma].filter(Boolean).join(" · "));
    }

    window.ProfileRenderers = { formatDate, renderDashboard, renderIdentity, renderStudentFull };
})(window, document);
