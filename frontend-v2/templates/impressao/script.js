(() => {
    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const fallbackClasses = [{ id: 1, nome: "6º Ano A", quantidade_estudantes: 30 }, { id: 2, nome: "7º Ano B", quantidade_estudantes: 45 }];
    const fallbackTags = ["Prova bimestral", "Trabalho avaliativo", "Lista de exercicios", "Recuperação", "Simulado", "Material de apoio", "Comunicado", "Registro", "CAED"];
    const state = { step: 1, file: null, mockFile: "", previewDoc: null, previewState: "normal", previewToken: 0, pages: 4, copies: 1, classes: [], selectedTags: ["Prova bimestral"], submitting: false };

    function authHeaders() {
        const token = localStorage.getItem("token") || "";
        return token ? (window.AppAuth?.criarHeadersAuth?.(token) || { Authorization: `Bearer ${token}` }) : {};
    }

    async function fetchJson(path, fallback) {
        try {
            const response = await fetch(path, { credentials: "same-origin", headers: authHeaders() });
            if (!response.ok) throw new Error("Falha ao carregar");
            return await response.json();
        } catch (_error) {
            return fallback;
        }
    }

    function formatBytes(bytes = 0) {
        if (!bytes) return "2.4 MB";
        const mb = bytes / 1024 / 1024;
        return `${mb >= 1 ? mb.toFixed(1) : (bytes / 1024).toFixed(0)} ${mb >= 1 ? "MB" : "KB"}`;
    }

    function countPdfPages(buffer) {
        const text = new TextDecoder("latin1").decode(new Uint8Array(buffer));
        return Math.max((text.match(/\/Type\s*\/Page\b/g) || []).length, 1);
    }

    function allPages() {
        return Array.from({ length: state.pages }, (_, index) => index + 1);
    }

    function getPageMode() {
        return $("input[name='modoPaginas']:checked")?.value === "custom" ? "custom" : "all";
    }

    function parsePageRange(text, total = state.pages) {
        const pages = new Set();
        String(text || "").split(",").map((part) => part.trim()).filter(Boolean).forEach((part) => {
            const range = part.split("-").map((value) => Number(value.trim()));
            const [start, end = start] = range;
            if (range.length > 2 || !Number.isInteger(start) || !Number.isInteger(end) || start <= 0 || end < start || end > total) throw new Error(`Intervalo inválido: "${part}"`);
            for (let page = start; page <= end; page += 1) pages.add(page);
        });
        return [...pages].sort((a, b) => a - b);
    }

    function selectedPages() {
        const interval = $("#intervaloPaginas")?.value?.trim() || "";
        if (getPageMode() !== "custom" || !interval) return allPages();
        try { return parsePageRange(interval); } catch (_error) { return allPages(); }
    }

    function updateIntervalField(focus = false) {
        const custom = getPageMode() === "custom";
        const field = $("[data-interval-field]");
        if (field) field.hidden = !custom;
        if (custom && focus) $("#intervaloPaginas")?.focus();
    }

    function selectedClass() {
        const id = $("#turmaImpressao")?.value || "";
        return state.classes.find((item) => String(item.id) === id) || null;
    }

    function classCopies(turma) {
        const amount = Math.floor(Number(turma?.quantidade_estudantes || 0));
        return Number.isFinite(amount) && amount > 0 ? amount : 0;
    }

    function renderClassSummary() {
        const summary = $("[data-class-summary]");
        if (!summary) return;
        const turma = selectedClass();
        const amount = classCopies(turma);
        if (!turma) summary.textContent = "Selecione uma turma para preencher as cópias automaticamente.";
        else if (!amount) summary.textContent = `${turma.nome} está sem quantidade cadastrada. Ajuste as cópias manualmente.`;
        else summary.textContent = state.copies === amount ? `${turma.nome} possui ${amount} estudante(s).` : `${turma.nome} possui ${amount} estudante(s). Cópias ajustadas manualmente para ${state.copies}.`;
    }

    function setupPdfJs() {
        if (!window.pdfjsLib) return false;
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        return true;
    }

    function showStep(step) {
        state.step = Math.max(1, Math.min(5, step));
        $$("[data-step]").forEach((item) => { item.hidden = Number(item.dataset.step) !== state.step; });
        $("[data-actions]").hidden = state.step === 5;
        $("[data-preview-panel]")?.classList.toggle("is-bottom", state.step === 5);
        const nextLabel = $("[data-next-label]");
        const nextIcon = $("[data-next-icon]");
        if (nextLabel) nextLabel.textContent = state.step === 4 ? "Confirmar Impressão" : "Próximo";
        if (nextIcon) nextIcon.textContent = state.step === 4 ? "check_circle" : "chevron_right";
        render();
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function renderPreview(root, pages = selectedPages()) {
        if (!root) return;
        root.innerHTML = "";
        const hasDocument = state.file || state.mockFile || state.step >= 4;
        const perSheet = Math.max(1, Number($("#paginasPorFolha")?.value || 1));
        const orientation = $("input[name='orientacao']:checked")?.value || "retrato";
        const totalSheets = Math.max(1, Math.ceil(pages.length / perSheet));
        const token = ++state.previewToken;
        Array.from({ length: Math.min(totalSheets, 4) }).forEach((_, index) => {
            const button = document.createElement("button");
            button.className = index === 0 ? "printing-page-thumb is-selected" : "printing-page-thumb";
            button.type = "button";
            button.dataset.orientation = orientation;
            button.dataset.pagesPerSheet = String(perSheet);
            button.setAttribute("aria-label", `Folha ${index + 1}`);
            previewPagesForSheet(index, perSheet, pages).forEach((page) => {
                const cell = document.createElement("span");
                cell.className = page ? "printing-page-cell" : "printing-page-cell is-empty";
                if (page) cell.dataset.previewPage = String(page);
                if (hasDocument && page) appendMockPage(cell);
                else if (page) cell.textContent = `Pág. ${page}`;
                button.append(cell);
            });
            root.append(button);
        });
        requestAnimationFrame(() => { paintPdfPreview(root, token).catch(() => {}); });
    }

    function previewPagesForSheet(sheetIndex, perSheet, pages) {
        const slice = pages.slice(sheetIndex * perSheet, sheetIndex * perSheet + perSheet);
        return slice.concat(Array.from({ length: perSheet - slice.length }, () => null));
    }

    function setPreviewState(next) {
        state.previewState = next;
        const panel = $("[data-preview-panel]");
        const handle = $("[data-preview-handle]");
        if (panel) panel.dataset.previewState = next;
        if (handle) {
            handle.setAttribute("aria-label", next === "hidden" ? "Abrir prévia" : next === "expanded" ? "Reduzir prévia" : "Expandir prévia");
            handle.setAttribute("aria-expanded", String(next !== "hidden"));
        }
        if (state.previewDoc) render();
    }

    function nextPreviewState(direction) {
        const states = ["hidden", "normal", "expanded"];
        const index = Math.max(0, states.indexOf(state.previewState));
        return states[Math.max(0, Math.min(states.length - 1, index + direction))];
    }

    function appendMockPage(button) {
        const mock = document.createElement("span");
        mock.className = "printing-page-thumb__mock";
        Array.from({ length: 5 }).forEach(() => mock.append(document.createElement("span")));
        button.append(mock);
    }

    async function paintPdfPreview(root, token) {
        if (!state.previewDoc) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 1.4);
        for (const cell of $$("[data-preview-page]", root)) {
            if (token !== state.previewToken) return;
            const page = await state.previewDoc.getPage(Number(cell.dataset.previewPage));
            const base = page.getViewport({ scale: 1 });
            const width = Math.max(40, cell.clientWidth);
            const height = Math.max(40, cell.clientHeight);
            const viewport = page.getViewport({ scale: Math.min(width / base.width, height / base.height) * dpr });
            const canvas = document.createElement("canvas");
            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            const ctx = canvas.getContext("2d");
            cell.replaceChildren(canvas);
            await page.render({ canvasContext: ctx, viewport }).promise;
        }
    }

    function render() {
        const fileName = state.file?.name || state.mockFile || "Prova_Matematica_1Bim.pdf";
        const fileSize = state.file ? formatBytes(state.file.size) : "2.4 MB";
        const pages = selectedPages();
        const sheets = Math.max(1, Math.ceil(pages.length / Math.max(1, Number($("#paginasPorFolha")?.value || 1))));
        const interval = getPageMode() === "custom" ? ($("#intervaloPaginas")?.value?.trim() || "intervalo não informado") : "todas as páginas";
        updateIntervalField();
        renderClassSummary();
        $("#copyCount").textContent = state.copies;
        $("[data-file-title]").textContent = state.file ? state.file.name : state.mockFile || "Toque para buscar arquivos";
        $("[data-file-hint]").textContent = state.file || state.mockFile ? `${state.pages} páginas • ${fileSize}` : "PDF, DOC ou DOCX até 10MB";
        $("[data-preview-title]").textContent = `Prévia das Folhas (${Math.min(sheets, 4)})`;
        renderPreview($("[data-preview-pages]"), pages);
        $("[data-review-file]").textContent = fileName;
        $("[data-review-meta]").textContent = `${state.pages} Páginas • ${fileSize}`;
        $("[data-review-settings]").innerHTML = `<p>${state.copies} cópias • ${$("#paginasPorFolha").value} página(s) por folha • ${$("input[name='orientacao']:checked")?.value || "retrato"}</p><p>Páginas: ${interval}</p>`;
        const finish = [$("#duplexAcabamento").checked && "Frente e verso", $("#grampear").checked && "Grampeado", $("#colorida").checked && "Colorido"].filter(Boolean).join(", ") || "Sem acabamento extra";
        const printer = $("input[name='impressora']:checked")?.value || "Secretaria - Principal";
        $("[data-review-finish]").innerHTML = `<p>${printer} • ${finish}</p><p>Tags: ${state.selectedTags.join(", ") || "Sem tag"}</p>`;
        $("[data-success-printer]").textContent = printer;
        $("[data-success-copies]").textContent = `${state.copies} exemplares${$("#duplexAcabamento").checked ? " (Frente e Verso)" : ""}`;
        $("[data-success-finish]").textContent = finish;
    }

    function setFeedback(message = "", error = false) {
        const feedback = $("[data-feedback]");
        feedback.textContent = message;
        feedback.dataset.variant = error ? "error" : "";
    }

    async function validatePreview(file) {
        if (!file) return;
        setFeedback("Validando arquivo...");
        const formData = new FormData();
        formData.append("arquivo", file);
        try {
            const response = await fetch("/impressao/preview", { method: "POST", body: formData, credentials: "same-origin", headers: authHeaders() });
            if (!response.ok) throw new Error(await response.text());
            await loadPreviewPdf(await response.arrayBuffer());
            setFeedback("Arquivo validado.");
        } catch (_error) {
            if (/\.pdf$/i.test(file.name) || file.type === "application/pdf") {
                await loadPreviewPdf(await file.arrayBuffer());
                setFeedback("Prévia local carregada.");
            } else {
                state.previewDoc = null;
                state.pages = 4;
                setFeedback("Prévia real indisponível; usando prévia visual.", true);
            }
        }
        render();
    }

    async function loadPreviewPdf(buffer) {
        state.pages = countPdfPages(buffer);
        state.previewDoc = null;
        if (!setupPdfJs()) return;
        try {
            state.previewDoc = await window.pdfjsLib.getDocument({ data: buffer.slice(0) }).promise;
            state.pages = state.previewDoc.numPages || state.pages;
        } catch (_error) {
            state.previewDoc = null;
        }
    }

    function buildPrintFormData() {
        const data = new FormData();
        const interval = $("#intervaloPaginas")?.value?.trim() || "";
        if (!state.file) throw new Error("Selecione um arquivo real antes de confirmar.");
        if (!localStorage.getItem("token")) throw new Error("Faça login para enviar a impressão.");
        if (getPageMode() === "custom" && !interval) throw new Error("Informe o intervalo de páginas.");
        if (getPageMode() === "custom") parsePageRange(interval);
        if (!state.selectedTags.length) throw new Error("Selecione ao menos uma tag antes de imprimir.");
        data.append("arquivo", state.file);
        data.append("copias", String(state.copies));
        data.append("paginas_por_folha", $("#paginasPorFolha").value);
        data.append("duplex", $("#duplexAcabamento").checked ? "true" : "false");
        data.append("orientacao", $("input[name='orientacao']:checked")?.value || "retrato");
        if (getPageMode() === "custom") data.append("intervalo_paginas", interval);
        state.selectedTags.forEach((tag) => data.append("tags", tag));
        return data;
    }

    async function submitPrint() {
        let payload;
        try {
            payload = buildPrintFormData();
        } catch (error) {
            setFeedback(error.message, true);
            return;
        }
        showStep(5);
        state.submitting = true;
        $("[data-success-title]").textContent = "Enviando...";
        $("[data-success-message]").textContent = "Enviando para Impressora...";
        try {
            const response = await fetch("/imprimir", { method: "POST", body: payload, credentials: "same-origin", headers: authHeaders() });
            if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Falha ao enviar impressão.");
            const result = await response.json();
            $("[data-success-title]").textContent = "Sucesso!";
            $("[data-success-message]").textContent = "Enviado para Impressora.";
            $("[data-collection-status]").textContent = result?.paginas_restantes === null ? "PRONTO PARA COLETA" : "PRONTO PARA COLETA";
        } catch (error) {
            $("[data-success-title]").textContent = "Atenção";
            $("[data-success-message]").textContent = error.message;
            $("[data-collection-status]").textContent = "VERIFIQUE A SOLICITAÇÃO";
            setFeedback(error.message, true);
        } finally {
            state.submitting = false;
        }
    }

    function renderTags(items) {
        const root = $("[data-tags]");
        root.innerHTML = "";
        items.forEach((item) => {
            const value = String(item.id || item.label || item).trim();
            const label = item.label || value;
            if (!value) return;
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = label;
            button.className = state.selectedTags.includes(value) ? "is-selected" : "";
            button.setAttribute("aria-pressed", String(state.selectedTags.includes(value)));
            button.addEventListener("click", () => {
                state.selectedTags = state.selectedTags.includes(value) ? state.selectedTags.filter((tag) => tag !== value) : [...state.selectedTags, value];
                renderTags(items);
                render();
            });
            root.append(button);
        });
        const status = $("[data-tags-status]");
        if (status) status.textContent = state.selectedTags.length ? `${state.selectedTags.length} tag(s) selecionada(s).` : "Selecione ao menos uma tag.";
    }

    async function loadBackendData() {
        const turmas = await fetchJson("/impressao/turmas", fallbackClasses);
        const tags = await fetchJson("/impressao/tags", fallbackTags.map((label) => ({ label })));
        const tagItems = Array.isArray(tags) ? tags : [];
        const select = $("#turmaImpressao");
        const tagValues = new Set(tagItems.map((item) => String(item.id || item.label || item).trim()).filter(Boolean));
        state.selectedTags = state.selectedTags.filter((tag) => tagValues.has(tag));
        if (!state.selectedTags.length && tagValues.has("Prova bimestral")) state.selectedTags = ["Prova bimestral"];
        state.classes = Array.isArray(turmas) ? turmas : [];
        select.innerHTML = `<option value="">Escolha uma turma...</option>`;
        state.classes.forEach((turma) => {
            const amount = classCopies(turma);
            select.add(new Option(amount ? `${turma.nome} (${amount} estudante(s))` : `${turma.nome} (sem quantidade)`, turma.id));
        });
        select.addEventListener("change", () => {
            const amount = classCopies(selectedClass());
            if (amount) state.copies = amount;
            render();
        });
        renderTags(tagItems);
        await fetchJson("/impressao/status", {});
        await fetchJson("/minha-cota", {});
    }

    function validateInterval() {
        const interval = $("#intervaloPaginas")?.value?.trim() || "";
        if (getPageMode() !== "custom") return true;
        if (!interval) {
            setFeedback("Informe o intervalo de páginas.", true);
            return false;
        }
        try {
            setFeedback(`${parsePageRange(interval).length} página(s) selecionada(s).`);
            return true;
        } catch (error) {
            setFeedback(error.message, true);
            return false;
        }
    }

    function validateStep() {
        if (state.step === 2 && !validateInterval()) return false;
        if (state.step === 3 && !state.selectedTags.length) {
            setFeedback("Selecione ao menos uma tag antes de continuar.", true);
            return false;
        }
        return true;
    }

    function bindEvents() {
        $$("[data-next]").forEach((button) => button.addEventListener("click", () => state.step === 4 ? submitPrint() : validateStep() && showStep(state.step + 1)));
        $$("[data-back]").forEach((button) => button.addEventListener("click", () => showStep(state.step - 1)));
        $$("[data-copy]").forEach((button) => button.addEventListener("click", () => { state.copies = Math.max(1, state.copies + Number(button.dataset.copy)); render(); }));
        $$("input[name='modoPaginas']").forEach((input) => input.addEventListener("change", () => { updateIntervalField(input.value === "custom"); render(); }));
        $("#intervaloPaginas")?.addEventListener("input", () => { if (getPageMode() === "custom") validateInterval(); });
        $("#arquivoAtividade").addEventListener("change", (event) => {
            state.file = event.target.files?.[0] || null; state.mockFile = ""; state.previewDoc = null;
            setPreviewState(state.file ? "expanded" : "normal");
            render();
            validatePreview(state.file);
        });
        $$("[data-recent-file]").forEach((button) => button.addEventListener("click", () => { state.previewDoc = null; state.file = null; state.mockFile = button.dataset.recentFile; state.pages = 4; setPreviewState("normal"); render(); }));
        bindPreviewSheet();
        ["change", "input"].forEach((eventName) => $("#printingForm").addEventListener(eventName, render));
    }

    function bindPreviewSheet() {
        const handle = $("[data-preview-handle]");
        if (!handle) return;
        let startY = 0;
        let dragged = false;
        handle.addEventListener("pointerdown", (event) => {
            startY = event.clientY;
            dragged = false;
            handle.setPointerCapture(event.pointerId);
        });
        handle.addEventListener("pointermove", (event) => { dragged = dragged || Math.abs(event.clientY - startY) > 8; });
        handle.addEventListener("pointerup", (event) => {
            const delta = event.clientY - startY;
            if (delta > 28) setPreviewState(nextPreviewState(-1));
            else if (delta < -28) setPreviewState(nextPreviewState(1));
            else if (!dragged) setPreviewState(state.previewState === "hidden" ? "normal" : state.previewState === "normal" ? "expanded" : "normal");
        });
    }

    bindEvents(); loadBackendData().then(render); setPreviewState(state.previewState); showStep(1);
})();
