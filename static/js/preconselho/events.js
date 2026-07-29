function registrarEventos() {
    window.addEventListener("beforeunload", (event) => {
        if (!modalDocenteAlterado && !modalDocenteSalvando) return;
        event.preventDefault();
        event.returnValue = "";
    });
    document.querySelectorAll("[data-preconselho-tab-trigger]").forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAba(botao.dataset.preconselhoTabTrigger || "");
        });
        botao.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            const abas = Array.from(document.querySelectorAll("[data-preconselho-tab-trigger]"))
                .filter((item) => !item.hidden);
            const indiceAtual = abas.indexOf(botao);
            if (indiceAtual < 0 || abas.length === 0) return;
            event.preventDefault();
            let proximoIndice = indiceAtual;
            if (event.key === "Home") proximoIndice = 0;
            if (event.key === "End") proximoIndice = abas.length - 1;
            if (event.key === "ArrowRight") proximoIndice = (indiceAtual + 1) % abas.length;
            if (event.key === "ArrowLeft") proximoIndice = (indiceAtual - 1 + abas.length) % abas.length;
            const proxima = abas[proximoIndice];
            ativarAba(proxima.dataset.preconselhoTabTrigger || "");
            proxima.focus();
        });
    });

    el("btnIrAdmin").addEventListener("click", () => {
        window.location.href = "/admin";
    });

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });

    el("formPreconselhoDocentePeriodo").addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) return;
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("preconselhoPeriodoDocente").addEventListener("change", async () => {
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) {
            el("preconselhoPeriodoDocente").value = String(estadoDocente.periodoId || "");
            return;
        }
        estadoDocente.periodoId = Number(el("preconselhoPeriodoDocente").value || 0);
        await carregarPainelDocente();
    });

    el("listaMinhasTurmasDisciplinas").addEventListener("click", async (event) => {
        const botao = event.target.closest("button[data-turma-id][data-disciplina-id]");
        if (!botao) {
            return;
        }
        if (!fecharModalRegistroDocente({ restaurarFoco: false })) return;
        estadoDocente.turmaId = Number(botao.dataset.turmaId || 0);
        estadoDocente.disciplinaId = Number(botao.dataset.disciplinaId || 0);
        renderizarCombosDocente();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
        limparFormularioDocente();
        levarProfessorParaListaEstudantes();
    });

    el("formFiltrosEstudantesDocente").addEventListener("submit", async (event) => {
        event.preventDefault();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);
    });

    el("preconselhoBuscaEstudante").addEventListener("input", () => {
        if (timerBuscaEstudante) window.clearTimeout(timerBuscaEstudante);
        timerBuscaEstudante = window.setTimeout(() => {
            void carregarEstudantesDocente();
        }, 250);
    });

    el("preconselhoStatusEstudante").addEventListener("change", async () => {
        await carregarEstudantesDocente();
    });

    el("listaEstudantesDocente").addEventListener("click", (event) => {
        const botao = event.target.closest("button[data-estudante-id]");
        if (!botao) {
            return;
        }
        const estudante = resolverEstudanteParaFormulario(botao.dataset.estudanteId || 0);
        abrirModalComEstudante(estudante);
    });

    el("listaRegistrosDocente").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-registro']");
        if (botaoEditar) {
            const estudante = resolverEstudanteParaFormulario(botaoEditar.dataset.estudanteId || 0);
            abrirModalComEstudante(estudante);
            return;
        }

        const botaoExcluir = event.target.closest("button[data-action='excluir-registro']");
        if (botaoExcluir) {
            const registro = estadoDocente.registros.find((item) => Number(item.id) === Number(botaoExcluir.dataset.registroId || 0));
            if (!registro) {
                return;
            }
            if (!window.confirm("Deseja realmente excluir este registro do pré-conselho?")) {
                return;
            }
            limparMensagem("msgPreconselhoRegistro");
            try {
                await excluirRegistroDocente(registro.id);
                const painelAtualizado = await carregarPainelDocente();
                if (!painelAtualizado) {
                    definirMensagem("msgPreconselhoRegistro", "Registro excluído, mas o painel não foi recarregado corretamente.", true);
                    return;
                }
                definirMensagem("msgPreconselhoDocente", "Registro excluído com sucesso.");
                fecharModalRegistroDocente({ restaurarFoco: false });
            } catch (erro) {
                definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao excluir o registro.", true);
            }
        }
    });

    el("formRegistroDocente").addEventListener("submit", salvarRegistroDocente);
    el("formRegistroDocente").addEventListener("input", () => {
        if (modalRegistroDocenteAberto() && !modalDocenteSalvando) modalDocenteAlterado = true;
    });
    el("formRegistroDocente").addEventListener("change", () => {
        if (modalRegistroDocenteAberto() && !modalDocenteSalvando) modalDocenteAlterado = true;
    });
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => {
        radio.addEventListener("change", renderizarMotivosReavaliacao);
    });
    el("btnSalvarReavaliacao").addEventListener("click", salvarReavaliacaoDocente);
    el("btnLimparRegistroDocente").addEventListener("click", () => {
        limparMensagem("msgPreconselhoRegistro");
        limparFormularioDocente();
    });
    el("btnExcluirRegistroDocente").addEventListener("click", async () => {
        const registro = registroDocenteAtual();
        if (!registro) {
            definirMensagem("msgPreconselhoRegistro", "Não há registro salvo para excluir.", true);
            return;
        }
        if (!window.confirm("Deseja realmente excluir este registro do pré-conselho?")) {
            return;
        }
        limparMensagem("msgPreconselhoRegistro");
        try {
            await excluirRegistroDocente(registro.id);
            const painelAtualizado = await carregarPainelDocente();
            if (!painelAtualizado) {
                definirMensagem("msgPreconselhoRegistro", "Registro excluído, mas o painel não foi recarregado corretamente.", true);
                return;
            }
            definirMensagem("msgPreconselhoDocente", "Registro excluído com sucesso.");
            fecharModalRegistroDocente({ restaurarFoco: false });
        } catch (erro) {
            definirMensagem("msgPreconselhoRegistro", erro.message || "Erro ao excluir o registro.", true);
        }
    });

    el("btnFecharModalRegistroDocente").addEventListener("click", () => {
        fecharModalRegistroDocente();
    });
    el("btnFecharModalRegistroDocenteRodape").addEventListener("click", () => {
        fecharModalRegistroDocente();
    });
    el("preconselhoModalEditor").addEventListener("click", (event) => {
        if (event.target === event.currentTarget) {
            fecharModalRegistroDocente();
        }
    });
    document.addEventListener("keydown", (event) => {
        prenderFocoNoModal(event);
        if (event.key === "Escape" && modalRegistroDocenteAberto()) {
            fecharModalRegistroDocente();
        }
    });
    document.addEventListener("click", (event) => {
        if (!event.target.closest("#preconselhoRavDetalhesField")) {
            ocultarSugestoesHabilidadesRav();
        }
    });

    el("preconselhoNivelAtencao").addEventListener("change", agendarPreviewDocente);
    el("preconselhoObservacaoProfessor").addEventListener("input", agendarPreviewDocente);
    el("preconselhoMotivosDocente").addEventListener("change", (event) => {
        if (!event.target.closest(".preconselho-motivo-checkbox")) {
            return;
        }
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    el("preconselhoRavBuscaHabilidade").addEventListener("input", () => {
        renderizarSugestoesHabilidadesRav(false);
    });
    el("preconselhoRavBuscaHabilidade").addEventListener("focus", () => {
        renderizarSugestoesHabilidadesRav(true);
    });
    el("preconselhoRavBuscaHabilidade").addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        ocultarSugestoesHabilidadesRav();
    });
    el("preconselhoRavHabilidadesDocente").addEventListener("click", (event) => {
        const botao = event.target.closest("button[data-action='remover-habilidade-rav']");
        if (!botao) {
            return;
        }
        const removerId = Number(botao.dataset.habilidadeId || 0);
        const ids = obterHabilidadesRavSelecionadasDocente()
            .filter((habilidadeId) => Number(habilidadeId) !== removerId);
        aplicarSelecaoHabilidadesRavDocente(ids);
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    el("preconselhoEstudanteEmRav").addEventListener("change", () => {
        atualizarVisibilidadeRavDocente();
        atualizarEstadoFormularioDocente();
        agendarPreviewDocente();
    });
    el("preconselhoRavAcoes").addEventListener("input", agendarPreviewDocente);

    el("formConsolidacaoPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarConsolidacao();
    });
    el("preconselhoPeriodoConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoProfessorConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoTurmaConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoDisciplinaConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });
    el("preconselhoVersaoConsolidacao").addEventListener("change", async () => {
        await carregarConsolidacao();
    });

    el("preconselhoTurmaReavaliacao").addEventListener("change", async () => {
        estadoPainelReavaliacao.estudantesExpandidos.clear();
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
    });
    el("preconselhoProfessorReavaliacao").addEventListener("change", async () => {
        estadoPainelReavaliacao.estudantesExpandidos.clear();
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
    });
    el("listaPainelReavaliacao").addEventListener("click", (event) => {
        const editar = event.target.closest('button[data-action="editar-reavaliacao-gestao"]');
        if (editar) {
            event.stopPropagation();
            const registro = estadoPainelReavaliacao.registros.find((item) => Number(item.id) === Number(editar.dataset.registroId));
            if (!registro) return;
            estadoPainelReavaliacao.registroEmEdicaoId = Number(registro.id);
            estadoPainelReavaliacao.resultadoEmEdicao = resultadoRegistroReavaliacao(registro);
            renderizarPainelReavaliacao();
            el("listaPainelReavaliacao")?.querySelector(`[data-form-reavaliacao-id="${Number(registro.id)}"] input`)?.focus();
            return;
        }
        if (event.target.closest('button[data-action="cancelar-reavaliacao-gestao"]')) {
            estadoPainelReavaliacao.registroEmEdicaoId = null;
            estadoPainelReavaliacao.resultadoEmEdicao = "";
            renderizarPainelReavaliacao();
            return;
        }
        const botao = event.target.closest("button[data-estudante-reavaliacao]");
        if (!botao) return;
        const chave = String(botao.dataset.estudanteReavaliacao || "");
        if (estadoPainelReavaliacao.estudantesExpandidos.has(chave)) {
            estadoPainelReavaliacao.estudantesExpandidos.delete(chave);
        } else {
            estadoPainelReavaliacao.estudantesExpandidos.add(chave);
        }
        renderizarPainelReavaliacao();
        el("listaPainelReavaliacao")?.querySelector(`[data-estudante-reavaliacao="${CSS.escape(chave)}"]`)?.focus();
    });
    el("listaPainelReavaliacao").addEventListener("change", (event) => {
        if (event.target.name !== "resultadoGestaoReavaliacao") return;
        estadoPainelReavaliacao.resultadoEmEdicao = event.target.value;
        renderizarPainelReavaliacao();
        const registroId = Number(estadoPainelReavaliacao.registroEmEdicaoId);
        el("listaPainelReavaliacao")?.querySelector(`[data-form-reavaliacao-id="${registroId}"] [name="motivoGestaoReavaliacao"]`)?.focus();
    });
    el("listaPainelReavaliacao").addEventListener("submit", async (event) => {
        const form = event.target.closest("form[data-form-reavaliacao-id]");
        if (!form) return;
        event.preventDefault();
        await salvarReavaliacaoGestao(form);
    });

    el("btnCopiarTextoConsolidado").addEventListener("click", async () => {
        await copiarTexto(
            "preconselhoTextoConsolidado",
            "msgPreconselhoConsolidacao",
            "Texto consolidado copiado.",
            { html: () => criarHtmlTextoConsolidadoComEstudantesEmNegrito(estadoConsolidacao.dados) }
        );
    });

    el("formRelatorioPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRelatorio();
    });
    el("preconselhoPeriodoRelatorio").addEventListener("change", async () => {
        await carregarRelatorio();
    });

    el("formRavPreconselho").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRav();
    });
    el("preconselhoPeriodoRav").addEventListener("change", async () => {
        await carregarRav();
    });
    el("preconselhoTurmaRav").addEventListener("change", async () => {
        await carregarRav();
    });
    el("preconselhoModoRav").addEventListener("change", () => {
        renderizarRav();
    });

    el("formPeriodoPreconselho").addEventListener("submit", salvarPeriodo);
    el("btnLimparPeriodoPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoPeriodo");
        limparFormularioPeriodo();
    });

    el("tbodyPeriodosPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-periodo']");
        if (botaoEditar) {
            carregarPeriodoNoFormulario(botaoEditar.dataset.periodoId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-periodo']");
        if (botaoStatus) {
            await alternarStatusPeriodo(botaoStatus.dataset.periodoId, botaoStatus.dataset.status);
        }
    });

    el("formMotivoPreconselho").addEventListener("submit", salvarMotivo);
    el("btnLimparMotivoPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoMotivo");
        limparFormularioMotivo();
    });
    el("formMotivoReavaliacao").addEventListener("submit", salvarMotivoReavaliacao);
    el("btnLimparMotivoReavaliacao").addEventListener("click", limparFormularioMotivoReavaliacao);
    el("tbodyMotivosReavaliacao").addEventListener("click", async (event) => {
        const editar = event.target.closest("button[data-action='editar-motivo-reavaliacao']");
        const status = event.target.closest("button[data-action='status-motivo-reavaliacao']");
        if (editar) {
            const item = (contextoAtual.motivos_reavaliacao_admin || []).find((motivo) => Number(motivo.id) === Number(editar.dataset.id));
            if (!item) return;
            el("preconselhoMotivoReavaliacaoId").value = String(item.id);
            el("preconselhoMotivoReavaliacaoResultado").value = item.resultado;
            el("preconselhoMotivoReavaliacaoCodigo").value = item.codigo;
            el("preconselhoMotivoReavaliacaoCodigo").disabled = true;
            el("preconselhoMotivoReavaliacaoDescricao").value = item.descricao;
            el("preconselhoMotivoReavaliacaoOrdem").value = String(item.ordem || 0);
            return;
        }
        if (status) {
            const resposta = await fetchComAuth(`/preconselho/motivos-reavaliacao/${Number(status.dataset.id)}/status`, {
                method: "PUT", headers: headersJson,
                body: JSON.stringify({ ativo: Number(status.dataset.ativo) !== 1 })
            });
            if (!resposta.ok) {
                definirMensagem("msgMotivoReavaliacao", await obterMensagemErroResposta(resposta, "Não foi possível alterar o status."), true);
                return;
            }
            await carregarMotivosReavaliacaoAdmin();
            definirMensagem("msgMotivoReavaliacao", "Status atualizado.");
        }
    });

    el("formHabilidadeRavPreconselho").addEventListener("submit", salvarHabilidadeRav);
    el("btnLimparHabilidadeRavPreconselho").addEventListener("click", () => {
        limparMensagem("msgPreconselhoRavHabilidade");
        limparFormularioHabilidadeRav();
    });
    el("formImportarHabilidadesRavPreconselho").addEventListener("submit", importarHabilidadesRavJson);

    el("tbodyMotivosPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-motivo']");
        if (botaoEditar) {
            carregarMotivoNoFormulario(botaoEditar.dataset.motivoId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-motivo']");
        if (botaoStatus) {
            await alternarStatusMotivo(botaoStatus.dataset.motivoId, botaoStatus.dataset.ativo);
        }
    });

    el("tbodyHabilidadesRavPreconselho").addEventListener("click", async (event) => {
        const botaoEditar = event.target.closest("button[data-action='editar-habilidade-rav']");
        if (botaoEditar) {
            carregarHabilidadeRavNoFormulario(botaoEditar.dataset.habilidadeId);
            return;
        }

        const botaoStatus = event.target.closest("button[data-action='status-habilidade-rav']");
        if (botaoStatus) {
            await alternarStatusHabilidadeRav(botaoStatus.dataset.habilidadeId, botaoStatus.dataset.ativo);
        }
    });
}

