(function (document) {
    function close(sidebar) {
        const toggle = sidebar?.querySelector(".app-sidebar-mobile-toggle");
        sidebar?.classList.remove("is-open");
        toggle?.setAttribute("aria-expanded", "false");
    }

    function init() {
        const sidebar = document.querySelector("[data-app-sidebar]");
        if (!sidebar) return;
        document.body.classList.add("has-app-sidebar");

        const navbar = document.querySelector("[data-app-navbar]");
        const syncNavbarHeight = () => {
            if (navbar) {
                document.documentElement.style.setProperty("--app-navbar-height", `${navbar.offsetHeight}px`);
            }
        };
        syncNavbarHeight();
        if (navbar && window.ResizeObserver) new ResizeObserver(syncNavbarHeight).observe(navbar);

        const toggle = sidebar.querySelector(".app-sidebar-mobile-toggle");
        const current = sidebar.querySelector("[data-app-sidebar-current]");
        const tabLinks = [...sidebar.querySelectorAll("[data-app-sidebar-tab-group]")];

        const targetFor = (link) => document.querySelector(
            `[data-${link.dataset.appSidebarTabGroup}-tab-trigger="${link.dataset.appSidebarTabValue}"]`
        );
        const syncTabs = () => {
            tabLinks.forEach((link) => {
                const target = targetFor(link);
                const active = target?.getAttribute("aria-selected") === "true" || target?.classList.contains("is-active");
                link.hidden = !target || target.hidden;
                link.disabled = Boolean(target?.disabled);
                link.classList.toggle("is-disabled", Boolean(target?.disabled));
                link.classList.toggle("is-active", Boolean(active));
                active ? link.setAttribute("aria-current", "page") : link.removeAttribute("aria-current");
            });
            const active = sidebar.querySelector(".app-sidebar-link.is-active");
            if (active && current) current.textContent = active.textContent.trim();
        };
        syncTabs();
        tabLinks.forEach((link) => {
            const target = targetFor(link);
            if (target && window.MutationObserver) {
                new MutationObserver(syncTabs).observe(target, {
                    attributes: true,
                    attributeFilter: ["class", "aria-selected", "hidden", "disabled"],
                });
            }
        });

        toggle?.addEventListener("click", () => {
            const open = !sidebar.classList.contains("is-open");
            sidebar.classList.toggle("is-open", open);
            toggle.setAttribute("aria-expanded", String(open));
        });

        sidebar.addEventListener("click", (event) => {
            const action = event.target.closest("[data-app-sidebar-action]");
            const tabLink = event.target.closest("[data-app-sidebar-tab-group]");
            const targetLink = event.target.closest("[data-app-sidebar-click-target]");
            if (tabLink && !tabLink.disabled) targetFor(tabLink)?.click();
            if (targetLink) document.getElementById(targetLink.dataset.appSidebarClickTarget)?.click();
            if (action) {
                document.dispatchEvent(new CustomEvent("app-sidebar:action", {
                    detail: { action: action.dataset.appSidebarAction },
                }));
            }
            if (event.target.closest(".app-sidebar-link")) close(sidebar);
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest("[data-app-sidebar]")) close(sidebar);
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
                close(sidebar);
                toggle?.focus();
            }
        });
    }

    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, { once: true }) : init();
})(document);
