function valorCampo(id) {
    return String(el(id)?.value || "").trim();
}

function montarQueryOcorrencias({
    nomeEstudanteId,
    tipoRegistroId,
    turmaIdId,
    statusId,
    dataInicialId,
    dataFinalId
}) {
    const params = new URLSearchParams();
    const nomeEstudante = valorCampo(nomeEstudanteId);
    const tipoRegistro = valorCampo(tipoRegistroId);
    const turmaId = valorCampo(turmaIdId);
    const status = valorCampo(statusId);
    const dataInicial = valorCampo(dataInicialId);
    const dataFinal = valorCampo(dataFinalId);

    if (nomeEstudante) params.set("nome_estudante", nomeEstudante);
    if (tipoRegistro) params.set("tipo_registro", tipoRegistro);
    if (turmaId) params.set("turma_id", turmaId);
    if (status) params.set("status", status);
    if (dataInicial) params.set("data_inicial", dataInicial);
    if (dataFinal) params.set("data_final", dataFinal);

    return params.toString() ? `?${params.toString()}` : "";
}

function descreverFiltrosOcorrencias(configuracao) {
    const partes = [];
    const nomeEstudante = valorCampo(configuracao.nomeEstudanteId);
    const tipoRegistro = valorCampo(configuracao.tipoRegistroId);
    const turmaId = valorCampo(configuracao.turmaIdId);
    const status = valorCampo(configuracao.statusId);
    const dataInicial = valorCampo(configuracao.dataInicialId);
    const dataFinal = valorCampo(configuracao.dataFinalId);

    if (nomeEstudante) {
        partes.push(`Referência: ${nomeEstudante}`);
    }
    if (tipoRegistro) {
        partes.push(`Tipo: ${rotuloTipoRegistro(tipoRegistro)}`);
    }
    if (turmaId) {
        const turma = obterTurmaOpcaoPorId(turmaId);
        partes.push(`Turma: ${turma?.nome || `ID ${turmaId}`}`);
    }
    if (status) {
        partes.push(`Status: ${rotuloStatus(status)}`);
    }
    if (dataInicial && dataFinal) {
        partes.push(`Período: ${formatarDataBr(dataInicial)} até ${formatarDataBr(dataFinal)}`);
    } else if (dataInicial) {
        partes.push(`A partir de: ${formatarDataBr(dataInicial)}`);
    } else if (dataFinal) {
        partes.push(`Até: ${formatarDataBr(dataFinal)}`);
    }

    return partes.length > 0 ? partes.join(" | ") : "Sem filtro aplicado.";
}

function totalOcorrenciasPorStatus(lista, status) {
    return (lista || []).filter((ocorrencia) => String(ocorrencia.status || "").trim() === status).length;
}

function atualizarResumoOcorrencias() {
    const total = ocorrenciasCache.length;
    const acompanhamento = totalOcorrenciasPorStatus(ocorrenciasCache, "em_acompanhamento");
    const aguardando = totalOcorrenciasPorStatus(ocorrenciasCache, "aguardando_responsavel");
    const resolvido = totalOcorrenciasPorStatus(ocorrenciasCache, "resolvido");

    if (el("resumoOcorrenciasTotal")) {
        el("resumoOcorrenciasTotal").innerText = String(total);
    }
    if (el("resumoOcorrenciasAcompanhamento")) {
        el("resumoOcorrenciasAcompanhamento").innerText = String(acompanhamento);
    }
    if (el("resumoOcorrenciasAguardando")) {
        el("resumoOcorrenciasAguardando").innerText = String(aguardando);
    }
    if (el("resumoOcorrenciasResolvido")) {
        el("resumoOcorrenciasResolvido").innerText = String(resolvido);
    }
    if (el("resumoOcorrenciasPeriodo")) {
        el("resumoOcorrenciasPeriodo").innerText = descreverFiltrosOcorrencias({
            nomeEstudanteId: "filtroNomeEstudante",
            tipoRegistroId: "filtroTipoRegistro",
            turmaIdId: "filtroTurmaId",
            statusId: "filtroStatus",
            dataInicialId: "filtroDataInicial",
            dataFinalId: "filtroDataFinal"
        });
    }
}

function agruparOcorrencias(lista, obterChave, obterRotulo) {
    const mapa = new Map();

    (lista || []).forEach((ocorrencia) => {
        const chaveBruta = obterChave(ocorrencia);
        const rotuloBruto = obterRotulo(ocorrencia);
        const chave = String(chaveBruta || rotuloBruto || "nao_informado").trim();
        const rotulo = String(rotuloBruto || chaveBruta || "Não informado").trim() || "Não informado";
        const atual = mapa.get(chave) || { label: rotulo, total: 0 };
        atual.total += 1;
        mapa.set(chave, atual);
    });

    return Array.from(mapa.values()).sort((a, b) => {
        if (b.total !== a.total) {
            return b.total - a.total;
        }
        return a.label.localeCompare(b.label, "pt-BR");
    });
}

function renderRankingLista(idLista, itens, vazio, totalBase = 0) {
    const lista = el(idLista);
    if (!lista) return;
    lista.innerHTML = "";

    if (!Array.isArray(itens) || itens.length === 0) {
        const itemVazio = document.createElement("li");
        itemVazio.className = "coordenacao-empty-state";
        itemVazio.innerText = vazio;
        lista.appendChild(itemVazio);
        return;
    }

    itens.slice(0, 5).forEach((item) => {
        const li = document.createElement("li");
        li.className = "coordenacao-ranking-item";

        const label = document.createElement("span");
        label.className = "coordenacao-ranking-label";
        label.innerText = item.label;

        const total = document.createElement("strong");
        total.innerText = String(item.total);

        const meta = document.createElement("span");
        meta.className = "coordenacao-ranking-meta";
        if (totalBase > 0) {
            const percentual = Math.round((item.total / totalBase) * 100);
            meta.innerText = `${percentual}% do relatório`;
        } else {
            meta.innerText = `${item.total} registro(s)`;
        }

        li.appendChild(label);
        li.appendChild(total);
        li.appendChild(meta);
        lista.appendChild(li);
    });
}

function atualizarResumoRelatorioOcorrencias() {
    const total = relatorioOcorrenciasCache.length;
    const resolvidas = totalOcorrenciasPorStatus(relatorioOcorrenciasCache, "resolvido");
    const abertas = total - resolvidas;
    const turmasImpactadas = new Set(
        relatorioOcorrenciasCache
            .map((ocorrencia) => String(ocorrencia.turma_nome || ocorrencia.turma_id || "").trim())
            .filter(Boolean)
    ).size;

    if (el("relatorioMetricasTotal")) {
        el("relatorioMetricasTotal").innerText = String(total);
    }
    if (el("relatorioMetricasAbertas")) {
        el("relatorioMetricasAbertas").innerText = String(abertas);
    }
    if (el("relatorioMetricasResolvidas")) {
        el("relatorioMetricasResolvidas").innerText = String(resolvidas);
    }
    if (el("relatorioMetricasTurmas")) {
        el("relatorioMetricasTurmas").innerText = String(turmasImpactadas);
    }

    const descricaoFiltros = descreverFiltrosOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        tipoRegistroId: "relatorioTipoRegistro",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
    if (el("relatorioPeriodo")) {
        el("relatorioPeriodo").innerText = total > 0
            ? `Recorte atual: ${descricaoFiltros}`
            : `Nenhuma ocorrência encontrada. ${descricaoFiltros}`;
    }

    renderRankingLista(
        "relatorioResumoStatus",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.status,
            (ocorrencia) => rotuloStatus(ocorrencia.status)
        ),
        "Nenhum status encontrado para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoTurmas",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.turma_id,
            (ocorrencia) => ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`
        ),
        "Nenhuma turma encontrada para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoProfessores",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.professor_requerente_id || ocorrencia.professor_requerente,
            (ocorrencia) => ocorrencia.professor_requerente || "Não informado"
        ),
        "Nenhum professor encontrado para o recorte selecionado.",
        total
    );
}

function renderTabelaRelatorioOcorrencias() {
    const tbody = el("tbodyRelatorioOcorrencias");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(relatorioOcorrenciasCache) || relatorioOcorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 6;
        td.className = "booking-empty";
        td.innerText = "Nenhum registro encontrado para o relatório.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    relatorioOcorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Tipo", rotuloTipoRegistro(ocorrencia.tipo_registro)));
        tr.appendChild(criarCelulaTabela("Referência", obterReferenciaRegistro(ocorrencia)));
        tr.appendChild(criarCelulaTabela("Contexto", obterContextoRegistro(ocorrencia)));
        tr.appendChild(criarCelulaTabela("Ação aplicada", rotuloAcao(ocorrencia.acao_aplicada)));
        tr.appendChild(criarCelulaTabela("Status", rotuloStatus(ocorrencia.status)));
        tbody.appendChild(tr);
    });
}

function renderRelatorioOcorrencias() {
    atualizarResumoRelatorioOcorrencias();
    renderTabelaRelatorioOcorrencias();
}

function invalidarRelatorioOcorrencias() {
    if (!relatorioOcorrenciasCarregado) return;
    relatorioOcorrenciasCarregado = false;
    setMensagemRelatorios("Dados atualizados. Gere o relatório novamente para refletir as alterações.");
}

async function carregarOpcoesOcorrencias() {
    const idsRegimentoSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const acaoAplicadaAtual = String(el("ocorrenciaAcaoAplicada")?.value || "").trim();
    const opcoesApi = await fetchJson("/ocorrencias/opcoes", { headers });
    opcoesOcorrencias = {
        tipos_registro: Array.isArray(opcoesApi.tipos_registro) ? opcoesApi.tipos_registro : [],
        turmas: Array.isArray(opcoesApi.turmas) ? opcoesApi.turmas : [],
        professores: Array.isArray(opcoesApi.professores) ? opcoesApi.professores : [],
        disciplinas: Array.isArray(opcoesApi.disciplinas) ? opcoesApi.disciplinas : [],
        leis: Array.isArray(opcoesApi.leis) ? opcoesApi.leis : [],
        artigos: Array.isArray(opcoesApi.artigos) ? opcoesApi.artigos : [],
        incisos: Array.isArray(opcoesApi.incisos) ? opcoesApi.incisos : [],
        alineas: Array.isArray(opcoesApi.alineas) ? opcoesApi.alineas : [],
        status: Array.isArray(opcoesApi.status) ? opcoesApi.status : [],
        quem_assina: Array.isArray(opcoesApi.quem_assina) ? opcoesApi.quem_assina : [],
        acoes_aplicadas: Array.isArray(opcoesApi.acoes_aplicadas) ? opcoesApi.acoes_aplicadas : [],
        regimento_itens: Array.isArray(opcoesApi.regimento_itens) ? opcoesApi.regimento_itens : [],
        status_padrao: opcoesApi.status_padrao || "registrado"
    };
    regimentoItensCache = Array.isArray(opcoesOcorrencias.regimento_itens)
        ? opcoesOcorrencias.regimento_itens.map((item) => ({
            ...item,
            atualizado_em: item.atualizado_em || "",
            criado_em: item.criado_em || ""
        }))
        : [];
    sincronizarCatalogosBaseLegal({
        leis: opcoesOcorrencias.leis,
        artigos: opcoesOcorrencias.artigos,
        incisos: opcoesOcorrencias.incisos,
        alineas: opcoesOcorrencias.alineas
    });

    rotulosAcao.clear();
    rotulosStatus.clear();
    rotulosTipoRegistro.clear();
    (opcoesOcorrencias.acoes_aplicadas || []).forEach((item) => {
        rotulosAcao.set(String(item.id), item.nome || item.id);
    });
    (opcoesOcorrencias.status || []).forEach((item) => {
        rotulosStatus.set(String(item.id), item.nome || item.id);
    });
    (opcoesOcorrencias.tipos_registro || []).forEach((item) => {
        rotulosTipoRegistro.set(String(item.id), item.nome || item.id);
    });

    preencherSelect("ocorrenciaTipoRegistro", opcoesOcorrencias.tipos_registro, {
        placeholder: "Selecione o tipo",
        valorPadrao: "estudante"
    });
    preencherSelect("filtroTipoRegistro", opcoesOcorrencias.tipos_registro, { incluirTodos: true });
    preencherSelect("relatorioTipoRegistro", opcoesOcorrencias.tipos_registro, { incluirTodos: true });
    preencherSelect("ocorrenciaTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("relatorioTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("ocorrenciaStatus", opcoesOcorrencias.status, {
        placeholder: "Selecione o status",
        valorPadrao: opcoesOcorrencias.status_padrao || "registrado"
    });
    preencherSelect("ocorrenciaQuemAssina", opcoesOcorrencias.quem_assina, {
        placeholder: "Selecione quem assina",
        valorPadrao: "responsavel"
    });
    preencherSelect("filtroStatus", opcoesOcorrencias.status, { incluirTodos: true });
    preencherSelect("relatorioStatus", opcoesOcorrencias.status, { incluirTodos: true });

    preencherSelect("estudanteTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroEstudanteTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    popularSugestoesProfessores();
    popularSugestoesDisciplinas();
    popularSugestoesRegimento();

    const idsSelecionadosSet = new Set(normalizarIdsRegimento(idsRegimentoSelecionados));
    const itensRegimentoSelecionados = (opcoesOcorrencias.regimento_itens || []).filter((item) =>
        idsSelecionadosSet.has(Number(item?.id || 0))
    );
    atualizarAcaoAplicadaPorGravidade({
        gravidade: inferirGravidadeOcorrenciaBaseLegal(itensRegimentoSelecionados),
        acaoAtual: acaoAplicadaAtual
    });

    atualizarSelectAulasPorTurma("");
    renderSelecionadorRegimento(idsRegimentoSelecionados);
    atualizarModoFormularioRegistro();
    atualizarPreviewOcorrencia();
}

function queryFiltrosOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "filtroNomeEstudante",
        tipoRegistroId: "filtroTipoRegistro",
        turmaIdId: "filtroTurmaId",
        statusId: "filtroStatus",
        dataInicialId: "filtroDataInicial",
        dataFinalId: "filtroDataFinal"
    });
}

function queryFiltrosRelatorioOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        tipoRegistroId: "relatorioTipoRegistro",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
}

function queryFiltrosEstudantes() {
    const params = new URLSearchParams();
    const nome = el("filtroEstudanteNome").value.trim();
    const turmaId = el("filtroEstudanteTurmaId").value;
    if (nome) params.set("nome", nome);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("incluir_inativos", "true");
    return `?${params.toString()}`;
}

function criarCelulaTabela(rotulo, conteudo = "") {
    const td = document.createElement("td");
    td.dataset.label = rotulo;
    if (typeof Node !== "undefined" && conteudo instanceof Node) {
        td.appendChild(conteudo);
    } else {
        td.innerText = conteudo ?? "";
    }
    return td;
}

function criarSelectSexoEstudante(estudante) {
    const select = document.createElement("select");
    const nome = String(estudante.nome || "estudante").trim();
    select.setAttribute("aria-label", `Sexo de ${nome}`);
    select.setAttribute("aria-describedby", "msgEstudantes");

    [
        ["", "Não informado"],
        ["F", "Feminino"],
        ["M", "Masculino"]
    ].forEach(([valor, rotulo]) => {
        const option = document.createElement("option");
        option.value = valor;
        option.textContent = rotulo;
        select.appendChild(option);
    });
    select.value = String(estudante.sexo || "");

    select.addEventListener("change", async () => {
        const sexoAnterior = String(estudante.sexo || "");
        select.disabled = true;
        select.setAttribute("aria-busy", "true");
        setMensagemEstudantes(`Salvando sexo de ${nome}...`);

        try {
            const atualizado = await fetchJson(`/estudantes/${estudante.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({
                    nome: estudante.nome,
                    turma_id: Number(estudante.turma_id),
                    sexo: select.value || null,
                    ativo: Boolean(estudante.ativo)
                })
            });
            Object.assign(estudante, atualizado);
            select.value = String(estudante.sexo || "");
            const celulaAtualizada = select
                .closest("tr")
                ?.querySelector('[data-label="Atualizado em"]');
            if (celulaAtualizada) {
                celulaAtualizada.textContent = formatarDataHora(estudante.atualizado_em);
            }
            setMensagemEstudantes(`Sexo de ${nome} atualizado com sucesso.`);
        } catch (err) {
            select.value = sexoAnterior;
            setMensagemEstudantes(`Não foi possível atualizar o sexo de ${nome}. ${err.message}`, true);
        } finally {
            select.disabled = false;
            select.removeAttribute("aria-busy");
        }
    });

    return select;
}

function renderTabelaOcorrencias() {
    const tbody = el("tbodyOcorrencias");
    atualizarResumoOcorrencias();
    tbody.innerHTML = "";

    if (!Array.isArray(ocorrenciasCache) || ocorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 7;
        td.className = "booking-empty";
        td.innerText = "Nenhum registro encontrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    ocorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        const selecionada = Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId);
        tr.classList.toggle("is-selected", selecionada);
        tr.addEventListener("click", () => {
            selecionarOcorrencia(ocorrencia);
        });

        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Tipo", rotuloTipoRegistro(ocorrencia.tipo_registro)));
        tr.appendChild(criarCelulaTabela("Referência", obterReferenciaRegistro(ocorrencia)));
        tr.appendChild(criarCelulaTabela("Contexto", obterContextoRegistro(ocorrencia)));
        tr.appendChild(criarCelulaTabela("Ação aplicada", rotuloAcao(ocorrencia.acao_aplicada)));

        const statusBadge = document.createElement("span");
        statusBadge.className = `status-chip ${classeStatus(ocorrencia.status)}`;
        statusBadge.innerText = rotuloStatus(ocorrencia.status);
        tr.appendChild(criarCelulaTabela("Status", statusBadge));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnPdf = document.createElement("button");
        btnPdf.type = "button";
        btnPdf.innerText = "PDF";
        btnPdf.addEventListener("click", (event) => {
            event.stopPropagation();
            abrirPdfOcorrencia(ocorrencia);
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", (event) => {
            event.stopPropagation();
            selecionarOcorrencia(ocorrencia);
            preencherFormularioOcorrencia(ocorrencia);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", (event) => {
            event.stopPropagation();
            excluirOcorrencia(ocorrencia);
        });

        linhaAcoes.appendChild(btnPdf);
        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Ações", linhaAcoes));

        tbody.appendChild(tr);
    });
}

function renderTabelaEstudantes() {
    const tbody = el("tbodyEstudantes");
    tbody.innerHTML = "";

    const filtroStatus = el("filtroEstudanteStatus").value;
    const estudantesFiltrados = (estudantesCache || []).filter((estudante) => {
        if (filtroStatus === "ativos") return Boolean(estudante.ativo);
        if (filtroStatus === "inativos") return !Boolean(estudante.ativo);
        return true;
    });

    if (estudantesFiltrados.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 6;
        td.className = "booking-empty";
        td.innerText = "Nenhum estudante encontrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    estudantesFiltrados.forEach((estudante) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Nome", estudante.nome || ""));
        tr.appendChild(criarCelulaTabela("Turma", estudante.turma_nome || ""));
        tr.appendChild(criarCelulaTabela("Sexo", criarSelectSexoEstudante(estudante)));

        const badge = document.createElement("span");
        badge.className = `status-chip ${classeStatusEstudante(Boolean(estudante.ativo))}`;
        badge.innerText = estudante.ativo ? "Ativo" : "Inativo";
        tr.appendChild(criarCelulaTabela("Status", badge));
        tr.appendChild(criarCelulaTabela("Atualizado em", formatarDataHora(estudante.atualizado_em)));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => iniciarEdicaoEstudante(estudante));

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = estudante.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/estudantes/${estudante.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(estudante.ativo) })
                });
                setMensagemEstudantes("Status atualizado.");
                await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
            } catch (err) {
                setMensagemEstudantes(err.message, true);
            }
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", () => {
            excluirEstudante(estudante);
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnStatus);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Ações", linhaAcoes));

        tbody.appendChild(tr);
    });
}

async function carregarOcorrencias() {
    ocorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosOcorrencias()}`, { headers });
    const ocorrenciaSelecionada = ocorrenciasCache.find(
        (ocorrencia) => Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId)
    ) || null;

    if (ocorrenciaSelecionada) {
        renderDetalhesOcorrencia(ocorrenciaSelecionada);
    } else if (ocorrenciaSelecionadaId) {
        ocorrenciaSelecionadaId = null;
        renderDetalhesOcorrencia(null);
    }

    renderTabelaOcorrencias();
}

async function carregarRelatorioOcorrencias() {
    setMensagemRelatorios("");
    relatorioOcorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosRelatorioOcorrencias()}`, { headers });
    relatorioOcorrenciasCarregado = true;
    renderRelatorioOcorrencias();
}

async function carregarEstudantes() {
    estudantesCache = await fetchJson(`/estudantes${queryFiltrosEstudantes()}`, { headers });
    renderTabelaEstudantes();
}
