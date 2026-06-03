(() => {
    const DEFAULT_STATE = Object.freeze({
        upload: {
            fileName: "",
            source: null,
            valid: false,
            loading: false,
            error: "",
        },
        request: {
            professorId: null,
            turmaId: null,
            copias: 1,
            valid: false,
        },
        settings: {
            pageMode: "all",
            intervalo: "",
            paginasPorFolha: 1,
            orientacao: "retrato",
            duplex: false,
            valid: false,
        },
        tags: {
            selected: [],
            valid: false,
        },
        preview: {
            loading: false,
            ready: false,
            visible: false,
        },
        visibility: {
            step1: true,
            step2: false,
            step3: false,
            step4: false,
            step5: false,
        },
        submit: {
            canSubmit: false,
            sending: false,
        },
    });

    function cloneDefaultState() {
        return JSON.parse(JSON.stringify(DEFAULT_STATE));
    }

    function createStore() {
        let currentState = cloneDefaultState();
        const listeners = new Set();

        function notify() {
            listeners.forEach((listener) => {
                try {
                    listener(currentState);
                } catch (_err) {
                    // Mantem a UI responsiva mesmo se um observador falhar.
                }
            });
        }

        return {
            getState() {
                return currentState;
            },
            replaceState(nextState) {
                currentState = nextState;
                notify();
                return currentState;
            },
            patchState(patch) {
                currentState = {
                    ...currentState,
                    ...patch,
                };
                notify();
                return currentState;
            },
            reset() {
                currentState = cloneDefaultState();
                notify();
                return currentState;
            },
            subscribe(listener) {
                if (typeof listener !== "function") {
                    return () => undefined;
                }

                listeners.add(listener);
                return () => {
                    listeners.delete(listener);
                };
            },
            createSnapshot() {
                return JSON.parse(JSON.stringify(currentState));
            },
            getDefaultState() {
                return cloneDefaultState();
            },
        };
    }

    window.PrintingUI = window.PrintingUI || {};
    window.PrintingUI.state = createStore();
})();
