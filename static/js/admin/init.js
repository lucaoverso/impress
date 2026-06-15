function registrarEventos() {
    registrarEventosAbasAdmin();
    el("formTurma").addEventListener("submit", cadastrarTurma);
    el("turmaTurno").addEventListener("change", () => {
        atualizarJanelaAulasFormularioTurma({ forcarPadrao: true });
    });
    el("turmaAulaInicial").addEventListener("change", () => {
        atualizarJanelaAulasFormularioTurma();
    });
    el("formConfiguracaoAula").addEventListener("submit", salvarConfiguracaoAula);
    el("configAulaTipo").addEventListener("change", atualizarFormularioTipoConfiguracaoAula);
    el("btnCancelarEdicaoConfiguracaoAula").addEventListener("click", limparFormularioConfiguracaoAula);
    el("formDisciplina").addEventListener("submit", cadastrarDisciplina);
    el("formRecurso").addEventListener("submit", cadastrarRecurso);
    el("btnCancelarEdicaoRecurso").addEventListener("click", limparFormularioRecurso);
    el("btnUploadImagemRecurso").addEventListener("click", uploadImagemRecurso);
    el("btnRemoverImagemRecurso").addEventListener("click", removerImagemRecursoSelecionada);

    el("btnGerarRelatorios").addEventListener("click", carregarRelatorios);
    el("btnBuscarHistorico").addEventListener("click", buscarHistorico);

    if (usuarioEhAdmin) {
        registerAuditEvents();
        el("formProfessor").addEventListener("submit", cadastrarProfessor);
        el("formAtribuicaoDocente").addEventListener("submit", cadastrarAtribuicaoDocente);
        el("formImportarAtribuicoesDocentes").addEventListener("submit", importarAtribuicoesDocentesArquivo);
        el("formCotaRegras").addEventListener("submit", salvarRegrasCota);
        el("formStatusImpressao").addEventListener("submit", salvarStatusImpressao);
        el("profSenha").addEventListener("input", atualizarHintSenha);
        el("profCargo").addEventListener("change", () => {
            if (!professorEmEdicaoId) {
                aplicarModoFormularioProfessor(false);
            }
        });
        el("atribuicaoProfessor").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("atribuicaoDisciplina").addEventListener("change", carregarTurmasAtribuidasProfessorDisciplina);
        el("btnSelecionarTodasTurmasAtribuicao").addEventListener("click", selecionarTodasTurmasAtribuicao);
        el("btnLimparTurmasAtribuicao").addEventListener("click", limparSelecaoTurmasAtribuicao);
        el("btnBaixarModeloAtribuicoesJson").addEventListener("click", baixarModeloAtribuicoesJson);
        el("filtroAtribuicaoProfessor").addEventListener("change", carregarAtribuicoesDocentes);
        el("filtroAtribuicaoTurma").addEventListener("change", carregarAtribuicoesDocentes);
        el("filtroAtribuicaoDisciplina").addEventListener("change", carregarAtribuicoesDocentes);
        el("btnLimparFiltrosAtribuicoes").addEventListener("click", limparFiltrosAtribuicoesDocentes);
        el("btnCancelarEdicaoProfessor").addEventListener("click", limparFormularioProfessor);
        el("btnRecalcularCotas").addEventListener("click", recalcularCotasMes);
        el("mesReferenciaCota").addEventListener("change", carregarProfessores);
    }

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) {
            return;
        }

        aplicarPermissoesTela();

        if (usuarioEhAdmin) {
            el("mesReferenciaCota").value = mesAtualIso();
            await carregarOpcoesProfessor();
            await carregarContextoAtribuicoesDocentes();
            await carregarContextoTurmasDisciplinas();
            limparFormularioProfessor();
        }
        limparFormularioRecurso();
        registrarEventos();
        if (usuarioEhAdmin) {
            atualizarHintSenha();
        }
        atualizarFormularioTipoConfiguracaoAula();
        await carregarConfiguracoesAulasAdmin();
        atualizarJanelaAulasFormularioTurma({ forcarPadrao: true });

        const tarefas = [
            carregarStatusImpressaoAdmin(),
            carregarFilaAdmin(),
            buscarHistorico(),
            carregarRecursos(),
            carregarRelatorios(),
            carregarTurmasAdmin(),
            carregarDisciplinasAdmin()
        ];
        if (usuarioEhAdmin) {
            tarefas.push(
                loadAuditEvents(),
                carregarProfessores(),
                carregarCoordenadores(),
                carregarAtribuicoesDocentes(),
                carregarTurmasDisciplinasAdmin()
            );
        }
        await Promise.all(tarefas);
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}
