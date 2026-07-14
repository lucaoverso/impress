async function inicializarAdminRecursos() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) return;

        document.querySelectorAll("[data-admin-only='true']").forEach((elemento) => {
            elemento.hidden = !usuarioEhAdmin;
        });

        limparFormularioRecurso();
        el("formRecurso")?.addEventListener("submit", cadastrarRecurso);
        el("btnCancelarEdicaoRecurso")?.addEventListener("click", limparFormularioRecurso);
        el("btnUploadImagemRecurso")?.addEventListener("click", uploadImagemRecurso);
        el("btnRemoverImagemRecurso")?.addEventListener("click", removerImagemRecursoSelecionada);
        await carregarRecursos();
    } catch (err) {
        setMensagem("msgRecurso", err.message || "Falha ao carregar os recursos.", true);
    }
}

inicializarAdminRecursos();
