async function validarAcessoGestao() {
    const usuario = await fetchJson("/me", { headers });
    const cargo = normalizarCargoUsuario(usuario);
    const ehGestor = cargo === "ADMIN" || cargo === "COORDENADOR";
    if (!ehGestor) {
        window.location.href = "/servicos";
        return false;
    }
    return true;
}

function registrarEventosAbas() {
    listarBotoesAbasCoord().forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAbaCoordenacao(botao.dataset.coordTabTrigger);
        });
    });
}

function registrarEventosEditorDescricao() {
    const editor = obterEditorDescricao();
    if (!editor) return;

    editor.addEventListener("input", () => {
        sincronizarDescricaoEditor();
    });
    editor.addEventListener("keyup", salvarSelecaoDescricaoEditor);
    editor.addEventListener("mouseup", salvarSelecaoDescricaoEditor);
    editor.addEventListener("focus", salvarSelecaoDescricaoEditor);

    document.querySelectorAll("[data-rich-command]").forEach((botao) => {
        botao.addEventListener("mousedown", (event) => {
            event.preventDefault();
        });
        botao.addEventListener("click", () => {
            aplicarComandoDescricao(botao.dataset.richCommand);
        });
    });
}

function registrarEventosOcorrencias() {
    el("formFiltrosOcorrencias").addEventListener("submit", filtrarOcorrencias);
    el("formOcorrencia").addEventListener("submit", salvarOcorrencia);
    el("formOcorrencia").addEventListener("input", atualizarPreviewOcorrencia);
    el("formOcorrencia").addEventListener("change", atualizarPreviewOcorrencia);
    registrarEventosEditorDescricao();
    el("btnLimparFiltros").addEventListener("click", limparFiltrosOcorrencias);
    el("btnNovaOcorrencia").addEventListener("click", () => {
        const painelAberto = painelFormularioOcorrenciaAberto();
        if (painelAberto && !ocorrenciaEmEdicaoId) {
            limparFormularioOcorrencia();
            return;
        }

        limparFormularioOcorrencia({ manterAberto: true });
        mostrarPainelFormularioOcorrencia({ scroll: true });
        el("ocorrenciaBuscaEstudante").focus();
    });
    el("btnFecharPainelOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });
    el("btnCancelarEdicaoOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });

    el("ocorrenciaBuscaEstudante").addEventListener("input", () => {
        el("ocorrenciaEstudanteId").value = "";
        agendarBuscaEstudantes();
    });
    el("ocorrenciaBuscaEstudante").addEventListener("change", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("blur", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("focus", () => {
        atualizarSugestoesEstudantesBusca(true).catch((err) => setMensagemOcorrencias(err.message, true));
    });

    el("ocorrenciaBuscaProfessor").addEventListener("input", () => {
        el("ocorrenciaProfessorRequerenteId").value = "";
        atualizarSugestoesProfessoresBusca();
    });
    el("ocorrenciaBuscaProfessor").addEventListener("change", aplicarSelecaoProfessorPorTexto);
    el("ocorrenciaBuscaProfessor").addEventListener("blur", aplicarSelecaoProfessorPorTexto);
    el("ocorrenciaBuscaProfessor").addEventListener("focus", () => {
        atualizarSugestoesProfessoresBusca(true);
    });

    el("ocorrenciaDisciplina").addEventListener("input", () => {
        atualizarSugestoesDisciplinasBusca();
    });
    el("ocorrenciaDisciplina").addEventListener("change", aplicarSelecaoDisciplinaPorTexto);
    el("ocorrenciaDisciplina").addEventListener("blur", aplicarSelecaoDisciplinaPorTexto);
    el("ocorrenciaDisciplina").addEventListener("focus", () => {
        atualizarSugestoesDisciplinasBusca(true);
    });

    el("ocorrenciaBuscaRegimento").addEventListener("input", () => {
        atualizarSugestoesRegimentoBusca();
    });
    el("ocorrenciaBuscaRegimento").addEventListener("change", aplicarSelecaoRegimentoPorTexto);
    el("ocorrenciaBuscaRegimento").addEventListener("blur", aplicarSelecaoRegimentoPorTexto);
    el("ocorrenciaBuscaRegimento").addEventListener("focus", () => {
        atualizarSugestoesRegimentoBusca(true);
    });

    el("ocorrenciaTurmaId").addEventListener("change", () => {
        el("ocorrenciaEstudanteId").value = "";
        atualizarSelectAulasPorTurma(el("ocorrenciaTurmaId").value);
        agendarBuscaEstudantes();
        ocultarSugestoes("listaEstudantesBusca");
        atualizarPreviewOcorrencia();
    });
}

function registrarEventosRelatorios() {
    el("formRelatorioOcorrencias").addEventListener("submit", filtrarRelatorioOcorrencias);
    el("btnLimparRelatorioOcorrencias").addEventListener("click", limparFiltrosRelatorioOcorrencias);
}

function registrarEventosEstudantes() {
    el("formEstudante").addEventListener("submit", salvarEstudante);
    el("formImportarEstudantesCsv").addEventListener("submit", importarEstudantesArquivo);
    el("btnCancelarEdicaoEstudante").addEventListener("click", limparFormularioEstudante);
    el("btnBaixarModeloEstudantesCsv").addEventListener("click", baixarModeloEstudantesCsv);
    el("formFiltrosEstudantes").addEventListener("submit", filtrarEstudantes);
    el("btnLimparFiltrosEstudantes").addEventListener("click", limparFiltrosEstudantes);
    el("filtroEstudanteStatus").addEventListener("change", renderTabelaEstudantes);
}

function registrarEventosRegimento() {
    el("formLeiBaseLegal").addEventListener("submit", salvarLeiBaseLegal);
    el("formArtigoBaseLegal").addEventListener("submit", salvarArtigoBaseLegal);
    el("formIncisoBaseLegal").addEventListener("submit", salvarIncisoBaseLegal);
    el("formAlineaBaseLegal").addEventListener("submit", salvarAlineaBaseLegal);
    el("formImportarRegimentoCsv").addEventListener("submit", importarRegimentoCsv);
    el("btnCancelarEdicaoLeiBaseLegal").addEventListener("click", limparFormularioLeiBaseLegal);
    el("btnCancelarEdicaoArtigoBaseLegal").addEventListener("click", limparFormularioArtigoBaseLegal);
    el("btnCancelarEdicaoIncisoBaseLegal").addEventListener("click", limparFormularioIncisoBaseLegal);
    el("btnCancelarEdicaoAlineaBaseLegal").addEventListener("click", limparFormularioAlineaBaseLegal);
    el("btnBaixarModeloRegimentoCsv").addEventListener("click", baixarModeloRegimentoCsv);

    el("artigoBaseLegalLeiBusca").addEventListener("input", () => {
        atualizarSugestoesLeisBaseLegal();
    });
    el("artigoBaseLegalLeiBusca").addEventListener("change", aplicarSelecaoLeiBaseLegalPorTexto);
    el("artigoBaseLegalLeiBusca").addEventListener("blur", aplicarSelecaoLeiBaseLegalPorTexto);
    el("artigoBaseLegalLeiBusca").addEventListener("focus", () => {
        atualizarSugestoesLeisBaseLegal(true);
    });

    el("incisoBaseLegalArtigoBusca").addEventListener("input", () => {
        atualizarSugestoesArtigosBaseLegal();
    });
    el("incisoBaseLegalArtigoBusca").addEventListener("change", aplicarSelecaoArtigoBaseLegalPorTexto);
    el("incisoBaseLegalArtigoBusca").addEventListener("blur", aplicarSelecaoArtigoBaseLegalPorTexto);
    el("incisoBaseLegalArtigoBusca").addEventListener("focus", () => {
        atualizarSugestoesArtigosBaseLegal(true);
    });

    el("alineaBaseLegalIncisoBusca").addEventListener("input", () => {
        atualizarSugestoesIncisosBaseLegal();
    });
    el("alineaBaseLegalIncisoBusca").addEventListener("change", aplicarSelecaoIncisoBaseLegalPorTexto);
    el("alineaBaseLegalIncisoBusca").addEventListener("blur", aplicarSelecaoIncisoBaseLegalPorTexto);
    el("alineaBaseLegalIncisoBusca").addEventListener("focus", () => {
        atualizarSugestoesIncisosBaseLegal(true);
    });
}

function registrarEventosGerais() {
    document.addEventListener("click", (event) => {
        if (event.target.closest(".coordenacao-autocomplete-shell")) return;
        ocultarTodasSugestoes();
    });
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnIrAdmin").addEventListener("click", () => {
        window.location.href = "/admin";
    });
    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        const autorizado = await validarAcessoGestao();
        if (!autorizado) return;

        registrarEventosAbas();
        registrarEventosOcorrencias();
        registrarEventosRelatorios();
        registrarEventosEstudantes();
        registrarEventosRegimento();
        registrarEventosGerais();

        await carregarOpcoesOcorrencias();
        limparFormularioOcorrencia();
        limparFormularioEstudante();
        limparFormularioRegimento();
        renderDetalhesOcorrencia(null);
        renderRelatorioOcorrencias();
        ativarAbaCoordenacao(abaCoordAtiva);

        await Promise.all([
            carregarOcorrencias(),
            carregarEstudantes(),
            carregarCatalogosBaseLegal(),
            carregarRegimentoItens()
        ]);
    } catch (err) {
        setMensagemOcorrencias(err.message || "Erro ao carregar modulo de coordenacao.", true);
    }
}
