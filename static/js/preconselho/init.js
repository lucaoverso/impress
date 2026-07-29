async function iniciarModulo() {
    registrarEventos();
    limparFormularioPeriodo();
    limparFormularioMotivo();
    limparFormularioHabilidadeRav();
    try {
        await carregarUsuario();
        await carregarContexto();
        await carregarPainelInicial();
    } catch (erro) {
        definirMensagem("msgPreconselhoDocente", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoConsolidacao", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoReavaliacao", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
        definirMensagem("msgPreconselhoRelatorio", erro.message || "Não foi possível carregar o módulo de pré-conselho.", true);
    }
}

iniciarModulo();
