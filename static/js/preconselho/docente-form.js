function estudanteDocenteAtual() {
    return estadoDocente.estudantes.find((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId)) || null;
}

function registroDocenteAtual() {
    return estadoDocente.registros.find((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId)) || null;
}

function resolverEstudanteParaFormulario(estudanteId) {
    const estudanteEncontrado = estadoDocente.estudantes.find((item) => Number(item.estudante_id) === Number(estudanteId));
    if (estudanteEncontrado) {
        return estudanteEncontrado;
    }

    const registro = estadoDocente.registros.find((item) => Number(item.estudante_id) === Number(estudanteId));
    if (!registro) {
        return null;
    }

    return {
        estudante_id: Number(registro.estudante_id),
        nome: String(registro.estudante_nome || ""),
        turma_id: Number(registro.turma_id || 0),
        turma_nome: String(registro.turma_nome || ""),
        sinalizado: true,
        registro_id: Number(registro.id || 0),
        nivel_atencao: String(registro.nivel_atencao || ""),
        observacao_professor: String(registro.observacao_professor || ""),
        texto_gerado: String(registro.texto_gerado || ""),
        motivo_ids: Array.isArray(registro.motivo_ids) ? registro.motivo_ids : [],
        motivos: Array.isArray(registro.motivos) ? registro.motivos : [],
        pos_preconselho_recuperado: typeof registro.pos_preconselho_recuperado === "boolean"
            ? registro.pos_preconselho_recuperado
            : null,
        pos_preconselho_motivo_ids: Array.isArray(registro.pos_preconselho_motivo_ids)
            ? registro.pos_preconselho_motivo_ids
            : [],
        pos_preconselho_motivos: Array.isArray(registro.pos_preconselho_motivos)
            ? registro.pos_preconselho_motivos
            : [],
        pos_preconselho_observacao: String(registro.pos_preconselho_observacao || ""),
        estudante_em_rav: Boolean(registro.estudante_em_rav),
        rav_habilidade_ids: Array.isArray(registro.rav_habilidade_ids)
            ? registro.rav_habilidade_ids
            : [],
        rav_habilidades: Array.isArray(registro.rav_habilidades)
            ? registro.rav_habilidades
            : [],
        rav_acoes: String(registro.rav_acoes || "")
    };
}

function obterMotivosSelecionadosDocente() {
    return Array.from(document.querySelectorAll(".preconselho-motivo-checkbox:checked"))
        .map((checkbox) => Number(checkbox.value || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0);
}

function aplicarSelecaoMotivosDocente(motivoIds = []) {
    const ids = new Set((motivoIds || []).map((item) => Number(item)));
    document.querySelectorAll(".preconselho-motivo-checkbox").forEach((checkbox) => {
        checkbox.checked = ids.has(Number(checkbox.value || 0));
    });
}

function obterHabilidadesRavSelecionadasDocente() {
    return Array.from(document.querySelectorAll("[data-rav-habilidade-selecionada-id]"))
        .map((item) => Number(item.dataset.ravHabilidadeSelecionadaId || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0);
}

function aplicarSelecaoHabilidadesRavDocente(habilidadeIds = []) {
    renderizarHabilidadesRavDocente(habilidadeIds);
}

function filtrarHabilidadesRavDocente(termo = "", limite = 12) {
    const combo = comboDocenteAtual();
    const termoLimpo = String(termo || "").trim().toLowerCase();
    const selecionados = new Set(obterHabilidadesRavSelecionadasDocente());
    const habilidades = obterHabilidadesRavPorDisciplina(
        combo?.disciplina_id,
        false,
        estadoDocente.periodoId,
        combo?.turma_id
    )
        .filter((item) => !selecionados.has(Number(item.id || 0)));

    const filtradas = termoLimpo
        ? habilidades.filter((item) =>
            String(`${item.codigo || ""} ${item.descricao || ""}`).toLowerCase().includes(termoLimpo)
        )
        : habilidades;
    return filtradas.slice(0, limite);
}

function ocultarSugestoesHabilidadesRav() {
    const sugestoes = el("preconselhoRavSugestoesHabilidades");
    if (!sugestoes) {
        return;
    }
    sugestoes.innerHTML = "";
    sugestoes.hidden = true;
}

function renderizarSugestoesHabilidadesRav(forcar = false) {
    const sugestoes = el("preconselhoRavSugestoesHabilidades");
    const input = el("preconselhoRavBuscaHabilidade");
    if (!sugestoes || !input) {
        return;
    }

    const termo = String(input.value || "").trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoesHabilidadesRav();
        return;
    }

    const itens = filtrarHabilidadesRavDocente(termo);
    sugestoes.innerHTML = "";
    if (itens.length === 0) {
        const vazio = document.createElement("div");
        vazio.className = "preconselho-rav-suggestion-empty";
        vazio.textContent = "Nenhuma habilidade encontrada para este periodo, turma e disciplina.";
        sugestoes.appendChild(vazio);
        sugestoes.hidden = false;
        return;
    }

    itens.forEach((habilidade) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "preconselho-rav-suggestion";
        botao.dataset.ravHabilidadeId = String(Number(habilidade.id || 0));
        botao.textContent = [habilidade.codigo, habilidade.descricao].filter(Boolean).join(" - ");
        botao.addEventListener("click", () => {
            const ids = obterHabilidadesRavSelecionadasDocente();
            const habilidadeId = Number(habilidade.id || 0);
            if (habilidadeId > 0 && !ids.includes(habilidadeId)) {
                aplicarSelecaoHabilidadesRavDocente([...ids, habilidadeId]);
            }
            input.value = "";
            ocultarSugestoesHabilidadesRav();
            atualizarEstadoFormularioDocente();
            agendarPreviewDocente();
            input.focus();
        });
        sugestoes.appendChild(botao);
    });
    sugestoes.hidden = false;
}

function atualizarStatusSinalizacaoDocente({ possuiEstudante = false, possuiRegistro = false } = {}) {
    if (!possuiEstudante) {
        el("preconselhoStatusSelecionadoTitulo").textContent = "Nenhum estudante em edição";
        el("preconselhoStatusSelecionadoTexto").textContent =
            "Quando você selecionar um estudante e salvar o formulário, a sinalização será aplicada automaticamente.";
        return;
    }

    if (possuiRegistro) {
        el("preconselhoStatusSelecionadoTitulo").textContent = "Estudante já sinalizado";
        el("preconselhoStatusSelecionadoTexto").textContent =
            "Ao salvar novamente, o parecer será atualizado. Para remover a sinalização desta seleção, use Excluir registro.";
        return;
    }

    el("preconselhoStatusSelecionadoTitulo").textContent = "Sinalização automática no salvamento";
    el("preconselhoStatusSelecionadoTexto").textContent =
        "Este estudante será sinalizado automaticamente assim que o registro for salvo nesta turma, disciplina e período.";
}

function atualizarVisibilidadeRavDocente() {
    const campo = el("preconselhoRavRegistroField");
    const detalhes = el("preconselhoRavDetalhesField");
    const checkbox = el("preconselhoEstudanteEmRav");
    const visivel = periodoTemRav();
    if (campo) {
        campo.hidden = !visivel;
    }
    if (detalhes) {
        detalhes.hidden = !visivel || !Boolean(checkbox?.checked);
        if (detalhes.hidden) {
            ocultarSugestoesHabilidadesRav();
        }
    }
    if (!visivel && checkbox) {
        checkbox.checked = false;
        aplicarSelecaoHabilidadesRavDocente([]);
        if (el("preconselhoRavAcoes")) {
            el("preconselhoRavAcoes").value = "";
        }
    }
}

function modalRegistroDocenteAberto() {
    return Boolean(el("preconselhoModalEditor")) && !el("preconselhoModalEditor").hidden;
}

function resetarScrollModalRegistroDocente() {
    const modal = el("preconselhoModalEditor");
    const painel = el("preconselhoPainelEditor");
    const editor = painel?.querySelector(".preconselho-editor-scroll");

    [modal, painel, editor].forEach((container) => {
        if (!container) {
            return;
        }

        container.scrollTop = 0;
        if (typeof container.scrollTo === "function") {
            container.scrollTo({ top: 0, left: 0, behavior: "auto" });
        }
    });
}

function focarInicioModalRegistroDocente() {
    const painel = el("preconselhoPainelEditor");
    const controles = obterControlesFocaveisModal();
    const primeiroControle = controles.find((item) => item.closest("#formRegistroDocente")) || controles[0] || painel;
    if (!primeiroControle || typeof primeiroControle.focus !== "function") {
        return;
    }

    try {
        primeiroControle.focus({ preventScroll: true });
    } catch (_erro) {
        primeiroControle.focus();
    }
}

function obterControlesFocaveisModal() {
    const painel = el("preconselhoPainelEditor");
    if (!painel) return [];
    return Array.from(painel.querySelectorAll(
        'button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((item) => !item.hidden && item.getClientRects().length > 0);
}

function prenderFocoNoModal(event) {
    if (event.key !== "Tab" || !modalRegistroDocenteAberto()) return;
    const controles = obterControlesFocaveisModal();
    if (controles.length === 0) {
        event.preventDefault();
        el("preconselhoPainelEditor")?.focus();
        return;
    }
    const primeiro = controles[0];
    const ultimo = controles[controles.length - 1];
    if (!el("preconselhoPainelEditor")?.contains(document.activeElement)) {
        event.preventDefault();
        primeiro.focus();
    } else if (event.shiftKey && document.activeElement === primeiro) {
        event.preventDefault();
        ultimo.focus();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
        event.preventDefault();
        primeiro.focus();
    }
}

function definirEstadoSalvamentoModal(salvando) {
    modalDocenteSalvando = Boolean(salvando);
    el("preconselhoPainelEditor")?.setAttribute("aria-busy", salvando ? "true" : "false");
    const botaoRegistro = el("btnSalvarRegistroDocente");
    const botaoReavaliacao = el("btnSalvarReavaliacao");
    if (botaoRegistro) {
        botaoRegistro.textContent = salvando ? "Salvando..." : "Salvar registro";
        if (salvando) botaoRegistro.disabled = true;
    }
    if (botaoReavaliacao) {
        botaoReavaliacao.textContent = salvando ? "Salvando..." : "Salvar reavaliação";
        if (salvando) botaoReavaliacao.disabled = true;
    }
    if (!salvando) atualizarEstadoFormularioDocente();
}

