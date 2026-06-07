(() => {
    function computeVisibility(state) {
        const uploadValid = Boolean(state?.upload?.valid);
        const requestValid = Boolean(state?.request?.valid);
        const settingsValid = Boolean(state?.settings?.valid);
        const submitted = Boolean(state?.submit?.submitted);

        return {
            step1: true,
            step2: uploadValid,
            step3: uploadValid && requestValid,
            step4: uploadValid && requestValid && settingsValid,
            step5: submitted,
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
        const requestedStep = Number(state?.wizard?.currentStep || 1);
        const maxUnlocked = visibility.step5 ? 5 : visibility.step4 ? 4 : visibility.step3 ? 3 : visibility.step2 ? 2 : 1;

        return Math.min(Math.max(requestedStep, 1), maxUnlocked);
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
