async function inicializarAdminAtribuicoes() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhAdmin) {
            window.location.href = "/admin/turmas";
            return;
        }

        await carregarContextoAtribuicoesDocentes();
        el("formAtribuicaoDocente").addEventListener("submit", cadastrarAtribuicaoDocente);
        el("formImportarAtribuicoesDocentes").addEventListener("submit", importarAtribuicoesDocentesArquivo);
        el("atribuicaoProfessor").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("atribuicaoDisciplina").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("btnSelecionarTodasTurmasAtribuicao").addEventListener("click", selecionarTodasTurmasAtribuicao);
        el("btnLimparTurmasAtribuicao").addEventListener("click", limparSelecaoTurmasAtribuicao);
        el("btnBaixarModeloAtribuicoesJson").addEventListener("click", baixarModeloAtribuicoesJson);
        ["filtroAtribuicaoProfessor", "filtroAtribuicaoTurma", "filtroAtribuicaoDisciplina"].forEach((id) => {
            el(id).addEventListener("change", carregarAtribuicoesDocentes);
        });
        el("btnLimparFiltrosAtribuicoes").addEventListener("click", limparFiltrosAtribuicoesDocentes);
        await carregarAtribuicoesDocentes();
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message || "Falha ao carregar as atribuições.", true);
    }
}

inicializarAdminAtribuicoes();
