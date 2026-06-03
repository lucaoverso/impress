(() => {
    function computeVisibility(state) {
        const uploadValid = Boolean(state?.upload?.valid);
        const requestValid = Boolean(state?.request?.valid);
        const settingsValid = Boolean(state?.settings?.valid);

        return {
            step1: true,
            step2: uploadValid,
            step3: uploadValid && requestValid,
            step4: uploadValid && requestValid && settingsValid,
        };
    }

    function canSubmit(state) {
        const visibility = computeVisibility(state);
        return Boolean(
            visibility.step4
            && state?.upload?.valid
            && state?.request?.valid
            && state?.settings?.valid
            && state?.tags?.valid
            && !state?.upload?.loading
            && !state?.preview?.loading
            && !state?.submit?.sending
        );
    }

    function resolveCurrentStep(state) {
        const visibility = computeVisibility(state);

        if (!visibility.step2) return 1;
        if (!visibility.step3) return 2;
        if (!visibility.step4) return 3;

        const requestedStep = Number(state?.wizard?.currentStep || 1);
        return Math.min(Math.max(requestedStep, 1), 4);
    }

    function applyWorkflowState(state) {
        const visibility = computeVisibility(state);
        return {
            ...state,
            visibility,
            wizard: {
                ...state.wizard,
                currentStep: resolveCurrentStep({
                    ...state,
                    visibility,
                }),
            },
            submit: {
                ...state.submit,
                canSubmit: canSubmit({
                    ...state,
                    visibility,
                }),
            },
        };
    }

    window.PrintingUI = window.PrintingUI || {};
    window.PrintingUI.workflow = {
        computeVisibility,
        canSubmit,
        applyWorkflowState,
        resolveCurrentStep,
    };
})();
