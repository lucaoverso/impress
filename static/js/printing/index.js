(() => {
    let lastRenderedStep = null;
    let lastPreviewVisible = false;
    const STEP_ENTER_CLASS = "is-step-enter";

    function isMobileWizardLayout() {
        return window.matchMedia("(max-width: 980px)").matches;
    }

    function syncDesktopPreviewHeight() {
        document.documentElement.style.removeProperty("--print-desktop-preview-height");
    }

    function animateAndScrollToStep(article) {
        if (!article) {
            return;
        }

        article.classList.remove(STEP_ENTER_CLASS);
        void article.offsetWidth;
        article.classList.add(STEP_ENTER_CLASS);
        article.addEventListener("animationend", () => {
            article.classList.remove(STEP_ENTER_CLASS);
        }, { once: true });
    }

    function scrollToWizardStart() {
        const wizardLeft = document.querySelector(".print-wizard-left");
        const activeArticle = document.querySelector(".print-wizard-left > .print-step-card:not([hidden])");
        const anchor = document.getElementById("printWizardStartAnchor");
        if (wizardLeft && typeof wizardLeft.scrollTo === "function") {
            wizardLeft.scrollTo({
                top: 0,
                behavior: "smooth",
            });
        }
        if (activeArticle) {
            activeArticle.scrollTop = 0;
        }
        if (!anchor) {
            return;
        }
        window.requestAnimationFrame(() => {
            anchor.scrollIntoView({
                behavior: "smooth",
                block: "start",
                inline: "nearest",
            });
        });
    }

    function clearStepAnimations(stepArticles) {
        Object.values(stepArticles).forEach((article) => {
            if (!article) {
                return;
            }
            article.classList.remove(STEP_ENTER_CLASS);
        });
    }

    function mergeDeep(base, patch) {
        const output = { ...base };
        Object.entries(patch || {}).forEach(([key, value]) => {
            if (
                value
                && typeof value === "object"
                && !Array.isArray(value)
                && base[key]
                && typeof base[key] === "object"
                && !Array.isArray(base[key])
            ) {
                output[key] = mergeDeep(base[key], value);
            } else {
                output[key] = value;
            }
        });
        return output;
    }

    function getPageMode() {
        const checked = document.querySelector("input[name='modoPaginas']:checked");
        return checked?.value === "custom" ? "custom" : "all";
    }

    function getForcedStep() {
        const raw = Number(document.documentElement.dataset.printingForceStep || 0);
        return Number.isFinite(raw) && raw > 0 ? raw : null;
    }

    function setForcedStep(step = null) {
        if (!step || Number(step) <= 0) {
            delete document.documentElement.dataset.printingForceStep;
            return;
        }
        document.documentElement.dataset.printingForceStep = String(step);
    }

    function updateIntervalGroupVisibility(pageMode = getPageMode()) {
        const intervaloGroup = document.getElementById("grupoIntervaloPaginas");
        if (!intervaloGroup) {
            return;
        }
        intervaloGroup.hidden = pageMode !== "custom";
    }

    function isPreviewReadyFromDom() {
        return document.querySelectorAll("#previewContainer .print-sheet-thumb").length > 0;
    }

    function isPreviewLoadingFromDom() {
        const texto = String(document.getElementById("intervaloInfo")?.innerText || "").trim().toLowerCase();
        return texto.includes("gerando") || texto.includes("buscando");
    }

    function safeValidateInterval() {
        if (typeof window.obterPaginasSelecionadas !== "function") {
            return null;
        }
        try {
            window.obterPaginasSelecionadas();
            return true;
        } catch (_err) {
            return false;
        }
    }

    function readLegacyDomState(overrides = {}) {
        const arquivoInput = document.getElementById("arquivo");
        const professorInput = document.getElementById("professorSolicitante");
        const turmaInput = document.getElementById("turmaImpressao");
        const copiasInput = document.getElementById("copias");
        const intervaloInput = document.getElementById("intervaloPaginas");
        const paginasPorFolhaInput = document.getElementById("paginasPorFolha");
        const orientacaoInput = document.getElementById("orientacao");
        const duplexInput = document.getElementById("duplex");
        const selectedTags = Array.from(document.querySelectorAll("#tagsImpressao input[type='checkbox']:checked"))
            .map((input) => String(input.value || "").trim())
            .filter(Boolean);
        const fileName = overrides?.upload?.fileName || arquivoInput?.files?.[0]?.name || "";
        const pageMode = overrides?.settings?.pageMode || getPageMode();
        const intervalo = intervaloInput?.value?.trim() || "";
        const turmaId = turmaInput?.value ? Number(turmaInput.value) : null;
        const copias = Math.max(1, Number(copiasInput?.value || 1));

        return {
            upload: {
                fileName,
                source: overrides?.upload?.source || null,
                valid: Boolean(overrides?.upload?.valid ?? fileName),
                loading: Boolean(overrides?.upload?.loading),
                error: overrides?.upload?.error || "",
            },
            request: {
                professorId: professorInput?.value ? Number(professorInput.value) : null,
                turmaId,
                copias,
                valid: Boolean(turmaId && copias >= 1),
            },
            settings: {
                pageMode,
                intervalo,
                paginasPorFolha: Number(paginasPorFolhaInput?.value || 1),
                orientacao: orientacaoInput?.value || "retrato",
                duplex: Boolean(duplexInput?.checked),
                valid: pageMode === "all" ? true : Boolean(intervalo) && safeValidateInterval() !== false,
            },
            tags: {
                selected: selectedTags,
                valid: selectedTags.length > 0,
            },
            preview: {
                loading: Boolean(overrides?.preview?.loading ?? isPreviewLoadingFromDom()),
                ready: Boolean(overrides?.preview?.ready ?? isPreviewReadyFromDom()),
                visible: true,
            },
            submit: {
                canSubmit: false,
                sending: Boolean(overrides?.submit?.sending),
            },
            wizard: {
                currentStep: Number(overrides?.wizard?.currentStep || document.documentElement.dataset.printingCurrentStep || 1),
            },
        };
    }

    function setChoiceSelection(selector, value, attributeName) {
        document.querySelectorAll(selector).forEach((button) => {
            button.classList.toggle("is-selected", button.dataset[attributeName] === String(value));
        });
    }

    function renderPageMode(state) {
        const pageMode = state?.settings?.pageMode === "custom" ? "custom" : "all";
        const checkedInput = document.querySelector(`input[name='modoPaginas'][value='${pageMode}']`);
        if (checkedInput) {
            checkedInput.checked = true;
        }
        updateIntervalGroupVisibility(pageMode);
        setChoiceSelection(".print-choice-block[data-layout-choice]", state?.settings?.paginasPorFolha || 1, "layoutChoice");
        setChoiceSelection(".print-choice-block[data-orientation-choice]", state?.settings?.orientacao || "retrato", "orientationChoice");
    }

    function renderCurrentStep(state) {
        const currentStepState = Number(state?.wizard?.currentStep || 1);
        const forcedStep = isMobileWizardLayout() ? getForcedStep() : null;
        const currentStep = forcedStep ? Math.max(currentStepState, forcedStep) : currentStepState;
        const stepArticles = {
            1: document.getElementById("etapaArquivo"),
            2: document.getElementById("etapaSolicitacao"),
            3: document.getElementById("etapaConfiguracoes"),
            4: document.getElementById("etapaConferencia"),
            5: document.getElementById("etapaAcompanhamento"),
        };
        const activeArticle = stepArticles[currentStep];

        Object.entries(stepArticles).forEach(([step, article]) => {
            if (!article) {
                return;
            }
            article.hidden = Number(step) !== currentStep;
        });

        const stepperCard = document.getElementById("printStepperCard");
        if (stepperCard && activeArticle && activeArticle.firstElementChild !== stepperCard) {
            activeArticle.prepend(stepperCard);
        }

        if (activeArticle) {
            clearStepAnimations(stepArticles);
            if (lastRenderedStep !== null && lastRenderedStep !== currentStep) {
                animateAndScrollToStep(activeArticle);
            }
        }

        [
            ["stepperArquivo", 1],
            ["stepperSolicitacao", 2],
            ["stepperConfiguracoes", 3],
            ["stepperResumo", 4],
            ["stepperAcompanhamento", 5],
        ].forEach(([id, step]) => {
            const item = document.getElementById(id);
            if (!item) {
                return;
            }

            item.classList.toggle("is-current", step === currentStep);
            item.classList.toggle("is-complete", step < currentStep);
        });

        document.documentElement.dataset.printingCurrentStep = String(currentStep);
        lastRenderedStep = currentStep;
        return currentStep;
    }

    function renderProgressiveFlow(state) {
        renderPageMode(state);
        const currentStep = renderCurrentStep(state);
        syncDesktopPreviewHeight();
        const shouldShowPreview = Boolean(state?.upload?.valid || state?.preview?.ready)
            && currentStep > 1;
        document.documentElement.dataset.printingMobilePreview = String(shouldShowPreview);

        if (shouldShowPreview && state?.preview?.ready && !lastPreviewVisible) {
            window.requestAnimationFrame(() => {
                window.requestAnimationFrame(() => {
                    if (typeof window.atualizarPreview === "function") {
                        window.atualizarPreview();
                    }
                });
            });
        }
        lastPreviewVisible = shouldShowPreview;

        const btnContinuarArquivo = document.getElementById("btnContinuarArquivo");
        const btnContinuarSolicitacao = document.getElementById("btnContinuarSolicitacao");
        const btnContinuarConfiguracoes = document.getElementById("btnContinuarConfiguracoes");
        if (btnContinuarArquivo) btnContinuarArquivo.disabled = !state?.visibility?.step2;
        if (btnContinuarSolicitacao) btnContinuarSolicitacao.disabled = !state?.visibility?.step3;
        if (btnContinuarConfiguracoes) btnContinuarConfiguracoes.disabled = !state?.visibility?.step4;
    }

    function syncFromLegacyDom(overrides = {}) {
        if (!window.PrintingUI?.state || !window.PrintingUI?.workflow) {
            return null;
        }

        const currentState = window.PrintingUI.state.getState();
        const nextState = mergeDeep(currentState, readLegacyDomState(overrides));
        const workflowState = window.PrintingUI.workflow.applyWorkflowState(nextState);
        window.PrintingUI.state.replaceState(workflowState);
        return workflowState;
    }

    function setWizardState(step, patch = {}) {
        if (!window.PrintingUI?.state || !window.PrintingUI?.workflow) {
            return null;
        }

        const currentState = window.PrintingUI.state.getState();
        const nextState = mergeDeep(currentState, mergeDeep(patch, {
            wizard: {
                currentStep: step,
            },
        }));
        const workflowState = window.PrintingUI.workflow.applyWorkflowState(nextState);
        window.PrintingUI.state.replaceState(workflowState);
        return workflowState;
    }

    function goToStep(step) {
        const current = window.PrintingUI?.state?.getState?.();
        if (!current) {
            return;
        }

        if (Number(step) <= 1) {
            setForcedStep(null);
        }

        const maxUnlocked = current.visibility.step5 ? 5 : current.visibility.step4 ? 4 : current.visibility.step3 ? 3 : current.visibility.step2 ? 2 : 1;
        const targetStep = Math.min(Math.max(step, 1), maxUnlocked);
        const currentStep = Number(current?.wizard?.currentStep || document.documentElement.dataset.printingCurrentStep || 1);
        const advancing = targetStep > currentStep;
        syncFromLegacyDom({
            wizard: {
                currentStep: targetStep,
            },
        });
        if (advancing) {
            scrollToWizardStart();
        }
    }

    function registerDomBindings() {
        updateIntervalGroupVisibility();

        document.querySelectorAll("input[name='modoPaginas']").forEach((input) => {
            input.addEventListener("change", () => {
                updateIntervalGroupVisibility(input.value);
                syncFromLegacyDom({
                    settings: {
                        pageMode: getPageMode(),
                    },
                });
                if (typeof window.atualizarPreview === "function") {
                    window.atualizarPreview();
                }
            });
        });

        document.querySelectorAll(".print-choice-block[data-layout-choice]").forEach((button) => {
            button.addEventListener("click", () => {
                const select = document.getElementById("paginasPorFolha");
                if (select) {
                    select.value = button.dataset.layoutChoice;
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });
        });

        document.querySelectorAll(".print-choice-block[data-orientation-choice]").forEach((button) => {
            button.addEventListener("click", () => {
                const select = document.getElementById("orientacao");
                if (select) {
                    select.value = button.dataset.orientationChoice;
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });
        });

        [
            "professorSolicitante",
            "turmaImpressao",
            "copias",
            "intervaloPaginas",
            "paginasPorFolha",
            "orientacao",
            "duplex",
        ].forEach((id) => {
            document.getElementById(id)?.addEventListener("change", () => syncFromLegacyDom());
            document.getElementById(id)?.addEventListener("input", () => syncFromLegacyDom());
        });

        document.getElementById("tagsImpressao")?.addEventListener("change", () => syncFromLegacyDom());

        document.getElementById("btnContinuarArquivo")?.addEventListener("click", () => goToStep(2));
        document.getElementById("btnVoltarSolicitacao")?.addEventListener("click", () => goToStep(1));
        document.getElementById("btnContinuarSolicitacao")?.addEventListener("click", () => goToStep(3));
        document.getElementById("btnVoltarConfiguracoes")?.addEventListener("click", () => goToStep(2));
        document.getElementById("btnContinuarConfiguracoes")?.addEventListener("click", () => goToStep(4));
        document.getElementById("btnVoltarConferencia")?.addEventListener("click", () => goToStep(3));
    }

    function bootstrapPrintingUI() {
        if (!window.PrintingUI?.state || !window.PrintingUI?.workflow) {
            return;
        }
        registerDomBindings();
        window.PrintingUI.state.subscribe(renderProgressiveFlow);
        syncFromLegacyDom();
        window.addEventListener("resize", () => {
            window.requestAnimationFrame(syncDesktopPreviewHeight);
        });
        window.requestAnimationFrame(syncDesktopPreviewHeight);
        document.documentElement.dataset.printingUi = "ready";
    }

    window.PrintingUI = window.PrintingUI || {};
    window.PrintingUI.ui = {
        syncFromLegacyDom,
        setWizardState,
        setForcedStep,
        renderProgressiveFlow,
        goToStep,
        isMobileWizardLayout,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootstrapPrintingUI, { once: true });
    } else {
        bootstrapPrintingUI();
    }
})();
