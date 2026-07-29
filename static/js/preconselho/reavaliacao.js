function statusDisciplinaReavaliacao(registro) {
    if (registro.pos_preconselho_recuperado === true) {
        return { rotulo: "Recuperado", classe: "is-recuperado" };
    }
    if (registro.pos_preconselho_recuperado === false) {
        return { rotulo: "Ficou para o conselho", classe: "is-conselho" };
    }
    return { rotulo: "Em reavaliação", classe: "is-pendente" };
}

function resultadoRegistroReavaliacao(registro) {
    if (registro?.pos_preconselho_recuperado === true) return "recuperado";
    if (registro?.pos_preconselho_recuperado === false) return "nao_recuperado";
    return "";
}

function renderizarEditorGestaoReavaliacao(registro) {
    const resultado = estadoPainelReavaliacao.resultadoEmEdicao;
    const motivos = Array.isArray(contextoAtual?.motivos_pos_preconselho?.[resultado])
        ? contextoAtual.motivos_pos_preconselho[resultado]
        : [];
    const selecionados = new Set(registro.pos_preconselho_motivo_ids || []);
    return `
        <form class="preconselho-review-manager-form" data-form-reavaliacao-id="${Number(registro.id)}">
            <fieldset>
                <legend>Resultado da reavaliação</legend>
                <label><input type="radio" name="resultadoGestaoReavaliacao" value="recuperado" ${resultado === "recuperado" ? "checked" : ""}> Recuperado</label>
                <label><input type="radio" name="resultadoGestaoReavaliacao" value="nao_recuperado" ${resultado === "nao_recuperado" ? "checked" : ""}> Ficou para o conselho</label>
            </fieldset>
            <fieldset class="preconselho-review-manager-reasons" ${resultado ? "" : "hidden"}>
                <legend>Motivos</legend>
                ${motivos.map((motivo) => `<label><input type="checkbox" name="motivoGestaoReavaliacao" value="${escaparHtml(motivo.id || "")}" ${selecionados.has(String(motivo.id || "")) ? "checked" : ""}> ${escaparHtml(motivo.descricao || "")}</label>`).join("") || "<p>Nenhum motivo disponível para este resultado.</p>"}
            </fieldset>
            <label class="pcpi-field">
                <span>Observação (opcional)</span>
                <textarea name="observacaoGestaoReavaliacao" rows="3" maxlength="1000">${escaparHtml(registro.pos_preconselho_observacao || "")}</textarea>
            </label>
            <p class="pcpi-hint">Registro originalmente atribuído a ${escaparHtml(registro.professor_nome || "professor não informado")}.</p>
            <div class="pcpi-inline-actions">
                <button class="btn-destaque" type="submit">Salvar reavaliação</button>
                <button type="button" data-action="cancelar-reavaliacao-gestao">Cancelar</button>
            </div>
            <p class="pcpi-status-copy" data-msg-reavaliacao-id="${Number(registro.id)}"></p>
        </form>`;
}

function agruparRegistrosPainelReavaliacao(registros) {
    const grupos = new Map();
    registros.forEach((registro) => {
        const chave = String(registro.estudante_id || registro.estudante_nome || "");
        const grupo = grupos.get(chave) || {
            id: registro.estudante_id,
            nome: registro.estudante_nome || "Estudante sem nome",
            turma: registro.turma_nome || "Turma não informada",
            disciplinas: []
        };
        grupo.disciplinas.push(registro);
        grupos.set(chave, grupo);
    });
    return Array.from(grupos.values()).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

function renderizarPainelReavaliacao() {
    const container = el("listaPainelReavaliacao");
    const periodo = estadoPainelReavaliacao.periodo;
    const registros = estadoPainelReavaliacao.registros;
    const estudantes = agruparRegistrosPainelReavaliacao(estadoPainelReavaliacao.registros);
    const totalPendentes = registros.filter((item) => item.pos_preconselho_recuperado === null).length;
    const totalRecuperados = registros.filter((item) => item.pos_preconselho_recuperado === true).length;
    const totalParaConselho = registros.filter((item) => item.pos_preconselho_recuperado === false).length;
    el("preconselhoTotalEmReavaliacao").textContent = String(totalPendentes);
    el("preconselhoTotalRecuperados").textContent = String(totalRecuperados);
    el("preconselhoTotalParaConselho").textContent = String(totalParaConselho);
    el("preconselhoReavaliacaoPeriodoNome").textContent = periodo ? rotuloPeriodo(periodo) : "Nenhum período ativo";

    if (!periodo) {
        el("preconselhoResumoPainelReavaliacao").textContent = "Inicie a reavaliação de um período para habilitar este painel.";
        container.innerHTML = '<p class="preconselho-empty-state">Não há período em reavaliação no momento.</p>';
        return;
    }
    if (estudantes.length === 0) {
        el("preconselhoResumoPainelReavaliacao").textContent = "Nenhum estudante encontrado para o filtro aplicado.";
        container.innerHTML = '<p class="preconselho-empty-state">Nenhum estudante está em reavaliação nesta turma.</p>';
        return;
    }

    const totalRegistros = registros.length;
    el("preconselhoResumoPainelReavaliacao").textContent = `${estudantes.length} estudante(s) único(s) • ${totalRegistros} registro(s) disciplinar(es). Os indicadores acima contabilizam os registros.`;
    container.innerHTML = estudantes.map((estudante) => {
        const chave = String(estudante.id || estudante.nome);
        const expandido = estadoPainelReavaliacao.estudantesExpandidos.has(chave);
        const disciplinas = estudante.disciplinas
            .slice()
            .sort((a, b) => String(a.disciplina_nome || "").localeCompare(String(b.disciplina_nome || ""), "pt-BR"));
        return `
            <section class="preconselho-review-student">
                <button type="button" class="preconselho-review-student-toggle"
                    data-estudante-reavaliacao="${escaparHtml(chave)}" aria-expanded="${expandido ? "true" : "false"}">
                    <span><strong>${escaparHtml(estudante.nome)}</strong><small>${escaparHtml(estudante.turma)} • ${disciplinas.length} disciplina(s)</small></span>
                    <span class="preconselho-review-chevron" aria-hidden="true"></span>
                </button>
                <div class="preconselho-review-disciplines" ${expandido ? "" : "hidden"}>
                    ${disciplinas.map((disciplina) => {
                        const status = statusDisciplinaReavaliacao(disciplina);
                        return `<div class="preconselho-review-discipline">
                            <div class="preconselho-review-discipline-main">
                                <span>${escaparHtml(disciplina.disciplina_nome || "Disciplina não informada")}</span>
                                <small>${escaparHtml(disciplina.professor_nome || "Professor não informado")}</small>
                            </div>
                            <div class="preconselho-review-discipline-actions">
                                <strong class="preconselho-review-status ${status.classe}">${status.rotulo}</strong>
                                <button type="button" data-action="editar-reavaliacao-gestao" data-registro-id="${Number(disciplina.id)}">
                                    ${disciplina.pos_preconselho_recuperado === null ? "Registrar reavaliação" : "Alterar resultado"}
                                </button>
                            </div>
                            ${Number(estadoPainelReavaliacao.registroEmEdicaoId) === Number(disciplina.id) ? renderizarEditorGestaoReavaliacao(disciplina) : ""}
                        </div>`;
                    }).join("")}
                </div>
            </section>`;
    }).join("");
}

async function carregarPainelReavaliacao() {
    limparMensagem("msgPreconselhoReavaliacao");
    const periodo = obterPeriodos().find((item) => String(item.status || "").toUpperCase() === "EM_REAVALIACAO") || null;
    estadoPainelReavaliacao.periodo = periodo;
    estadoPainelReavaliacao.registros = [];
    if (!periodo) {
        renderizarPainelReavaliacao();
        return;
    }

    const params = new URLSearchParams({ periodo_id: String(periodo.id) });
    const turmaId = String(el("preconselhoTurmaReavaliacao")?.value || "").trim();
    const professorId = String(el("preconselhoProfessorReavaliacao")?.value || "").trim();
    if (turmaId) params.set("turma_id", turmaId);
    if (professorId) params.set("professor_id", professorId);
    try {
        const resposta = await fetchComAuth(`/preconselho/registros?${params.toString()}`, { headers });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar as reavaliações."));
        const dados = await resposta.json();
        estadoPainelReavaliacao.registros = Array.isArray(dados.itens) ? dados.itens : [];
        renderizarPainelReavaliacao();
    } catch (erro) {
        renderizarPainelReavaliacao();
        definirMensagem("msgPreconselhoReavaliacao", erro.message || "Não foi possível carregar as reavaliações.", true);
    }
}

async function salvarReavaliacaoGestao(form) {
    const registroId = Number(form.dataset.formReavaliacaoId || 0);
    const resultado = form.querySelector('[name="resultadoGestaoReavaliacao"]:checked')?.value || "";
    const motivoIds = Array.from(form.querySelectorAll('[name="motivoGestaoReavaliacao"]:checked')).map((item) => item.value);
    const observacao = String(form.querySelector('[name="observacaoGestaoReavaliacao"]')?.value || "").trim();
    const mensagem = form.querySelector("[data-msg-reavaliacao-id]");
    if (!resultado || motivoIds.length === 0) {
        mensagem.textContent = "Selecione o resultado e ao menos um motivo.";
        mensagem.dataset.state = "erro";
        return;
    }
    const botao = form.querySelector('button[type="submit"]');
    botao.disabled = true;
    botao.textContent = "Salvando...";
    try {
        const resposta = await fetchComAuth(`/preconselho/registros/${registroId}/reavaliacao`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({ recuperado: resultado === "recuperado", motivo_ids: motivoIds, observacao })
        });
        if (!resposta.ok) throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível salvar a reavaliação."));
        estadoPainelReavaliacao.registroEmEdicaoId = null;
        estadoPainelReavaliacao.resultadoEmEdicao = "";
        await carregarPainelReavaliacao();
        definirMensagem("msgPreconselhoReavaliacao", "Reavaliação registrada pela gestão com sucesso.");
    } catch (erro) {
        mensagem.textContent = erro.message || "Não foi possível salvar a reavaliação.";
        mensagem.dataset.state = "erro";
        botao.disabled = false;
        botao.textContent = "Salvar reavaliação";
    }
}

