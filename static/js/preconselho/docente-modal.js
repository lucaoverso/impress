function abrirModalRegistroDocente() {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return;
    }

    atualizarModoDocente();
    if (modal.hidden) {
        const focoAtual = document.activeElement;
        ultimoElementoFocadoModal = focoAtual && typeof focoAtual.focus === "function" ? focoAtual : null;
    }
    modal.hidden = false;
    document.body.classList.add("preconselho-modal-open");
    window.requestAnimationFrame(() => {
        resetarScrollModalRegistroDocente();
        focarInicioModalRegistroDocente();
    });
}

function fecharModalRegistroDocente({ limparFormulario = true, restaurarFoco = true, forcar = false } = {}) {
    const modal = el("preconselhoModalEditor");
    if (!modal) {
        return false;
    }
    if (modalDocenteSalvando && !forcar) {
        return false;
    }
    if (!forcar && modalDocenteAlterado && !window.confirm("Descartar as alterações não salvas?")) {
        return false;
    }

    modal.hidden = true;
    document.body.classList.remove("preconselho-modal-open");

    if (limparFormulario) {
        limparMensagem("msgPreconselhoRegistro");
        limparFormularioDocente();
    }

    if (restaurarFoco && ultimoElementoFocadoModal && typeof ultimoElementoFocadoModal.focus === "function") {
        ultimoElementoFocadoModal.focus();
    }
    ultimoElementoFocadoModal = null;
    modalDocenteAlterado = false;
    return true;
}

function abrirModalComEstudante(estudante) {
    if (!estudante) {
        return;
    }

    preencherFormularioComEstudante(estudante);
    abrirModalRegistroDocente();
}

function limparFormularioDocente() {
    estadoDocente.estudanteId = null;
    el("preconselhoRegistroAtualId").value = "";
    el("preconselhoEstudanteAtualId").value = "";
    el("preconselhoEstudanteSelecionadoNome").textContent = "Selecione um estudante para iniciar.";
    el("preconselhoEstudanteSelecionadoMeta").textContent = "Os dados do registro aparecerão aqui.";
    el("preconselhoSinalizarEstudante").checked = false;
    el("preconselhoNivelAtencao").value = "";
    el("preconselhoObservacaoProfessor").value = "";
    el("preconselhoEstudanteEmRav").checked = false;
    el("preconselhoRavBuscaHabilidade").value = "";
    el("preconselhoRavAcoes").value = "";
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => { radio.checked = false; });
    el("preconselhoObservacaoReavaliacao").value = "";
    el("preconselhoMotivosReavaliacao").innerHTML = "";
    aplicarSelecaoMotivosDocente([]);
    aplicarSelecaoHabilidadesRavDocente([]);
    renderizarHabilidadesRavDocente();
    el("preconselhoTextoPreview").value = "";
    el("preconselhoPreviewAjuda").textContent = "Selecione um estudante e marque os motivos para gerar a pré-visualização.";
    atualizarStatusSinalizacaoDocente();
    atualizarVisibilidadeRavDocente();
    atualizarEstadoFormularioDocente();
    renderizarEstudantesDocente();
    modalDocenteAlterado = false;
}

function definirBotoesDocenteHabilitados() {
    const periodo = periodoDocenteAtual();
    const registro = registroDocenteAtual();
    const possuiEstudante = Number(estadoDocente.estudanteId || 0) > 0;
    const podeEditar = Boolean(periodo?.editavel);
    const camposHabilitados = possuiEstudante && podeEditar;
    const podeReavaliar = possuiEstudante && Boolean(registro) && periodoEmReavaliacao(periodo);

    el("preconselhoNivelAtencao").disabled = !camposHabilitados;
    el("preconselhoObservacaoProfessor").disabled = !camposHabilitados;
    el("preconselhoEstudanteEmRav").disabled = !camposHabilitados || !periodoTemRav(periodo);
    el("preconselhoRavAcoes").disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    el("preconselhoRavBuscaHabilidade").disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    document.querySelectorAll(".preconselho-motivo-checkbox").forEach((checkbox) => {
        checkbox.disabled = !camposHabilitados;
    });
    document.querySelectorAll("[data-action='remover-habilidade-rav']").forEach((botao) => {
        botao.disabled = !camposHabilitados || !periodoTemRav(periodo) || !Boolean(el("preconselhoEstudanteEmRav").checked);
    });
    el("btnSalvarRegistroDocente").disabled = modalDocenteSalvando || !possuiEstudante || !podeEditar;
    el("btnExcluirRegistroDocente").disabled = !registro || !podeEditar;
    el("preconselhoReavaliacaoField").hidden = !periodoEmReavaliacao(periodo) || !registro;
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"], .preconselho-review-reason').forEach((campo) => {
        campo.disabled = !podeReavaliar;
    });
    el("preconselhoObservacaoReavaliacao").disabled = !podeReavaliar;
    el("btnSalvarReavaliacao").disabled = modalDocenteSalvando || !podeReavaliar;

    if (!possuiEstudante) {
        el("preconselhoPreviewAjuda").textContent = "Selecione um estudante para preencher o formulário.";
        return;
    }
    if (!podeEditar && !podeReavaliar) {
        el("preconselhoPreviewAjuda").textContent = "O período selecionado está fechado para edição do professor. Os dados permanecem disponíveis para consulta.";
        return;
    }
    if (obterMotivosSelecionadosDocente().length === 0) {
        el("preconselhoPreviewAjuda").textContent = "Selecione ao menos um motivo para gerar a pré-visualização.";
        return;
    }

    el("preconselhoPreviewAjuda").textContent =
        "O texto é atualizado automaticamente conforme os motivos e a observação selecionados.";
}

function renderizarMotivosReavaliacao() {
    const container = el("preconselhoMotivosReavaliacao");
    const resultado = document.querySelector('[name="preconselhoResultadoReavaliacao"]:checked')?.value || "";
    const registro = registroDocenteAtual();
    const catalogo = contextoAtual?.motivos_pos_preconselho?.[resultado] || [];
    const selecionados = new Set(registro?.pos_preconselho_motivo_ids || []);
    container.innerHTML = catalogo.length
        ? catalogo.map((motivo) => `<label><input class="preconselho-review-reason" type="checkbox" value="${escaparHtml(motivo.id || "")}" ${selecionados.has(String(motivo.id || "")) ? "checked" : ""}> <span>${escaparHtml(motivo.descricao || "")}</span></label>`).join("")
        : (resultado ? '<p class="pcpi-hint">Nenhum motivo disponível.</p>' : "");
    atualizarEstadoFormularioDocente();
}

function atualizarEstadoFormularioDocente() {
    definirBotoesDocenteHabilitados();
}

