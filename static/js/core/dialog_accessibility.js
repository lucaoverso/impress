(() => {
    const dialogSelector = '[role="dialog"][aria-modal="true"]';
    const focusableSelector = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled]):not([type="hidden"])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        'summary',
        '[contenteditable="true"]',
        '[tabindex]:not([tabindex="-1"])',
    ].join(',');

    function isVisible(element) {
        return !element.closest('[hidden], [aria-hidden="true"], [inert]')
            && element.getClientRects().length > 0;
    }

    function activeDialog() {
        return [...document.querySelectorAll(dialogSelector)].filter(isVisible).at(-1) || null;
    }

    function focusableElements(dialog) {
        return [...dialog.querySelectorAll(focusableSelector)].filter(isVisible);
    }

    function trapTab(event) {
        if (event.key !== 'Tab') return;

        const dialog = activeDialog();
        if (!dialog) return;

        const focusable = focusableElements(dialog);
        if (!focusable.length) {
            event.preventDefault();
            dialog.focus();
            return;
        }

        const first = focusable[0];
        const last = focusable.at(-1);
        if (!dialog.contains(document.activeElement)) {
            event.preventDefault();
            first.focus();
        } else if (document.activeElement === dialog) {
            event.preventDefault();
            (event.shiftKey ? last : first).focus();
        } else if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    document.querySelectorAll(dialogSelector).forEach((dialog) => {
        if (!dialog.hasAttribute('tabindex')) dialog.tabIndex = -1;
    });
    document.addEventListener('keydown', trapTab);
})();
