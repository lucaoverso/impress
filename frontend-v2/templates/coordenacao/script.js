const filterForm = document.querySelector("[data-coordenacao-filters]");
const searchForm = document.querySelector("[data-top-navbar-search]");
const sideNavLinks = Array.from(document.querySelectorAll(".side-navbar__link[href^='#']"));
const sideNavPanels = sideNavLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);
const backendReadyForms = document.querySelectorAll(
    "[data-base-legal-form], [data-student-search-form], [data-teacher-reason-form]",
);

function setActiveSideNav(targetId) {
    const fallbackId = sideNavLinks[0]?.getAttribute("href")?.slice(1);
    const activePanel = document.getElementById(targetId) || document.getElementById(fallbackId);
    if (!activePanel) return;
    const activePanelId = activePanel.id;

    sideNavLinks.forEach((link) => {
        const isActive = link.getAttribute("href") === `#${activePanelId}`;
        link.classList.toggle("is-active", isActive);

        if (isActive) {
            link.setAttribute("aria-current", "page");
            return;
        }

        link.removeAttribute("aria-current");
    });

    sideNavPanels.forEach((panel) => {
        const isActive = panel.id === activePanelId;
        panel.hidden = !isActive;
        panel.classList.toggle("is-active", isActive);
    });
}

function announceFrontendOnly(event) {
    event.preventDefault();
    const source = event.currentTarget;
    source.dataset.pendingBackend = "true";
}

filterForm?.addEventListener("submit", announceFrontendOnly);
searchForm?.addEventListener("submit", announceFrontendOnly);
backendReadyForms.forEach((form) => form.addEventListener("submit", announceFrontendOnly));

sideNavLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        const targetId = link.getAttribute("href")?.slice(1);
        if (targetId) {
            setActiveSideNav(targetId);
            history.replaceState(null, "", `#${targetId}`);
        }
    });
});

const initialPanelId = location.hash.slice(1) || sideNavLinks[0]?.getAttribute("href")?.slice(1);
if (initialPanelId) setActiveSideNav(initialPanelId);

document.querySelector("[data-app-logout]")?.addEventListener("click", () => {
    document.body.dataset.logoutRequested = "true";
});

window.SuiteEscolarV2 = {
    ...(window.SuiteEscolarV2 || {}),
    setActiveSideNav,
};
