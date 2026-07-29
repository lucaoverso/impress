async function carregarUsuario() {
    const resposta = await fetchComAuth("/me", { headers });
    if (!resposta.ok) {
        throw new Error("Não foi possível carregar o usuário.");
    }

    usuarioAtual = await resposta.json();
    if (!modulosPermitidos(usuarioAtual).has("preconselho")) {
        window.location.href = "/servicos";
        return;
    }

    renderizarCabecalho();
}

async function carregarContexto() {
    const resposta = await fetchComAuth("/preconselho/contexto", { headers });
    if (!resposta.ok) {
        throw new Error(await obterMensagemErroResposta(resposta, "Não foi possível carregar o contexto do pré-conselho."));
    }

    contextoAtual = await resposta.json();

    renderizarCabecalho();
    renderizarAbasDisponiveis();
    renderizarSelectPeriodos();
    renderizarSelectsConsolidacao();
    renderizarSelectDisciplinaHabilidadeRav();
    renderizarSelectNivelAtencao();
    renderizarSelectCategoriasMotivo();
    renderizarMotivosDocente();
    renderizarTabelaPeriodos();
    renderizarTabelaMotivos();
    renderizarTabelaHabilidadesRav();

    if (!el("preconselhoPeriodoConsolidacao").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoConsolidacao").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }
    if (!el("preconselhoPeriodoRelatorio").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoRelatorio").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }
    if (!el("preconselhoPeriodoRav").value && obterPeriodos().length > 0) {
        const periodoAberto = obterPeriodos().find((item) => item.status === "ABERTO");
        el("preconselhoPeriodoRav").value = String(periodoAberto?.id || obterPeriodos()[0].id);
    }

    renderizarRelatorio();
    renderizarRav();
    renderizarPainelReavaliacao();
}

async function carregarPainelInicial() {
    const tarefas = [];
    if (paginaPreconselhoAtual === "docente" && usuarioEhProfessor(usuarioAtual)) {
        tarefas.push(carregarPainelDocente());
    }
    if (paginaPreconselhoAtual === "consolidacao" && contextoAtual?.pode_consolidar) {
        tarefas.push(carregarConsolidacao());
    }
    if (paginaPreconselhoAtual === "reavaliacao" && contextoAtual?.pode_consolidar) {
        tarefas.push(carregarPainelReavaliacao());
    }
    if (paginaPreconselhoAtual === "relatorio" && contextoAtual?.pode_relatorio) {
        tarefas.push(carregarRelatorio());
    }
    if (paginaPreconselhoAtual === "rav" && contextoAtual?.pode_relatorio) {
        tarefas.push(carregarRav());
    }
    await Promise.all(tarefas);
}

