function renderizarTabelaPeriodos() {
    const tbody = el("tbodyPeriodosPreconselho");
    if (!tbody) {
        return;
    }

    const periodos = obterPeriodos();
    if (periodos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="booking-empty">Nenhum período cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = periodos.map((item) => `
        <tr>
            <td data-label="Período">
                <strong>${escaparHtml(rotuloPeriodo(item))}</strong>
                <div class="preconselho-table-meta">${Number(item.ano_letivo || 0)} • etapa ${Number(item.etapa || 0)}${item.tem_rav ? " • RAV" : ""}</div>
            </td>
            <td data-label="Status">
                <span class="status-chip ${statusPeriodoClasse(item.status)}">${escaparHtml(rotuloStatusPeriodo(item.status))}</span>
            </td>
            <td data-label="Datas">
                ${escaparHtml(formatarDataBr(item.data_inicio))} a ${escaparHtml(formatarDataBr(item.data_fim))}
            </td>
            <td data-label="Ações">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-periodo" data-periodo-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-periodo" data-periodo-id="${Number(item.id)}" data-status="${escaparHtml(item.status || "")}">
                        ${item.status === "ABERTO" ? "Iniciar reavaliação" : (item.status === "EM_REAVALIACAO" ? "Encerrar" : "Reabrir")}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function renderizarTabelaMotivos() {
    const tbody = el("tbodyMotivosPreconselho");
    if (!tbody) {
        return;
    }

    const motivos = obterMotivosContexto();
    if (motivos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="booking-empty">Nenhum motivo cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = motivos.map((item) => `
        <tr>
            <td data-label="Categoria">
                <strong>${escaparHtml(rotuloCategoria(item.categoria))}</strong>
                <div class="preconselho-table-meta">${escaparHtml(item.codigo || "")}</div>
            </td>
            <td data-label="Descrição">
                ${escaparHtml(item.descricao || "")}
            </td>
            <td data-label="Status">
                <span class="status-chip ${Number(item.ativo ?? 1) === 1 ? "status-aberto" : "status-fechado"}">
                    ${Number(item.ativo ?? 1) === 1 ? "Ativo" : "Inativo"}
                </span>
            </td>
            <td data-label="Ações">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-motivo" data-motivo-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-motivo" data-motivo-id="${Number(item.id)}" data-ativo="${Number(item.ativo ?? 1)}">
                        ${Number(item.ativo ?? 1) === 1 ? "Inativar" : "Ativar"}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function sincronizarCatalogoReavaliacao(itens) {
    contextoAtual.motivos_reavaliacao_admin = itens;
    contextoAtual.motivos_pos_preconselho = {
        recuperado: itens.filter((item) => item.resultado === "recuperado" && Number(item.ativo) === 1)
            .map((item) => ({ id: item.codigo, descricao: item.descricao })),
        nao_recuperado: itens.filter((item) => item.resultado === "nao_recuperado" && Number(item.ativo) === 1)
            .map((item) => ({ id: item.codigo, descricao: item.descricao })),
    };
}

function renderizarTabelaMotivosReavaliacao() {
    const tbody = el("tbodyMotivosReavaliacao");
    if (!tbody) return;
    const itens = contextoAtual?.motivos_reavaliacao_admin || [];
    tbody.innerHTML = itens.map((item) => `
        <tr>
            <td data-label="Resultado">${item.resultado === "recuperado" ? "Recuperado" : "Ficou para o conselho"}</td>
            <td data-label="Código">${escaparHtml(item.codigo || "")}</td>
            <td data-label="Descrição">${escaparHtml(item.descricao || "")}</td>
            <td data-label="Status">${Number(item.ativo) === 1 ? "Ativo" : "Inativo"}</td>
            <td data-label="Ações"><div class="preconselho-table-actions">
                <button type="button" data-action="editar-motivo-reavaliacao" data-id="${Number(item.id)}">Editar</button>
                <button type="button" data-action="status-motivo-reavaliacao" data-id="${Number(item.id)}" data-ativo="${Number(item.ativo)}">${Number(item.ativo) === 1 ? "Inativar" : "Ativar"}</button>
            </div></td>
        </tr>`).join("");
}

async function carregarMotivosReavaliacaoAdmin() {
    if (!contextoAtual?.pode_configurar) return;
    const resposta = await fetchComAuth("/preconselho/motivos-reavaliacao?incluir_inativos=true", { headers });
    if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar os motivos da reavaliação."));
    sincronizarCatalogoReavaliacao(await resposta.json());
    renderizarTabelaMotivosReavaliacao();
}

function limparFormularioMotivoReavaliacao() {
    el("preconselhoMotivoReavaliacaoId").value = "";
    el("preconselhoMotivoReavaliacaoResultado").value = "recuperado";
    el("preconselhoMotivoReavaliacaoCodigo").value = "";
    el("preconselhoMotivoReavaliacaoCodigo").disabled = false;
    el("preconselhoMotivoReavaliacaoDescricao").value = "";
    el("preconselhoMotivoReavaliacaoOrdem").value = "0";
}

async function salvarMotivoReavaliacao(event) {
    event.preventDefault();
    limparMensagem("msgMotivoReavaliacao");
    const id = Number(el("preconselhoMotivoReavaliacaoId").value || 0);
    const payload = {
        resultado: el("preconselhoMotivoReavaliacaoResultado").value,
        descricao: el("preconselhoMotivoReavaliacaoDescricao").value.trim(),
        ordem: Number(el("preconselhoMotivoReavaliacaoOrdem").value || 0),
    };
    if (!id) payload.codigo = el("preconselhoMotivoReavaliacaoCodigo").value.trim();
    try {
        const resposta = await fetchComAuth(id ? `/preconselho/motivos-reavaliacao/${id}` : "/preconselho/motivos-reavaliacao", {
            method: id ? "PUT" : "POST", headers: headersJson, body: JSON.stringify(payload)
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar o motivo."));
        await carregarMotivosReavaliacaoAdmin();
        limparFormularioMotivoReavaliacao();
        definirMensagem("msgMotivoReavaliacao", "Motivo salvo com sucesso.");
    } catch (erro) { definirMensagem("msgMotivoReavaliacao", erro.message, true); }
}

function renderizarTabelaHabilidadesRav() {
    const tbody = el("tbodyHabilidadesRavPreconselho");
    if (!tbody) {
        return;
    }

    const habilidades = obterHabilidadesRavContexto();
    if (habilidades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="booking-empty">Nenhuma habilidade de RAV cadastrada.</td></tr>';
        return;
    }

    tbody.innerHTML = habilidades.map((item) => `
        <tr>
            <td data-label="Periodo">
                <strong>${escaparHtml(item.periodo_nome || "")}</strong>
            </td>
            <td data-label="Disciplina">
                <strong>${escaparHtml(item.disciplina_nome || "")}</strong>
                <div class="preconselho-table-meta">Ordem ${Number(item.ordem || 0)}</div>
            </td>
            <td data-label="Codigo">
                ${escaparHtml(item.codigo || "")}
            </td>
            <td data-label="Habilidade">
                ${escaparHtml(item.descricao || "")}
            </td>
            <td data-label="Turmas">
                ${escaparHtml((Array.isArray(item.turmas) ? item.turmas : []).map((turma) => turma.nome).filter(Boolean).join(", "))}
            </td>
            <td data-label="Status">
                <span class="status-chip ${Number(item.ativo ?? 1) === 1 ? "status-aberto" : "status-fechado"}">
                    ${Number(item.ativo ?? 1) === 1 ? "Ativa" : "Inativa"}
                </span>
            </td>
            <td data-label="Acoes">
                <div class="preconselho-table-actions">
                    <button type="button" data-action="editar-habilidade-rav" data-habilidade-id="${Number(item.id)}">Editar</button>
                    <button type="button" data-action="status-habilidade-rav" data-habilidade-id="${Number(item.id)}" data-ativo="${Number(item.ativo ?? 1)}">
                        ${Number(item.ativo ?? 1) === 1 ? "Inativar" : "Ativar"}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

function limparFormularioPeriodo() {
    el("preconselhoPeriodoEdicaoId").value = "";
    el("preconselhoPeriodoNome").value = "";
    el("preconselhoPeriodoAnoLetivo").value = String(new Date().getFullYear());
    el("preconselhoPeriodoEtapa").value = "1";
    el("preconselhoPeriodoDataInicio").value = "";
    el("preconselhoPeriodoDataFim").value = "";
    el("preconselhoPeriodoStatusForm").value = "ABERTO";
    el("preconselhoPeriodoTemRav").checked = false;
}

function limparFormularioMotivo() {
    el("preconselhoMotivoEdicaoId").value = "";
    el("preconselhoMotivoCategoria").value = CATEGORIAS_MOTIVO[0].id;
    el("preconselhoMotivoCodigo").value = "";
    el("preconselhoMotivoCodigo").disabled = false;
    el("preconselhoMotivoDescricao").value = "";
    el("preconselhoMotivoOrdem").value = "0";
}

function limparFormularioHabilidadeRav() {
    el("preconselhoRavHabilidadeEdicaoId").value = "";
    el("preconselhoRavHabilidadePeriodo").selectedIndex = 0;
    el("preconselhoRavHabilidadeDisciplina").selectedIndex = 0;
    el("preconselhoRavHabilidadeCodigo").value = "";
    Array.from(el("preconselhoRavHabilidadeTurmas").options || []).forEach((option) => {
        option.selected = false;
    });
    el("preconselhoRavHabilidadeDescricao").value = "";
    el("preconselhoRavHabilidadeOrdem").value = "0";
}

function carregarPeriodoNoFormulario(periodoId) {
    const periodo = obterPeriodos().find((item) => Number(item.id) === Number(periodoId));
    if (!periodo) {
        return;
    }

    el("preconselhoPeriodoEdicaoId").value = String(periodo.id);
    el("preconselhoPeriodoNome").value = String(periodo.nome || "");
    el("preconselhoPeriodoAnoLetivo").value = String(periodo.ano_letivo || "");
    el("preconselhoPeriodoEtapa").value = String(periodo.etapa || "1");
    el("preconselhoPeriodoDataInicio").value = String(periodo.data_inicio || "");
    el("preconselhoPeriodoDataFim").value = String(periodo.data_fim || "");
    el("preconselhoPeriodoStatusForm").value = String(periodo.status === "FECHADO" ? "ENCERRADO" : (periodo.status || "ENCERRADO"));
    el("preconselhoPeriodoTemRav").checked = Boolean(periodo.tem_rav);
}

function carregarMotivoNoFormulario(motivoId) {
    const motivo = obterMotivosContexto().find((item) => Number(item.id) === Number(motivoId));
    if (!motivo) {
        return;
    }

    el("preconselhoMotivoEdicaoId").value = String(motivo.id);
    el("preconselhoMotivoCategoria").value = String(motivo.categoria || CATEGORIAS_MOTIVO[0].id);
    el("preconselhoMotivoCodigo").value = String(motivo.codigo || "");
    el("preconselhoMotivoCodigo").disabled = true;
    el("preconselhoMotivoDescricao").value = String(motivo.descricao || "");
    el("preconselhoMotivoOrdem").value = String(Number(motivo.ordem || 0));
}

function carregarHabilidadeRavNoFormulario(habilidadeId) {
    const habilidade = obterHabilidadesRavContexto().find((item) => Number(item.id) === Number(habilidadeId));
    if (!habilidade) {
        return;
    }

    el("preconselhoRavHabilidadeEdicaoId").value = String(habilidade.id);
    el("preconselhoRavHabilidadePeriodo").value = String(habilidade.periodo_id || "");
    el("preconselhoRavHabilidadeDisciplina").value = String(habilidade.disciplina_id || "");
    el("preconselhoRavHabilidadeCodigo").value = String(habilidade.codigo || "");
    const turmaIds = new Set((Array.isArray(habilidade.turma_ids) ? habilidade.turma_ids : []).map((item) => String(item)));
    Array.from(el("preconselhoRavHabilidadeTurmas").options || []).forEach((option) => {
        option.selected = turmaIds.has(option.value);
    });
    el("preconselhoRavHabilidadeDescricao").value = String(habilidade.descricao || "");
    el("preconselhoRavHabilidadeOrdem").value = String(Number(habilidade.ordem || 0));
}

async function recarregarPeriodos() {
    const resposta = await fetchComAuth("/preconselho/periodos", { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar os períodos."));
    }

    const periodos = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        periodos
    };
    renderizarSelectPeriodos();
    renderizarSelectDisciplinaHabilidadeRav();
    renderizarTabelaPeriodos();
}

async function recarregarMotivos() {
    const incluirInativos = Boolean(contextoAtual?.pode_configurar);
    const sufixo = incluirInativos ? "?incluir_inativos=true" : "";
    const resposta = await fetchComAuth(`/preconselho/motivos${sufixo}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível atualizar os motivos."));
    }

    const motivos = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        motivos
    };
    renderizarMotivosDocente();
    renderizarTabelaMotivos();
}

async function recarregarHabilidadesRav() {
    const incluirInativos = Boolean(contextoAtual?.pode_configurar);
    const sufixo = incluirInativos ? "?incluir_inativos=true" : "";
    const resposta = await fetchComAuth(`/preconselho/habilidades-rav${sufixo}`, { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel atualizar as habilidades de RAV."));
    }

    const rav_habilidades = await resposta.json();
    contextoAtual = {
        ...contextoAtual,
        rav_habilidades
    };
    renderizarHabilidadesRavDocente();
    renderizarTabelaHabilidadesRav();
    await carregarMotivosReavaliacaoAdmin();
}

