function renderizarCabecalho() {
    const primeiroNome = obterPrimeiroNome();
    const possuiVisaoDocente = Boolean(contextoAtual?.professor_id);
    const possuiVisaoInstitucional = Boolean(contextoAtual?.pode_consolidar);
    let descricao = "visão institucional";
    if (possuiVisaoDocente && possuiVisaoInstitucional) {
        descricao = "registro docente e visão institucional";
    } else if (possuiVisaoDocente) {
        descricao = "registro docente";
    }
    el("preconselhoUsuario").textContent = `${primeiroNome} | ${descricao}`;
    el("btnIrAdmin").hidden = !Boolean(usuarioAtual?.eh_admin);
}

function renderizarAbasDisponiveis() {
    const mostrarDocente = Boolean(contextoAtual?.professor_id);
    const mostrarConsolidacao = Boolean(contextoAtual?.pode_consolidar);
    const mostrarRelatorio = Boolean(contextoAtual?.pode_relatorio);
    const mostrarRav = Boolean(contextoAtual?.pode_relatorio);
    const mostrarConfiguracoes = Boolean(contextoAtual?.pode_configurar);

    el("tabBtnDocente").hidden = !mostrarDocente;
    el("tabBtnConsolidacao").hidden = !mostrarConsolidacao;
    el("tabBtnReavaliacao").hidden = !mostrarConsolidacao;
    el("tabBtnRelatorio").hidden = !mostrarRelatorio;
    el("tabBtnRav").hidden = !mostrarRav;
    el("tabBtnConfiguracoes").hidden = !mostrarConfiguracoes;

    const ordem = [
        { aba: "docente", visivel: mostrarDocente },
        { aba: "consolidacao", visivel: mostrarConsolidacao },
        { aba: "reavaliacao", visivel: mostrarConsolidacao },
        { aba: "relatorio", visivel: mostrarRelatorio },
        { aba: "rav", visivel: mostrarRav },
        { aba: "configuracoes", visivel: mostrarConfiguracoes }
    ].filter((item) => item.visivel);

    const paginaPermitida = ordem.find((item) => item.aba === paginaPreconselhoAtual);
    if (!paginaPermitida && ordem.length > 0) {
        const destinos = {
            docente: "/preconselho",
            consolidacao: "/preconselho/consolidacao",
            reavaliacao: "/preconselho/reavaliacao",
            relatorio: "/preconselho/relatorios",
            rav: "/preconselho/rav",
            configuracoes: "/preconselho/configuracoes"
        };
        window.location.replace(destinos[ordem[0].aba] || "/preconselho");
        return;
    }
    ativarAba(paginaPreconselhoAtual);
}

function ativarAba(aba) {
    abaAtiva = aba || "";

    document.querySelectorAll("[data-preconselho-tab-trigger]").forEach((botao) => {
        const ativa = botao.dataset.preconselhoTabTrigger === abaAtiva;
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
        botao.tabIndex = ativa ? 0 : -1;
    });

    document.querySelectorAll("[data-preconselho-tab-panel]").forEach((painel) => {
        const ativo = painel.dataset.preconselhoTabPanel === abaAtiva;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

function renderizarSelectPeriodos() {
    const periodos = obterPeriodos();
    if (!estadoDocente.periodoId && periodos.length > 0) {
        const periodoReavaliacao = periodos.find(
            (item) => String(item.status || "").toUpperCase() === "EM_REAVALIACAO"
        );
        const periodoAberto = periodos.find(
            (item) => String(item.status || "").toUpperCase() === "ABERTO"
        );
        estadoDocente.periodoId = Number(periodoReavaliacao?.id || periodoAberto?.id || periodos[0].id);
    }

    preencherSelect(
        el("preconselhoPeriodoDocente"),
        periodos,
        (item) => item.id,
        (item) => `${rotuloPeriodo(item)} - ${rotuloStatusPeriodo(item.status).toLowerCase()}`,
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: estadoDocente.periodoId || periodos[0]?.id || ""
        }
    );

    preencherSelect(
        el("preconselhoPeriodoConsolidacao"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoConsolidacao")?.value || periodos[0]?.id || ""
        }
    );

    preencherSelect(
        el("preconselhoPeriodoRelatorio"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um período",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoRelatorio")?.value || periodos[0]?.id || ""
        }
    );

    preencherSelect(
        el("preconselhoPeriodoRav"),
        periodos,
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione um periodo",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoPeriodoRav")?.value || periodos[0]?.id || ""
        }
    );

    if (estadoDocente.periodoId) {
        el("preconselhoPeriodoDocente").value = String(estadoDocente.periodoId);
    }
}

function renderizarSelectsConsolidacao() {
    preencherSelect(
        el("preconselhoProfessorConsolidacao"),
        Array.isArray(contextoAtual?.professores) ? contextoAtual.professores : [],
        (item) => item.id,
        (item) => item.label || item.nome,
        "Todos os professores",
        {
            valorSelecionado: el("preconselhoProfessorConsolidacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoTurmaConsolidacao"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaConsolidacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoDisciplinaConsolidacao"),
        Array.isArray(contextoAtual?.disciplinas) ? contextoAtual.disciplinas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as disciplinas",
        {
            valorSelecionado: el("preconselhoDisciplinaConsolidacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoTurmaReavaliacao"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaReavaliacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoProfessorReavaliacao"),
        Array.isArray(contextoAtual?.professores) ? contextoAtual.professores : [],
        (item) => item.id,
        (item) => item.label || item.nome,
        "Todos os professores",
        {
            valorSelecionado: el("preconselhoProfessorReavaliacao")?.value || ""
        }
    );

    preencherSelect(
        el("preconselhoTurmaRav"),
        Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : [],
        (item) => item.id,
        (item) => item.nome,
        "Todas as turmas",
        {
            valorSelecionado: el("preconselhoTurmaRav")?.value || ""
        }
    );
}

function renderizarSelectDisciplinaHabilidadeRav() {
    preencherSelect(
        el("preconselhoRavHabilidadePeriodo"),
        obterPeriodos(),
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Selecione o periodo",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoRavHabilidadePeriodo")?.value || obterPeriodos()[0]?.id || ""
        }
    );
    preencherSelect(
        el("preconselhoRavImportPeriodo"),
        obterPeriodos(),
        (item) => item.id,
        (item) => rotuloPeriodo(item),
        "Periodo informado no JSON",
        {
            valorSelecionado: el("preconselhoRavImportPeriodo")?.value || ""
        }
    );
    preencherSelect(
        el("preconselhoRavHabilidadeDisciplina"),
        Array.isArray(contextoAtual?.disciplinas) ? contextoAtual.disciplinas : [],
        (item) => item.id,
        (item) => item.nome,
        "Selecione a disciplina",
        {
            permitirVazio: false,
            valorSelecionado: el("preconselhoRavHabilidadeDisciplina")?.value || ""
        }
    );
    const selectTurmas = el("preconselhoRavHabilidadeTurmas");
    const selecionadas = new Set(Array.from(selectTurmas?.selectedOptions || []).map((option) => option.value));
    if (selectTurmas) {
        selectTurmas.innerHTML = "";
        (Array.isArray(contextoAtual?.turmas) ? contextoAtual.turmas : []).forEach((turma) => {
            const option = document.createElement("option");
            option.value = String(turma.id);
            option.textContent = String(turma.nome || "");
            option.selected = selecionadas.has(option.value);
            selectTurmas.appendChild(option);
        });
        selectTurmas.disabled = selectTurmas.options.length === 0;
    }
}

function renderizarSelectNivelAtencao() {
    preencherSelect(
        el("preconselhoNivelAtencao"),
        Array.isArray(contextoAtual?.niveis_atencao) ? contextoAtual.niveis_atencao : [],
        (item) => item.id,
        (item) => item.nome,
        "Não informado",
        {
            valorSelecionado: ""
        }
    );
}

function renderizarSelectCategoriasMotivo() {
    preencherSelect(
        el("preconselhoMotivoCategoria"),
        CATEGORIAS_MOTIVO,
        (item) => item.id,
        (item) => item.nome,
        "Selecione a categoria",
        {
            permitirVazio: false
        }
    );
}

function renderizarMotivosDocente() {
    const container = el("preconselhoMotivosDocente");
    if (!container) {
        return;
    }

    const selecionados = new Set(obterMotivosSelecionadosDocente());
    const motivos = obterMotivosContexto().filter((item) => Number(item.ativo ?? 1) === 1);

    if (motivos.length === 0) {
        container.innerHTML = '<p class="pcpi-hint">Nenhum motivo ativo cadastrado.</p>';
        return;
    }

    const grupos = CATEGORIAS_MOTIVO
        .map((categoria) => ({
            ...categoria,
            motivos: motivos.filter((item) => item.categoria === categoria.id)
        }))
        .filter((grupo) => grupo.motivos.length > 0);

    container.innerHTML = grupos.map((grupo) => `
        <section class="preconselho-motivo-group">
            <h3>${escaparHtml(grupo.nome)}</h3>
            <div class="preconselho-motivos">
                ${grupo.motivos.map((motivo) => `
                    <label class="preconselho-motivo-option">
                        <input class="preconselho-motivo-checkbox" type="checkbox" value="${Number(motivo.id)}" ${selecionados.has(Number(motivo.id)) ? "checked" : ""}>
                        <span>${escaparHtml(motivo.descricao || "")}</span>
                    </label>
                `).join("")}
            </div>
        </section>
    `).join("");
}

function renderizarHabilidadesRavDocente(habilidadeIdsSelecionadas = null) {
    const container = el("preconselhoRavHabilidadesDocente");
    if (!container) {
        return;
    }

    const combo = comboDocenteAtual();
    const selecionados = new Set(
        Array.isArray(habilidadeIdsSelecionadas)
            ? habilidadeIdsSelecionadas.map((item) => Number(item))
            : obterHabilidadesRavSelecionadasDocente()
    );
    const habilidades = obterHabilidadesRavPorDisciplina(
        combo?.disciplina_id,
        false,
        estadoDocente.periodoId,
        combo?.turma_id
    );

    if (!combo) {
        container.innerHTML = '<p class="preconselho-rav-empty">Selecione uma turma e disciplina para buscar habilidades.</p>';
        ocultarSugestoesHabilidadesRav();
        return;
    }
    if (habilidades.length === 0) {
        container.innerHTML = '<p class="preconselho-rav-empty">Nenhuma habilidade ativa cadastrada para este periodo, turma e disciplina.</p>';
        ocultarSugestoesHabilidadesRav();
        return;
    }

    const itensSelecionados = habilidades.filter((habilidade) => selecionados.has(Number(habilidade.id || 0)));
    if (itensSelecionados.length === 0) {
        container.innerHTML = '<p class="preconselho-rav-empty">Nenhuma habilidade selecionada ainda.</p>';
        renderizarSugestoesHabilidadesRav(false);
        return;
    }

    container.innerHTML = itensSelecionados.map((habilidade) => `
        <article class="preconselho-rav-skill-card" data-rav-habilidade-selecionada-id="${Number(habilidade.id)}">
            <span>${escaparHtml([habilidade.codigo, habilidade.descricao].filter(Boolean).join(" - "))}</span>
            <button type="button" data-action="remover-habilidade-rav" data-habilidade-id="${Number(habilidade.id)}">Remover</button>
        </article>
    `).join("");
    renderizarSugestoesHabilidadesRav(false);
}

