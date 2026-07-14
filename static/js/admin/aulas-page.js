async function inicializarAdminAulas() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) return;

        document.querySelectorAll("[data-admin-only='true']").forEach((elemento) => {
            elemento.hidden = !usuarioEhAdmin;
        });

        limparFormularioConfiguracaoAula();
        el("configAulaTipo")?.addEventListener("change", atualizarFormularioTipoConfiguracaoAula);
        el("formConfiguracaoAula")?.addEventListener("submit", salvarConfiguracaoAula);
        el("btnCancelarEdicaoConfiguracaoAula")?.addEventListener("click", limparFormularioConfiguracaoAula);
        await carregarConfiguracoesAulasAdmin();
    } catch (err) {
        setMensagem("msgConfiguracaoAula", err.message || "Falha ao carregar a grade de aulas.", true);
    }
}

inicializarAdminAulas();
