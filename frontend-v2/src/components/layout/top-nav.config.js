export const TOP_NAV_DEFAULTS = {
    search: {
        enabled: true,
        action: "",
        method: "get",
        name: "q",
        placeholder: "Buscar estudante ou registro...",
    },
    notifications: {
        enabled: true,
        hasUnread: false,
        count: 0,
    },
    calendar: {
        enabled: true,
        href: "",
    },
    user: {
        name: "Usuario",
        role: "Perfil",
        initials: "US",
        avatarUrl: "",
    },
};

export function createTopNavbarConfig(overrides = {}) {
    return {
        ...TOP_NAV_DEFAULTS,
        ...overrides,
        search: {
            ...TOP_NAV_DEFAULTS.search,
            ...(overrides.search || {}),
        },
        notifications: {
            ...TOP_NAV_DEFAULTS.notifications,
            ...(overrides.notifications || {}),
        },
        calendar: {
            ...TOP_NAV_DEFAULTS.calendar,
            ...(overrides.calendar || {}),
        },
        user: {
            ...TOP_NAV_DEFAULTS.user,
            ...(overrides.user || {}),
        },
    };
}

export const createTopNavConfig = createTopNavbarConfig;
