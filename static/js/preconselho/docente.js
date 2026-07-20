function renderizarResumoDocente() {
    const combos = Array.isArray(estadoDocente.combos) ? estadoDocente.combos : [];
    const totalCombos = combos.length;
    const totalSinalizados = combos.reduce((acc, item) => acc + Number(item.total_sinalizados || 0), 0);
    const totalPendentes = combos.reduce((acc, item) => acc + Number(item.total_pendentes || 0), 0);

    el("preconselhoResumoTotalTurmas").textContent = String(totalCombos);
    el("preconselhoResumoTotalSinalizados").textContent = String(totalSinalizados);
    el("preconselhoResumoTotalPendentes").textContent = String(totalPendentes);
}

function renderizarCombosDocente() {
    const container = el("listaMinhasTurmasDisciplinas");
    if (!container) {
        return;
    }

    if (!estadoDocente.periodoId) {
        container.innerHTML = '<p class="preconselho-empty-state">Selecione um período para carregar sua carga.</p>';
        return;
    }

    if (!Array.isArray(estadoDocente.combos) || estadoDocente.combos.length === 0) {
        container.innerHTML = '<p class="preconselho-empty-state">Nenhuma turma ou disciplina foi localizada para a sua carga neste período.</p>';
        return;
    }

    container.innerHTML = estadoDocente.combos.map((item) => {
        const ativo = Number(item.turma_id) === Number(estadoDocente.turmaId) && Number(item.disciplina_id) === Number(estadoDocente.disciplinaId);
        return `
            <button type="button" class="preconselho-selection-card ${ativo ? "is-active" : ""}"
                aria-pressed="${ativo ? "true" : "false"}"
                data-turma-id="${Number(item.turma_id)}"
                data-disciplina-id="${Number(item.disciplina_id)}">
                <strong>${escaparHtml(item.turma_nome || "")} • ${escaparHtml(item.disciplina_nome || "")}</strong>
                <span>${Number(item.total_estudantes || 0)} estudante(s)</span>
                <small>${Number(item.total_sinalizados || 0)} sinalizado(s)</small>
            </button>
        `;
    }).join("");
}

function levarProfessorParaListaEstudantes() {
    const secao = el("preconselhoSecaoEstudantes");
    if (!secao || !window.matchMedia("(max-width: 980px)").matches) return;

    const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => {
        secao.scrollIntoView({
            behavior: reduzirMovimento ? "auto" : "smooth",
            block: "start"
        });
    });
}

function renderizarEstudantesDocente() {
    const lista = el("listaEstudantesDocente");
    if (!lista) {
        return;
    }

    const combo = comboDocenteAtual();
    if (!combo) {
        lista.innerHTML = criarEstadoVazio("Escolha uma turma e disciplina para listar os estudantes.");
        el("preconselhoResumoEstudantesDocente").textContent = "A lista será carregada assim que uma combinação da carga for selecionada.";
        return;
    }

    if (!Array.isArray(estadoDocente.estudantes) || estadoDocente.estudantes.length === 0) {
        lista.innerHTML = criarEstadoVazio(
            estadoDocente.modo === "reavaliacao"
                ? "Nenhum estudante foi sinalizado nesta turma e disciplina."
                : "Nenhum estudante encontrado para os filtros aplicados."
        );
        el("preconselhoResumoEstudantesDocente").textContent = `${combo.turma_nome} • ${combo.disciplina_nome}`;
        return;
    }

    const trilho = lista.closest(".preconselho-rail-scroll");
    const scrollAnterior = trilho?.scrollTop || 0;
    lista.innerHTML = estadoDocente.estudantes.map((item) => {
        const selecionado = Number(item.estudante_id) === Number(estadoDocente.estudanteId);
        const nivel = rotuloNivelAtencao(item.nivel_atencao);
        const statusReavaliacao = item.pos_preconselho_recuperado === true
            ? "Recuperado"
            : (item.pos_preconselho_recuperado === false ? "Ficou para o conselho" : "Reavaliação pendente");
        const classeStatusReavaliacao = item.pos_preconselho_recuperado === true
            ? "pcpi-chip-status-recuperado"
            : (item.pos_preconselho_recuperado === false ? "pcpi-chip-status-conselho" : "pcpi-chip-status-pendente");
        const classeCardReavaliacao = estadoDocente.modo === "reavaliacao"
            ? (item.pos_preconselho_recuperado === true
                ? "preconselho-card-status-recuperado"
                : (item.pos_preconselho_recuperado === false
                    ? "preconselho-card-status-conselho"
                    : "preconselho-card-status-pendente"))
            : "";
        const descricaoItem = estadoDocente.modo === "reavaliacao"
            ? ""
            : (item.sinalizado
                ? `${item.motivos.length} motivo(s) selecionado(s)`
                    + (nivel ? ` • Atenção ${nivel}` : "")
                    + (item.motivos.length ? `\n${item.motivos.map((m) => `- ${m.descricao || ""}`).join("\n")}` : "")
                : "Clique para abrir um relato.");
        return `
            <li class="pcpi-item ${item.sinalizado ? "pcpi-item-manual" : "pcpi-item-automatico"} ${classeCardReavaliacao}">
                <button type="button" class="preconselho-list-button ${selecionado ? "is-active" : ""}" aria-pressed="${selecionado ? "true" : "false"}" data-estudante-id="${Number(item.estudante_id)}">
                    <span class="preconselho-list-button-top">
                        <strong>${escaparHtml(item.nome || "")}</strong>
                        <span class="pcpi-tag-group">
                            ${estadoDocente.modo === "registro" ? `<span class="pcpi-chip ${item.sinalizado ? "pcpi-chip-manual" : "pcpi-chip-automatico"}">${item.sinalizado ? "Sinalizado" : "Estudante Ok"}</span>` : ""}
                            ${periodoEmReavaliacao() && item.sinalizado ? `<span class="pcpi-chip ${classeStatusReavaliacao}">${escaparHtml(statusReavaliacao)}</span>` : ""}
                        </span>
                    </span>
                    ${descricaoItem ? `<span class="pcpi-item-note">${escaparHtml(descricaoItem)}</span>` : ""}
                </button>
            </li>
        `;
    }).join("");
    if (trilho) trilho.scrollTop = scrollAnterior;

    const total = estadoDocente.estudantes.length;
    const totalSinalizados = estadoDocente.estudantes.filter((item) => item.sinalizado).length;
    el("preconselhoResumoEstudantesDocente").textContent = estadoDocente.modo === "reavaliacao"
        ? `${combo.turma_nome} • ${combo.disciplina_nome} • ${total} estudante(s) para reavaliação.`
        : `${combo.turma_nome} • ${combo.disciplina_nome} • ${total} estudante(s), ${totalSinalizados} sinalizado(s).`;
}

function aplicarReavaliacaoNoEstado(registroAtualizado) {
    const registroAnterior = estadoDocente.registros.find(
        (item) => Number(item.id) === Number(registroAtualizado?.id)
    ) || {};
    const registro = {
        ...registroAnterior,
        ...registroAtualizado,
        motivo_ids: Array.isArray(registroAtualizado?.motivo_ids) ? registroAtualizado.motivo_ids : (registroAnterior.motivo_ids || []),
        motivos: Array.isArray(registroAtualizado?.motivos) ? registroAtualizado.motivos : (registroAnterior.motivos || []),
        pos_preconselho_motivo_ids: Array.isArray(registroAtualizado?.pos_preconselho_motivo_ids) ? registroAtualizado.pos_preconselho_motivo_ids : [],
        pos_preconselho_motivos: Array.isArray(registroAtualizado?.pos_preconselho_motivos) ? registroAtualizado.pos_preconselho_motivos : [],
    };
    estadoDocente.registros = estadoDocente.registros.map((item) =>
        Number(item.id) === Number(registro.id) ? registro : item
    );
    estadoDocente.estudantes = estadoDocente.estudantes.map((item) =>
        Number(item.estudante_id) === Number(registro.estudante_id)
            ? {
                ...item,
                pos_preconselho_recuperado: registro.pos_preconselho_recuperado,
                pos_preconselho_motivo_ids: registro.pos_preconselho_motivo_ids,
                pos_preconselho_motivos: registro.pos_preconselho_motivos,
                pos_preconselho_observacao: registro.pos_preconselho_observacao,
            }
            : item
    );
    renderizarEstudantesDocente();
    renderizarRegistrosDocente();
}

function formatarMotivosRegistro(motivos = []) {
    return motivos.map((item) => String(item.descricao || "")).filter(Boolean).join(", ");
}

function formatarListaNatural(valores = []) {
    const itens = Array.from(new Set(
        (Array.isArray(valores) ? valores : [])
            .map((item) => String(item || "").trim())
            .filter(Boolean)
    ));

    if (itens.length === 0) {
        return "";
    }
    if (itens.length === 1) {
        return itens[0];
    }
    if (itens.length === 2) {
        return `${itens[0]} e ${itens[1]}`;
    }
    return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

function renderizarRegistrosDocente() {
    const lista = el("listaRegistrosDocente");
    if (!lista) {
        return;
    }

    const itens = Array.isArray(estadoDocente.registros) ? estadoDocente.registros : [];
    el("preconselhoResumoRegistrosDocente").textContent = `${itens.length} ${itens.length === 1 ? "registro" : "registros"}`;

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum registro salvo para a turma e disciplina selecionadas.");
        return;
    }

    lista.innerHTML = itens.map((item) => `
        <li class="pcpi-item pcpi-item-manual">
            <div class="pcpi-checkbox-row">
                <div class="pcpi-item-body">
                    <div class="pcpi-item-top">
                        <strong>${escaparHtml(item.estudante_nome || "")}</strong>
                        <div class="pcpi-tag-group">
                            ${item.nivel_atencao ? `<span class="pcpi-chip">${escaparHtml(rotuloNivelAtencao(item.nivel_atencao))}</span>` : ""}
                            ${item.estudante_em_rav ? '<span class="pcpi-chip pcpi-chip-automatico">RAV</span>' : ""}
                            <span class="pcpi-chip pcpi-chip-manual">Salvo</span>
                        </div>
                    </div>
                    <p class="pcpi-item-line">${escaparHtml(item.disciplina_nome || "")}</p>
                    <p class="pcpi-item-note">${escaparHtml(formatarMotivosRegistro(item.motivos || []))}</p>
                    ${item.texto_gerado ? `<p class="pcpi-item-note is-secondary">${escaparHtml(item.texto_gerado)}</p>` : ""}
                    <div class="preconselho-item-actions">
                        <button type="button" class="preconselho-btn-link" data-action="editar-registro" data-estudante-id="${Number(item.estudante_id)}">Editar</button>
                        ${item.editavel ? `<button type="button" class="preconselho-btn-link" data-action="excluir-registro" data-registro-id="${Number(item.id)}">Excluir</button>` : ""}
                    </div>
                </div>
            </div>
        </li>
    `).join("");
}

function preencherFormularioComEstudante(estudante) {
    if (!estudante) {
        limparFormularioDocente();
        return;
    }

    estadoDocente.estudanteId = Number(estudante.estudante_id);
    const registro = registroDocenteAtual();

    el("preconselhoRegistroAtualId").value = registro ? String(registro.id) : "";
    el("preconselhoEstudanteAtualId").value = String(estudante.estudante_id);
    el("preconselhoEstudanteSelecionadoNome").textContent = estudante.nome || "Estudante";
    const resultadoReavaliacao = estudante.pos_preconselho_recuperado === true
        ? "recuperado"
        : (estudante.pos_preconselho_recuperado === false ? "nao_recuperado" : "");
    el("preconselhoEstudanteSelecionadoMeta").textContent = estadoDocente.modo === "reavaliacao"
        ? `${estudante.turma_nome || ""} • ${comboDocenteAtual()?.disciplina_nome || ""} • ${resultadoReavaliacao ? "Reavaliação já registrada" : "Reavaliação pendente"}.`
        : estudante.sinalizado
        ? `${estudante.turma_nome || ""} • Registro já salvo para a seleção atual.`
        : `${estudante.turma_nome || ""} • Ainda não sinalizado neste período e disciplina.`;
    el("preconselhoSinalizarEstudante").checked = true;
    el("preconselhoNivelAtencao").value = String(estudante.nivel_atencao || "");
    el("preconselhoObservacaoProfessor").value = String(estudante.observacao_professor || "");
    document.querySelectorAll('[name="preconselhoResultadoReavaliacao"]').forEach((radio) => {
        radio.checked = radio.value === resultadoReavaliacao;
    });
    el("preconselhoObservacaoReavaliacao").value = String(estudante.pos_preconselho_observacao || "");
    el("preconselhoEstudanteEmRav").checked = periodoTemRav() && Boolean(estudante.estudante_em_rav);
    el("preconselhoRavBuscaHabilidade").value = "";
    el("preconselhoRavAcoes").value = String(estudante.rav_acoes || "");
    aplicarSelecaoMotivosDocente(estudante.motivo_ids || []);
    renderizarHabilidadesRavDocente();
    aplicarSelecaoHabilidadesRavDocente(estudante.rav_habilidade_ids || []);
    renderizarMotivosReavaliacao();
    atualizarStatusSinalizacaoDocente({
        possuiEstudante: true,
        possuiRegistro: Boolean(estudante.sinalizado),
    });
    atualizarVisibilidadeRavDocente();

    renderizarEstudantesDocente();
    atualizarEstadoFormularioDocente();
    void atualizarPreviewDocente();
    modalDocenteAlterado = false;
}

async function atualizarPreviewDocente() {
    const possuiEstudante = Number(estadoDocente.estudanteId || 0) > 0;
    const motivoIds = obterMotivosSelecionadosDocente();
    const estudante = resolverEstudanteParaFormulario(estadoDocente.estudanteId);
    const combo = comboDocenteAtual();

    if (!possuiEstudante) {
        el("preconselhoTextoPreview").value = "";
        atualizarEstadoFormularioDocente();
        return;
    }

    if (motivoIds.length === 0) {
        el("preconselhoTextoPreview").value = "";
        atualizarEstadoFormularioDocente();
        return;
    }

    try {
        const resposta = await fetchComAuth("/preconselho/texto/preview", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                motivo_ids: motivoIds,
                observacao_professor: String(el("preconselhoObservacaoProfessor").value || "").trim(),
                nivel_atencao: String(el("preconselhoNivelAtencao").value || "").trim() || null,
                pos_preconselho_recuperado: null,
                pos_preconselho_motivo_ids: [],
                pos_preconselho_observacao: "",
                estudante_em_rav: periodoTemRav() && Boolean(el("preconselhoEstudanteEmRav").checked),
                rav_habilidade_ids: obterHabilidadesRavSelecionadasDocente(),
                rav_acoes: String(el("preconselhoRavAcoes").value || "").trim(),
                estudante_nome: String(estudante?.nome || "").trim(),
                estudante_sexo: estudante?.sexo || null,
                periodo_id: Number(estadoDocente.periodoId || 0) || null,
                turma_id: Number(combo?.turma_id || 0) || null,
                disciplina_id: Number(combo?.disciplina_id || 0) || null,
                disciplina_nome: String(combo?.disciplina_nome || "").trim()
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível gerar a pré-visualização."));
        }

        const dados = await resposta.json();
        el("preconselhoTextoPreview").value = String(dados?.texto || "");
        atualizarEstadoFormularioDocente();
    } catch (erro) {
        el("preconselhoTextoPreview").value = "";
        el("preconselhoPreviewAjuda").textContent = erro.message || "Não foi possível gerar a pré-visualização.";
    }
}

function agendarPreviewDocente() {
    if (timerPreviewDocente) {
        window.clearTimeout(timerPreviewDocente);
    }
    timerPreviewDocente = window.setTimeout(() => {
        void atualizarPreviewDocente();
    }, 250);
}

async function carregarCombosDocente() {
    if (!estadoDocente.periodoId) {
        estadoDocente.combos = [];
        renderizarResumoDocente();
        renderizarCombosDocente();
        return;
    }

    const resposta = await fetchComAuth(`/preconselho/minhas-turmas-disciplinas?periodo_id=${Number(estadoDocente.periodoId)}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar as turmas e disciplinas do professor."));
    }

    estadoDocente.combos = await resposta.json();
    const comboAtual = comboDocenteAtual();
    if (!comboAtual && estadoDocente.combos.length > 0) {
        estadoDocente.turmaId = Number(estadoDocente.combos[0].turma_id);
        estadoDocente.disciplinaId = Number(estadoDocente.combos[0].disciplina_id);
    } else if (estadoDocente.combos.length === 0) {
        estadoDocente.turmaId = null;
        estadoDocente.disciplinaId = null;
    }

    renderizarResumoDocente();
    renderizarCombosDocente();
}

async function carregarEstudantesDocente() {
    const combo = comboDocenteAtual();
    if (!combo || !estadoDocente.periodoId) {
        estadoDocente.estudantes = [];
        renderizarEstudantesDocente();
        return;
    }

    atualizarModoDocente();
    const params = new URLSearchParams({
        periodo_id: String(estadoDocente.periodoId),
        turma_id: String(combo.turma_id),
        disciplina_id: String(combo.disciplina_id),
        q: String(el("preconselhoBuscaEstudante").value || "").trim(),
        status: estadoDocente.modo === "reavaliacao"
            ? "sinalizados"
            : String(el("preconselhoStatusEstudante").value || "todos")
    });

    if (buscaEstudanteController) buscaEstudanteController.abort();
    buscaEstudanteController = new AbortController();
    const sequenciaAtual = ++buscaEstudanteSequencia;
    let resposta;
    try {
        resposta = await fetchComAuth(`/preconselho/estudantes?${params.toString()}`, {
            headers,
            signal: buscaEstudanteController.signal
        });
    } catch (erro) {
        if (erro?.name === "AbortError") return;
        throw erro;
    }
    if (sequenciaAtual !== buscaEstudanteSequencia) return;
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os estudantes."));
    }

    const estudantes = await resposta.json();
    if (sequenciaAtual !== buscaEstudanteSequencia) return;
    estadoDocente.estudantes = estudantes;
    if (!estadoDocente.estudantes.some((item) => Number(item.estudante_id) === Number(estadoDocente.estudanteId))) {
        estadoDocente.estudanteId = null;
    }
    renderizarEstudantesDocente();
}

async function carregarRegistrosDocente() {
    const combo = comboDocenteAtual();
    if (!combo || !estadoDocente.periodoId) {
        estadoDocente.registros = [];
        renderizarRegistrosDocente();
        return;
    }

    const params = new URLSearchParams({
        periodo_id: String(estadoDocente.periodoId),
        turma_id: String(combo.turma_id),
        disciplina_id: String(combo.disciplina_id)
    });

    const resposta = await fetchComAuth(`/preconselho/registros?${params.toString()}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os registros salvos."));
    }

    const dados = await resposta.json();
    estadoDocente.registros = Array.isArray(dados?.itens) ? dados.itens : [];
    renderizarRegistrosDocente();
}

async function carregarPainelDocente(estudanteIdParaReabrir = null) {
    limparMensagem("msgPreconselhoDocente");
    try {
        atualizarModoDocente();
        await carregarCombosDocente();
        await Promise.all([carregarEstudantesDocente(), carregarRegistrosDocente()]);

        if (estudanteIdParaReabrir) {
            const estudante = resolverEstudanteParaFormulario(estudanteIdParaReabrir);
            if (estudante) {
                preencherFormularioComEstudante(estudante);
            } else {
                limparFormularioDocente();
            }
        } else {
            limparFormularioDocente();
        }

        definirMensagem("msgPreconselhoDocente", "Painel docente atualizado.");
        return true;
    } catch (erro) {
        estadoDocente.combos = [];
        estadoDocente.estudantes = [];
        estadoDocente.registros = [];
        renderizarResumoDocente();
        renderizarCombosDocente();
        renderizarEstudantesDocente();
        renderizarRegistrosDocente();
        limparFormularioDocente();
        definirMensagem("msgPreconselhoDocente", erro.message || "Não foi possível carregar o painel docente.", true);
        return false;
    }
}

