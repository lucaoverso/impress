async function inicializarAdminProfessores() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhAdmin) {
            window.location.href = "/admin/turmas";
            return;
        }

        el("mesReferenciaCota").value = mesAtualIso();
        await carregarOpcoesProfessor();
        limparFormularioProfessor();

        el("formProfessor").addEventListener("submit", cadastrarProfessor);
        el("formCotaRegras").addEventListener("submit", salvarRegrasCota);
        el("profSenha").addEventListener("input", atualizarHintSenha);
        el("profCargo").addEventListener("change", () => {
            if (!professorEmEdicaoId) aplicarModoFormularioProfessor(false);
        });
        el("btnCancelarEdicaoProfessor").addEventListener("click", limparFormularioProfessor);
        el("btnRecalcularCotas").addEventListener("click", recalcularCotasMes);
        el("mesReferenciaCota").addEventListener("change", carregarProfessores);

        atualizarHintSenha();
        await Promise.all([carregarProfessores(), carregarCoordenadores()]);
    } catch (err) {
        setMensagem("msgProfessor", err.message || "Falha ao carregar os usuários.", true);
    }
}

inicializarAdminProfessores();
