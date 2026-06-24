export const SIDE_NAV_MODULES = {
    coordenacao: {
        context: "Modulo de coordenacao",
        current: "ocorrencias",
        primaryAction: {
            href: "#novo-registro",
            label: "Novo registro",
            icon: "add_circle",
        },
        sections: [
            {
                label: "Coordenacao",
                description: "Rotinas do modulo",
                links: [
                    { key: "ocorrencias", href: "#ocorrencias", label: "Ocorrencias", icon: "grid_view" },
                    { key: "base-legal", href: "#base-legal", label: "Base legal", icon: "article" },
                    { key: "estudantes", href: "#estudantes", label: "Estudantes", icon: "person" },
                    { key: "relatorios", href: "#relatorios", label: "Relatorios", icon: "bar_chart" },
                    { key: "fluxo-professor", href: "#fluxo-professor", label: "Fluxo do professor", icon: "send" },
                ],
            },
        ],
    },
    impressao: {
        context: "Modulo de impressao",
        current: "envio",
        primaryAction: {
            href: "#form-impressao",
            label: "Novo envio",
            icon: "upload_file",
        },
        sections: [
            {
                label: "Impressao",
                description: "Envios e acompanhamento",
                links: [
                    { key: "envio", href: "#nova-impressao", label: "Enviar atividade", icon: "print" },
                    { key: "historico", href: "#historico", label: "Historico", icon: "history" },
                    { key: "cotas", href: "#cotas", label: "Cotas e consumo", icon: "speed" },
                ],
            },
        ],
    },
    agendamento: {
        context: "Modulo de agendamento",
        current: "calendario",
        primaryAction: {
            href: "#novo-agendamento",
            label: "Agendar recurso",
            icon: "add_circle",
        },
        sections: [
            {
                label: "Agendamento",
                description: "Recursos e reservas",
                links: [
                    { key: "calendario", href: "#calendario", label: "Calendario", icon: "calendar_month" },
                    { key: "historico", href: "#historico", label: "Historico", icon: "history" },
                    { key: "recursos", href: "#recursos", label: "Recursos", icon: "inventory_2" },
                ],
            },
        ],
    },
};

export function getSideNavModuleConfig(moduleKey) {
    return SIDE_NAV_MODULES[moduleKey] || null;
}
