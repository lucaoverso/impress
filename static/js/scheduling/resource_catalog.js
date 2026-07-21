(function (window, document) {
    const { fetchJson } = window.AppApi;
    const headers = () => window.AppAuth.criarHeadersAuth();
    let resources = [];
    let lastFocusedElement = null;
    let selectedResourceId = 0;

    const el = (id) => document.getElementById(id);
    const normalized = (value) => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const isMobile = () => window.matchMedia("(max-width: 900px)").matches;
    const quantityText = (resource) => Number(resource.quantidade_itens || 1) === 1
        ? "1 item cadastrado"
        : `${Number(resource.quantidade_itens || 1)} itens cadastrados`;

    function iconClass(resource) {
        const value = normalized(`${resource.tipo} ${resource.nome}`);
        if (value.includes("notebook") || value.includes("computador")) return "bi-laptop";
        if (value.includes("tablet")) return "bi-tablet-landscape";
        if (value.includes("som") || value.includes("audio") || value.includes("caixa")) return "bi-speaker";
        if (value.includes("camera")) return "bi-camera-video";
        if (value.includes("tv") || value.includes("televis")) return "bi-tv";
        return "bi-projector";
    }

    function cover(resource, className) {
        const node = document.createElement("div");
        node.className = className;
        const image = String(resource.imagem_capa || "").trim();
        if (image) {
            node.style.backgroundImage = `url("${image.replace(/["\\]/g, "")}")`;
            node.classList.add("has-image");
        }
        const icon = document.createElement("i");
        icon.className = `bi ${iconClass(resource)}`;
        icon.setAttribute("aria-hidden", "true");
        node.appendChild(icon);
        return node;
    }

    function scheduleUrl(resource) {
        return `/agendamento?recurso_id=${encodeURIComponent(resource.id)}`;
    }

    function openDrawer(resource, trigger, initial = false) {
        selectedResourceId = Number(resource.id || 0);
        lastFocusedElement = trigger || document.activeElement;
        el("catalogDrawerType").textContent = resource.tipo || "Recurso";
        el("catalogDrawerTitle").textContent = resource.nome || "Recurso sem nome";
        el("catalogDrawerDescription").textContent = resource.descricao || "Sem descrição cadastrada.";
        el("catalogDrawerQuantity").textContent = quantityText(resource);
        el("catalogDrawerSchedule").href = scheduleUrl(resource);
        el("catalogDrawerCover").replaceWith(cover(resource, "catalog-drawer-cover"));
        document.querySelector(".catalog-drawer-cover").id = "catalogDrawerCover";
        const drawer = el("catalogDrawer");
        drawer.inert = false;
        drawer.classList.add("is-open");
        drawer.setAttribute("aria-hidden", "false");
        document.querySelectorAll(".catalog-card").forEach((card) => card.classList.toggle("is-selected", Number(card.dataset.resourceId) === selectedResourceId));
        if (isMobile()) {
            document.body.classList.add("catalog-drawer-open");
            if (!initial) document.querySelector(".catalog-drawer-close")?.focus();
        }
    }

    function closeDrawer() {
        const drawer = el("catalogDrawer");
        drawer.classList.remove("is-open");
        drawer.setAttribute("aria-hidden", "true");
        drawer.inert = true;
        document.body.classList.remove("catalog-drawer-open");
        lastFocusedElement?.focus();
    }

    function card(resource) {
        const article = document.createElement("article");
        article.className = "catalog-card";
        article.dataset.resourceId = String(resource.id);
        article.classList.toggle("is-selected", Number(resource.id) === selectedResourceId);
        article.appendChild(cover(resource, "catalog-card-cover"));

        const body = document.createElement("div");
        body.className = "catalog-card-body";
        const heading = document.createElement("div");
        heading.className = "catalog-card-heading";
        const type = document.createElement("span");
        type.className = "catalog-resource-type";
        type.textContent = resource.tipo || "Recurso";
        const title = document.createElement("h3");
        title.textContent = resource.nome || "Recurso sem nome";
        const description = document.createElement("p");
        description.textContent = resource.descricao || "Sem descrição cadastrada.";
        heading.append(type, title, description);

        const meta = document.createElement("div");
        meta.className = "catalog-card-meta";
        const quantity = document.createElement("span");
        quantity.textContent = quantityText(resource);
        const status = document.createElement("span");
        status.className = "catalog-status";
        const dot = document.createElement("i");
        dot.setAttribute("aria-hidden", "true");
        status.append(dot, "Disponível");
        meta.append(quantity, status);

        const actions = document.createElement("div");
        actions.className = "catalog-card-actions";
        const schedule = document.createElement("a");
        schedule.className = "button button--primary";
        schedule.href = scheduleUrl(resource);
        schedule.textContent = "Agendar";
        const details = document.createElement("button");
        details.type = "button";
        details.className = "button print-secondary-btn";
        details.textContent = "Ver disponibilidade";
        details.addEventListener("click", () => openDrawer(resource, details));
        actions.append(schedule, details);
        body.append(heading, meta, actions);
        article.appendChild(body);
        return article;
    }

    function render() {
        const query = normalized(el("catalogSearch").value.trim());
        const type = el("catalogTypeFilter").value;
        const capacity = el("catalogCapacityFilter")?.value || "";
        const filtered = resources.filter((resource) => {
            const matchesQuery = !query || normalized(`${resource.nome} ${resource.tipo} ${resource.descricao}`).includes(query);
            const quantity = Number(resource.quantidade_itens || 1);
            const matchesCapacity = !capacity || (capacity === "1" ? quantity === 1 : quantity >= 2);
            return matchesQuery && matchesCapacity && (!type || resource.tipo === type);
        });
        const grid = el("catalogGrid");
        grid.replaceChildren();
        grid.setAttribute("aria-busy", "false");
        el("catalogSummary").textContent = `${filtered.length} de ${resources.length} recurso${resources.length === 1 ? "" : "s"}`;
        if (!filtered.length) {
            const empty = document.createElement("div");
            empty.className = "catalog-empty";
            const icon = document.createElement("i");
            icon.className = "bi bi-search";
            icon.setAttribute("aria-hidden", "true");
            const title = document.createElement("h3");
            title.textContent = "Nenhum recurso encontrado";
            const copy = document.createElement("p");
            copy.textContent = "Tente outro termo ou limpe os filtros.";
            const reset = document.createElement("button");
            reset.type = "button";
            reset.className = "button print-secondary-btn";
            reset.textContent = "Limpar filtros";
            reset.addEventListener("click", () => {
                el("catalogSearch").value = "";
                el("catalogTypeFilter").value = "";
                if (el("catalogCapacityFilter")) el("catalogCapacityFilter").value = "";
                render();
            });
            empty.append(icon, title, copy, reset);
            grid.appendChild(empty);
            return;
        }
        if (!filtered.some((resource) => Number(resource.id) === selectedResourceId)) selectedResourceId = Number(filtered[0].id);
        filtered.forEach((resource) => grid.appendChild(card(resource)));
        const selected = filtered.find((resource) => Number(resource.id) === selectedResourceId) || filtered[0];
        if (!isMobile()) openDrawer(selected, null, true);
    }

    async function init() {
        try {
            window.AppAuth.garantirToken();
            resources = await fetchJson("/agendamento/recursos", { headers: headers() });
            const select = el("catalogTypeFilter");
            [...new Set(resources.map((resource) => String(resource.tipo || "Recurso").trim()).filter(Boolean))]
                .sort((a, b) => a.localeCompare(b, "pt-BR"))
                .forEach((type) => {
                    const option = document.createElement("option");
                    option.value = type;
                    option.textContent = type;
                    select.appendChild(option);
                });
            el("catalogSearch").addEventListener("input", render);
            select.addEventListener("change", render);
            el("catalogCapacityFilter")?.addEventListener("change", render);
            document.querySelectorAll("[data-close-catalog]").forEach((node) => node.addEventListener("click", closeDrawer));
            window.addEventListener("keydown", (event) => { if (event.key === "Escape" && el("catalogDrawer").classList.contains("is-open")) closeDrawer(); });
            render();
        } catch (error) {
            el("catalogGrid").setAttribute("aria-busy", "false");
            el("catalogSummary").textContent = "Catálogo indisponível";
            el("catalogMessage").textContent = error.message || "Não foi possível carregar os recursos.";
            el("catalogMessage").dataset.variant = "erro";
        }
    }

    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, { once: true }) : init();
})(window, document);
