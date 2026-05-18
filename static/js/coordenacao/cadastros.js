function limparFormularioEstudante() {
    estudanteEmEdicao = null;
    el("formEstudante").reset();
    el("tituloFormEstudante").innerText = "Cadastrar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "none";
}

function iniciarEdicaoEstudante(estudante) {
    estudanteEmEdicao = estudante;
    el("estudanteNome").value = estudante.nome || "";
    el("estudanteTurmaId").value = String(estudante.turma_id || "");
    el("tituloFormEstudante").innerText = "Editar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "inline-block";
    ativarAbaCoordenacao("estudantes");
}

function aplicarSelecaoEstudantePorTexto() {
    const input = el("ocorrenciaBuscaEstudante");
    const hidden = el("ocorrenciaEstudanteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaEstudantes, texto);
    if (!item) {
        hidden.value = "";
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    input.value = String(item.nome || item.label || texto).trim();
    hidden.value = String(item.id);
    el("ocorrenciaTurmaId").value = String(item.turma_id);
    atualizarSelectAulasPorTurma(item.turma_id);
    ocultarSugestoes("listaEstudantesBusca");
}

function aplicarSelecaoProfessorPorTexto() {
    const input = el("ocorrenciaBuscaProfessor");
    const hidden = el("ocorrenciaProfessorRequerenteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaProfessoresBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaProfessores, texto, opcoesOcorrencias.professores || []);
    if (item) {
        input.value = String(item.nome || item.label || texto).trim();
    }
    hidden.value = item ? String(item.id) : "";
    ocultarSugestoes("listaProfessoresBusca");
}

function aplicarSelecaoDisciplinaPorTexto() {
    const input = el("ocorrenciaDisciplina");
    const texto = input.value.trim();
    if (!texto) {
        ocultarSugestoes("listaDisciplinasBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaDisciplinas, texto, opcoesOcorrencias.disciplinas || []);
    if (item) {
        input.value = String(item.nome || item.label || texto).trim();
    }
    ocultarSugestoes("listaDisciplinasBusca");
}

function selecionarSugestaoEstudante(item) {
    if (!item) return;
    el("ocorrenciaBuscaEstudante").value = String(item.nome || item.label || "").trim();
    el("ocorrenciaEstudanteId").value = String(item.id || "");
    if (item.turma_id) {
        el("ocorrenciaTurmaId").value = String(item.turma_id);
        atualizarSelectAulasPorTurma(item.turma_id);
    }
    atualizarPreviewOcorrencia();
}

function selecionarSugestaoProfessor(item) {
    if (!item) return;
    el("ocorrenciaBuscaProfessor").value = String(item.nome || item.label || "").trim();
    el("ocorrenciaProfessorRequerenteId").value = String(item.id || "");
    atualizarPreviewOcorrencia();
}

function selecionarSugestaoDisciplina(item) {
    if (!item) return;
    el("ocorrenciaDisciplina").value = String(item.nome || item.label || "").trim();
    atualizarPreviewOcorrencia();
}

function filtrarSugestoesLocais(itens, termo, { limite = 12, campos = ["nome", "label"] } = {}) {
    const lista = Array.isArray(itens) ? itens : [];
    const termoLimpo = String(termo || "").trim().toLowerCase();
    if (!termoLimpo) {
        return lista.slice(0, limite);
    }

    return lista.filter((item) => campos.some((campo) => {
        const valor = String(item?.[campo] || "").trim().toLowerCase();
        return valor.includes(termoLimpo);
    })).slice(0, limite);
}

async function atualizarSugestoesEstudantesBusca(forcar = false) {
    if (obterTipoRegistroFormulario() !== "estudante") {
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }
    const input = el("ocorrenciaBuscaEstudante");
    const termo = input.value.trim();
    const turmaId = el("ocorrenciaTurmaId").value;
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("limite", "20");
    const itens = await fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers });
    preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, itens, {
        onSelect: selecionarSugestaoEstudante,
        textoVazio: "Nenhum estudante encontrado."
    });
}

function agendarBuscaEstudantes() {
    if (timerBuscaEstudantes) clearTimeout(timerBuscaEstudantes);
    timerBuscaEstudantes = setTimeout(() => {
        atualizarSugestoesEstudantesBusca().catch((err) => setMensagemOcorrencias(err.message, true));
    }, 250);
}

function atualizarSugestoesProfessoresBusca(forcar = false) {
    if (obterTipoRegistroFormulario() === "geral") {
        ocultarSugestoes("listaProfessoresBusca");
        return;
    }
    const termo = el("ocorrenciaBuscaProfessor").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaProfessoresBusca");
        return;
    }

    const itens = filtrarSugestoesLocais(opcoesOcorrencias.professores, termo, {
        limite: 12,
        campos: ["nome", "email", "label"]
    });
    preencherDatalist("listaProfessoresBusca", mapaBuscaProfessores, itens, {
        onSelect: selecionarSugestaoProfessor,
        textoVazio: "Nenhum professor encontrado."
    });
}

function atualizarSugestoesDisciplinasBusca(forcar = false) {
    const termo = el("ocorrenciaDisciplina").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaDisciplinasBusca");
        return;
    }

    const itens = filtrarSugestoesLocais(opcoesOcorrencias.disciplinas, termo, {
        limite: 12,
        campos: ["nome", "label"]
    });
    preencherDatalist("listaDisciplinasBusca", mapaBuscaDisciplinas, itens, {
        onSelect: selecionarSugestaoDisciplina,
        textoVazio: "Nenhuma disciplina encontrada."
    });
}

function montarPayloadOcorrencia() {
    sincronizarDescricaoEditor();
    const tipoRegistro = obterTipoRegistroFormulario();
    const textoEstudante = el("ocorrenciaBuscaEstudante").value.trim();
    const itemEstudante = obterItemSugestaoPorTexto(mapaBuscaEstudantes, textoEstudante);
    const textoProfessor = el("ocorrenciaBuscaProfessor").value.trim();
    const itemProfessor = obterItemSugestaoPorTexto(mapaBuscaProfessores, textoProfessor, opcoesOcorrencias.professores || []);
    const tituloGeral = String(el("ocorrenciaTituloGeral")?.value || "").trim();

    const estudanteIdHidden = Number(el("ocorrenciaEstudanteId").value || 0);
    const professorIdSelecionado = Number(el("ocorrenciaProfessorRequerenteId").value || 0);
    const professorSelecionado = professorIdSelecionado > 0
        ? obterProfessorOpcaoPorId(professorIdSelecionado)
        : itemProfessor;

    const estudanteId = estudanteIdHidden || (itemEstudante ? Number(itemEstudante.id) : 0);
    const nomeEstudante = itemEstudante ? itemEstudante.nome : textoEstudante;

    return {
        tipo_registro: tipoRegistro,
        nome_estudante: tipoRegistro === "geral"
            ? (tituloGeral || null)
            : (tipoRegistro === "estudante" ? (nomeEstudante || null) : null),
        estudante_id: tipoRegistro === "estudante" && estudanteId > 0 ? estudanteId : null,
        turma_id: tipoRegistro === "estudante" ? Number(el("ocorrenciaTurmaId").value) : null,
        professor_requerente: tipoRegistro === "geral"
            ? null
            : (professorSelecionado ? professorSelecionado.nome : (textoProfessor || null)),
        professor_requerente_id: tipoRegistro === "geral"
            ? null
            : (professorSelecionado ? Number(professorSelecionado.id) : null),
        disciplina: el("ocorrenciaDisciplina").value.trim() || null,
        data_ocorrencia: el("ocorrenciaData").value,
        aula: tipoRegistro === "estudante" ? String(el("ocorrenciaAula").value || "").trim() : null,
        horario_ocorrencia: el("ocorrenciaHorario").value.trim(),
        descricao: el("ocorrenciaDescricao").value.trim(),
        regimento_item_ids: obterIdsRegimentoSelecionadosFormulario(),
        acao_aplicada: el("ocorrenciaAcaoAplicada").value,
        status: el("ocorrenciaStatus").value || opcoesOcorrencias.status_padrao || "registrado"
    };
}

async function salvarOcorrencia(event) {
    event.preventDefault();
    if (!sincronizarRegimentoPendenteAntesSalvar()) {
        return;
    }
    const idsRegimentoSelecionados = validarBaseLegalSelecionadaAntesSalvar();
    if (idsRegimentoSelecionados.length === 0) {
        return;
    }

    const payload = montarPayloadOcorrencia();
    payload.regimento_item_ids = idsRegimentoSelecionados;
    if (!payload.descricao) {
        setMensagemOcorrencias("Descricao e obrigatoria.", true);
        obterEditorDescricao()?.focus();
        return;
    }

    try {
        let ocorrencia;
        if (ocorrenciaEmEdicaoId) {
            ocorrencia = await fetchJson(`/ocorrencias/${ocorrenciaEmEdicaoId}`, {
                method: "PATCH",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Registro atualizado com sucesso.");
        } else {
            ocorrencia = await fetchJson("/ocorrencias", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Registro salvo com sucesso.");
        }

        limparFormularioOcorrencia();
        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        const ocorrenciaAtualizada = ocorrenciasCache.find(
            (item) => Number(item.id) === Number(ocorrencia?.id)
        ) || ocorrencia;
        selecionarOcorrencia(ocorrenciaAtualizada);
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function limparFiltrosOcorrencias() {
    el("formFiltrosOcorrencias").reset();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarRelatorioOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function limparFiltrosRelatorioOcorrencias() {
    el("formRelatorioOcorrencias").reset();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function excluirOcorrencia(ocorrencia) {
    const referencia = obterReferenciaRegistro(ocorrencia);
    const confirmou = window.confirm(`Excluir o registro "${referencia}"? Esta acao nao pode ser desfeita.`);
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/ocorrencias/${ocorrencia.id}`,
            `/ocorrencias/${ocorrencia.id}/excluir`
        );

        if (Number(ocorrenciaEmEdicaoId) === Number(ocorrencia.id)) {
            limparFormularioOcorrencia();
        }
        if (Number(ocorrenciaSelecionadaId) === Number(ocorrencia.id)) {
            selecionarOcorrencia(null);
        }

        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        setMensagemOcorrencias(resposta?.mensagem || "Registro excluido com sucesso.");
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function excluirEstudante(estudante) {
    const nomeEstudante = String(estudante?.nome || "este estudante").trim();
    const confirmou = window.confirm(
        `Excluir o cadastro de ${nomeEstudante}? As ocorrencias ja registradas serao preservadas no historico.`
    );
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/estudantes/${estudante.id}`,
            `/estudantes/${estudante.id}/excluir`
        );

        if (Number(estudanteEmEdicao?.id) === Number(estudante.id)) {
            limparFormularioEstudante();
        }
        if (Number(el("ocorrenciaEstudanteId")?.value || 0) === Number(estudante.id)) {
            el("ocorrenciaEstudanteId").value = "";
        }

        invalidarRelatorioOcorrencias();
        await Promise.all([
            carregarEstudantes(),
            carregarOcorrencias(),
            atualizarSugestoesEstudantesBusca(true)
        ]);

        const totalDesvinculado = Number(resposta?.ocorrencias_desvinculadas || 0);
        const sufixo = totalDesvinculado > 0
            ? ` ${totalDesvinculado} ocorrencia(s) ficaram apenas com o nome do estudante no historico.`
            : "";
        setMensagemEstudantes((resposta?.mensagem || "Estudante excluido com sucesso.") + sufixo);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function salvarEstudante(event) {
    event.preventDefault();
    const payload = {
        nome: el("estudanteNome").value.trim(),
        turma_id: Number(el("estudanteTurmaId").value)
    };

    try {
        if (estudanteEmEdicao) {
            await fetchJson(`/estudantes/${estudanteEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    ativo: Boolean(estudanteEmEdicao.ativo)
                })
            });
            setMensagemEstudantes("Estudante atualizado com sucesso.");
        } else {
            await fetchJson("/estudantes", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemEstudantes("Estudante cadastrado com sucesso.");
        }

        limparFormularioEstudante();
        await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function importarEstudantesArquivo(event) {
    event.preventDefault();
    const arquivo = el("arquivoCsvEstudantes")?.files?.[0];
    if (!arquivo) {
        setMensagemEstudantes("Selecione um arquivo JSON ou CSV para importar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/estudantes/importar", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagemEstudantes(comporMensagemImportacaoCsv(resposta), houveFalhaImportacao(resposta));
        el("formImportarEstudantesCsv").reset();
        await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function importarRegimentoCsv(event) {
    event.preventDefault();
    const arquivo = el("arquivoCsvRegimento")?.files?.[0];
    if (!arquivo) {
        setMensagemRegimento("Selecione um arquivo JSON ou CSV para importar.", true);
        return;
    }

    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/regimento-itens/importar", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagemRegimento(comporMensagemImportacaoCsv(resposta), houveFalhaImportacao(resposta));
        el("formImportarRegimentoCsv").reset();
        await Promise.all([carregarCatalogosBaseLegal(), carregarRegimentoItens(idsSelecionados)]);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

function baixarModeloEstudantesCsv() {
    baixarArquivoTexto("modelo_estudantes.json", MODELO_JSON_ESTUDANTES, "application/json;charset=utf-8");
}

function baixarModeloRegimentoCsv() {
    baixarArquivoTexto("modelo_base_legal.json", MODELO_JSON_BASE_LEGAL, "application/json;charset=utf-8");
}

async function filtrarEstudantes(event) {
    event.preventDefault();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function limparFiltrosEstudantes() {
    el("formFiltrosEstudantes").reset();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}
