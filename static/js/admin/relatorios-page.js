async function inicializarAdminRelatorios() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) return;
        el("btnGerarRelatorios").addEventListener("click", carregarRelatorios);
        await carregarRelatorios();
    } catch (err) {
        setMensagem("msgRelatorios", err.message || "Falha ao carregar os relatórios.", true);
    }
}

inicializarAdminRelatorios();
