async function inicializarAdminImpressao() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) return;

        document.querySelectorAll("[data-admin-only='true']").forEach((elemento) => {
            elemento.hidden = !usuarioEhAdmin;
        });

        el("btnBuscarHistorico")?.addEventListener("click", buscarHistorico);
        if (usuarioEhAdmin) {
            el("formStatusImpressao")?.addEventListener("submit", salvarStatusImpressao);
            el("formImpressora")?.addEventListener("submit", cadastrarImpressora);
        }

        const tarefas = [
            carregarStatusImpressaoAdmin(),
            carregarFilaAdmin(),
            buscarHistorico(),
        ];
        if (usuarioEhAdmin) tarefas.push(carregarImpressorasAdmin());
        await Promise.all(tarefas);
    } catch (err) {
        setMensagem("msgRelatorios", err.message || "Falha ao carregar a gestão de impressão.", true);
    }
}

inicializarAdminImpressao();
