let laudoEstudanteEmEdicao = null;
let apoiosEstudanteCatalogo = [];

function limparFormularioEstudante() {
    estudanteEmEdicao = null;
    el("formEstudante").reset();
    el("tituloFormEstudante").innerText = "Cadastrar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "none";
    el("secaoLaudosEstudante").hidden = true;
    limparFormularioLaudoEstudante();
}

function iniciarEdicaoEstudante(estudante) {
    estudanteEmEdicao = estudante;
    el("estudanteNome").value = estudante.nome || "";
    el("estudanteTurmaId").value = String(estudante.turma_id || "");
    el("estudanteSexo").value = String(estudante.sexo || "");
    el("tituloFormEstudante").innerText = "Editar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "inline-block";
    el("secaoLaudosEstudante").hidden = false;
    limparFormularioLaudoEstudante();
    carregarLaudosEstudante();
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
    if (item) {
        adicionarEstudanteVinculado({
            estudante_id: Number(item.id || 0) || null,
            nome: String(item.nome || item.label || texto).trim(),
            turma_id: Number(item.turma_id || 0) || null,
            turma_nome: String(item.turma_nome || "").trim()
        });
    } else {
        setMensagemOcorrencias("Selecione um estudante cadastrado na lista para carregar a turma automaticamente.", true);
        atualizarSugestoesEstudantesBusca(true).catch((err) => setMensagemOcorrencias(err.message, true));
        input.focus();
        return;
    }
    input.value = "";
    hidden.value = "";
    ocultarSugestoes("listaEstudantesBusca");
    atualizarPreviewOcorrencia();
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
    if (obterTipoRegistroFormulario() === "professor") {
        adicionarProfessorVinculado({
            professor_id: item ? Number(item.id || 0) || null : null,
            nome: String(item?.nome || item?.label || texto).trim(),
            email: String(item?.email || "").trim()
        });
        input.value = "";
        hidden.value = "";
        ocultarSugestoes("listaProfessoresBusca");
        atualizarPreviewOcorrencia();
        return;
    }

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
    adicionarEstudanteVinculado({
        estudante_id: Number(item.id || 0) || null,
        nome: String(item.nome || item.label || "").trim(),
        turma_id: Number(item.turma_id || 0) || null,
        turma_nome: String(item.turma_nome || "").trim()
    });
    el("ocorrenciaBuscaEstudante").value = "";
    el("ocorrenciaEstudanteId").value = "";
    atualizarPreviewOcorrencia();
}

function selecionarSugestaoProfessor(item) {
    if (!item) return;
    if (obterTipoRegistroFormulario() === "professor") {
        adicionarProfessorVinculado({
            professor_id: Number(item.id || 0) || null,
            nome: String(item.nome || item.label || "").trim(),
            email: String(item.email || "").trim()
        });
        el("ocorrenciaBuscaProfessor").value = "";
        el("ocorrenciaProfessorRequerenteId").value = "";
        atualizarPreviewOcorrencia();
        return;
    }
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
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    params.set("limite", "20");
    const idsSelecionados = new Set(
        obterEstudantesVinculadosFormulario()
            .map((item) => Number(item.estudante_id || 0))
            .filter((item) => item > 0)
    );
    const itens = (await fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers }))
        .filter((item) => !idsSelecionados.has(Number(item.id || 0)));
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

    const professoresSelecionados = new Set(
        obterProfessoresVinculadosFormulario()
            .map((item) => Number(item.professor_id || 0))
            .filter((item) => item > 0)
    );
    const itens = filtrarSugestoesLocais(opcoesOcorrencias.professores, termo, {
        limite: 12,
        campos: ["nome", "email", "label"]
    }).filter((item) => (
        obterTipoRegistroFormulario() !== "professor"
        || !professoresSelecionados.has(Number(item.id || 0))
    ));
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

function sincronizarVinculadosPendentesAntesSalvar() {
    const tipoRegistro = obterTipoRegistroFormulario();
    const textoEstudante = String(el("ocorrenciaBuscaEstudante")?.value || "").trim();
    if (tipoRegistro === "estudante" && textoEstudante) {
        aplicarSelecaoEstudantePorTexto();
    }

    const textoProfessor = String(el("ocorrenciaBuscaProfessor")?.value || "").trim();
    if ((tipoRegistro === "professor" || tipoRegistro === "estudante") && textoProfessor) {
        aplicarSelecaoProfessorPorTexto();
    }
    return true;
}

function montarPayloadOcorrencia() {
    sincronizarDescricaoEditor();
    const tipoRegistro = obterTipoRegistroFormulario();
    const estudantesVinculados = obterEstudantesVinculadosFormulario();
    const professoresVinculados = obterProfessoresVinculadosFormulario();
    const textoProfessor = el("ocorrenciaBuscaProfessor").value.trim();
    const itemProfessor = obterItemSugestaoPorTexto(mapaBuscaProfessores, textoProfessor, opcoesOcorrencias.professores || []);
    const assuntoOuPauta = String(el("ocorrenciaDisciplina")?.value || "").trim();

    const professorIdSelecionado = Number(el("ocorrenciaProfessorRequerenteId").value || 0);
    const professorSelecionado = professorIdSelecionado > 0
        ? obterProfessorOpcaoPorId(professorIdSelecionado)
        : itemProfessor;
    const primeiroEstudante = estudantesVinculados[0] || null;
    const primeiroProfessor = professoresVinculados[0] || null;

    return {
        pre_registration_id: preRegistroEmComplementacaoId || null,
        tipo_registro: tipoRegistro,
        quem_assina: tipoRegistro === "estudante" ? obterQuemAssinaFormulario() : null,
        nome_estudante: tipoRegistro === "geral"
            ? (assuntoOuPauta || null)
            : (tipoRegistro === "estudante" ? (resumoNomesVinculados(estudantesVinculados) || null) : null),
        estudante_id: tipoRegistro === "estudante" && Number(primeiroEstudante?.estudante_id || 0) > 0
            ? Number(primeiroEstudante.estudante_id)
            : null,
        estudantes_vinculados: tipoRegistro === "estudante" ? estudantesVinculados : [],
        turma_id: tipoRegistro === "estudante"
            ? (obterContextoTurmaEstudantesFormulario().turma_id || null)
            : null,
        professor_requerente: tipoRegistro === "geral"
            ? null
            : (
                tipoRegistro === "professor"
                    ? (resumoNomesVinculados(professoresVinculados) || null)
                    : (professorSelecionado ? professorSelecionado.nome : (textoProfessor || null))
            ),
        professor_requerente_id: tipoRegistro === "geral"
            ? null
            : (
                tipoRegistro === "professor"
                    ? (Number(primeiroProfessor?.professor_id || 0) > 0 ? Number(primeiroProfessor.professor_id) : null)
                    : (professorSelecionado ? Number(professorSelecionado.id) : null)
            ),
        professores_vinculados: tipoRegistro === "professor" ? professoresVinculados : [],
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
    sincronizarVinculadosPendentesAntesSalvar();
    if (!sincronizarRegimentoPendenteAntesSalvar()) {
        return;
    }
    const idsRegimentoSelecionados = validarBaseLegalSelecionadaAntesSalvar();
    if (registroExigeBaseLegal() && idsRegimentoSelecionados.length === 0) {
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
        if (typeof carregarPreRegistros === "function") {
            await carregarPreRegistros({ manager: true });
        }
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
        turma_id: Number(el("estudanteTurmaId").value),
        sexo: el("estudanteSexo").value || null
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

function limparFormularioLaudoEstudante() {
    laudoEstudanteEmEdicao = null;
    el("formLaudoEstudante")?.reset();
    if (el("estudanteLaudoId")) el("estudanteLaudoId").value = "";
    if (el("btnSalvarLaudoEstudante")) el("btnSalvarLaudoEstudante").textContent = "Adicionar laudo";
    if (el("btnCancelarEdicaoLaudoEstudante")) el("btnCancelarEdicaoLaudoEstudante").hidden = true;
}

function iniciarEdicaoLaudoEstudante(laudo) {
    laudoEstudanteEmEdicao = laudo;
    el("estudanteLaudoId").value = String(laudo.id);
    el("estudanteLaudoCondicao").value = String(laudo.condicao_necessidade || "");
    el("estudanteLaudoClassificacao").value = String(laudo.classificacao || "");
    el("estudanteLaudoSistema").value = String(laudo.sistema_classificacao || "");
    el("estudanteLaudoCodigo").value = String(laudo.codigo_laudo || "");
    el("estudanteLaudoDescricao").value = String(laudo.descricao_laudo || "");
    el("estudanteLaudoPossui").checked = Boolean(laudo.possui_laudo);
    el("estudanteLaudoData").value = String(laudo.data_laudo || "");
    el("estudanteLaudoObservacoesRestritas").value = String(laudo.observacoes_restritas || "");
    document.querySelectorAll('[data-apoio-estudante-id]').forEach((input) => {
        input.checked = (laudo.apoio_ids || []).includes(Number(input.value));
    });
    el("btnSalvarLaudoEstudante").textContent = "Salvar alterações";
    el("btnCancelarEdicaoLaudoEstudante").hidden = false;
    el("estudanteLaudoCondicao").focus();
}

function renderizarLaudosEstudante(laudos) {
    const lista = el("listaLaudosEstudante");
    lista.innerHTML = "";
    if (!Array.isArray(laudos) || laudos.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-field-hint";
        vazio.textContent = "Nenhum diagnóstico ou laudo cadastrado para este estudante.";
        lista.appendChild(vazio);
        return;
    }

    laudos.forEach((laudo) => {
        const item = document.createElement("article");
        item.className = "estudante-laudo-item";
        const conteudo = document.createElement("div");
        const titulo = document.createElement("h4");
        titulo.textContent = laudo.condicao_necessidade || "Condição não informada";
        conteudo.appendChild(titulo);
        if (laudo.descricao_laudo) {
            const observacoes = document.createElement("p");
            observacoes.textContent = laudo.descricao_laudo;
            conteudo.appendChild(observacoes);
        }
        const meta = document.createElement("div");
        meta.className = "estudante-laudo-meta";
        const cid = document.createElement("span");
        cid.className = "status-chip";
        cid.textContent = laudo.codigo_laudo
            ? `${laudo.sistema_classificacao || "Código"} ${laudo.codigo_laudo}`
            : (laudo.classificacao || "Sem classificação");
        const status = document.createElement("span");
        status.className = `status-chip ${classeStatusEstudante(Boolean(laudo.ativo))}`;
        status.textContent = laudo.ativo ? "Ativo" : "Inativo";
        meta.append(cid, status);
        conteudo.appendChild(meta);

        const acoes = document.createElement("div");
        acoes.className = "coordenacao-inline";
        const editar = document.createElement("button");
        editar.type = "button";
        editar.textContent = "Editar";
        editar.addEventListener("click", () => iniciarEdicaoLaudoEstudante(laudo));
        const excluir = document.createElement("button");
        excluir.type = "button";
        excluir.className = "coordenacao-btn-danger";
        excluir.textContent = "Excluir";
        excluir.addEventListener("click", () => excluirLaudoEstudante(laudo));
        acoes.append(editar, excluir);
        item.append(conteudo, acoes);
        lista.appendChild(item);
    });
}

async function carregarLaudosEstudante() {
    if (!estudanteEmEdicao) return;
    try {
        const laudos = await fetchJson(`/estudantes/${estudanteEmEdicao.id}/laudos`, { headers });
        renderizarLaudosEstudante(laudos);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

function renderizarCatalogoApoios() {
    const grupos = {
        necessidade_pedagogica: el("opcoesNecessidadesPedagogicas"),
        recurso_acessibilidade: el("opcoesRecursosAcessibilidade")
    };
    Object.values(grupos).forEach((grupo) => { grupo.innerHTML = ""; });
    apoiosEstudanteCatalogo.forEach((apoio) => {
        const label = document.createElement("label");
        label.className = "estudante-apoio-check";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = String(apoio.id);
        input.dataset.apoioEstudanteId = String(apoio.id);
        label.append(input, document.createTextNode(apoio.nome));
        grupos[apoio.tipo]?.appendChild(label);
    });
}

async function carregarCatalogoApoios() {
    apoiosEstudanteCatalogo = await fetchJson("/estudante-apoios/catalogo", { headers });
    renderizarCatalogoApoios();
}

async function adicionarOpcaoApoio(tipo, inputId) {
    const input = el(inputId);
    const nome = input.value.trim();
    if (!nome) return;
    try {
        await fetchJson("/estudante-apoios/catalogo", {
            method: "POST", headers: headersJson, body: JSON.stringify({ tipo, nome })
        });
        input.value = "";
        await carregarCatalogoApoios();
        setMensagemEstudantes("Opção adicionada com sucesso.");
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function salvarLaudoEstudante(event) {
    event.preventDefault();
    if (!estudanteEmEdicao) return;
    const payload = {
        condicao_necessidade: el("estudanteLaudoCondicao").value.trim(),
        classificacao: el("estudanteLaudoClassificacao").value.trim() || null,
        sistema_classificacao: el("estudanteLaudoSistema").value || null,
        codigo_laudo: el("estudanteLaudoCodigo").value.trim() || null,
        descricao_laudo: el("estudanteLaudoDescricao").value.trim() || null,
        possui_laudo: el("estudanteLaudoPossui").checked,
        data_laudo: el("estudanteLaudoData").value || null,
        observacoes_restritas: el("estudanteLaudoObservacoesRestritas").value.trim() || null,
        apoio_ids: Array.from(document.querySelectorAll('[data-apoio-estudante-id]:checked'))
            .map((input) => Number(input.value))
    };
    const editando = Boolean(laudoEstudanteEmEdicao);
    if (editando) payload.ativo = Boolean(laudoEstudanteEmEdicao.ativo);
    const url = editando
        ? `/estudantes/${estudanteEmEdicao.id}/laudos/${laudoEstudanteEmEdicao.id}`
        : `/estudantes/${estudanteEmEdicao.id}/laudos`;
    try {
        await fetchJson(url, {
            method: editando ? "PUT" : "POST",
            headers: headersJson,
            body: JSON.stringify(payload)
        });
        limparFormularioLaudoEstudante();
        await Promise.all([carregarLaudosEstudante(), carregarEstudantes()]);
        setMensagemEstudantes(editando ? "Laudo atualizado com sucesso." : "Laudo adicionado com sucesso.");
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function excluirLaudoEstudante(laudo) {
    if (!estudanteEmEdicao) return;
    if (!window.confirm(`Excluir o registro “${laudo.condicao_necessidade}”?`)) return;
    try {
        await fetchJson(`/estudantes/${estudanteEmEdicao.id}/laudos/${laudo.id}`, {
            method: "DELETE",
            headers
        });
        limparFormularioLaudoEstudante();
        await Promise.all([carregarLaudosEstudante(), carregarEstudantes()]);
        setMensagemEstudantes("Laudo excluído com sucesso.");
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
