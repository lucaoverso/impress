async function inicializarAdminTurmas() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) return;

        configuracoesAulasAdmin = await fetchJson("/admin/configuracao-aulas?incluir_inativas=true", { headers });
        atualizarJanelaAulasFormularioTurma({ forcarPadrao: true });
        el("formTurma").addEventListener("submit", cadastrarTurma);
        el("turmaTurno").addEventListener("change", () => atualizarJanelaAulasFormularioTurma({ forcarPadrao: true }));
        el("turmaAulaInicial").addEventListener("change", atualizarJanelaAulasFormularioTurma);
        el("formDisciplina").addEventListener("submit", cadastrarDisciplina);

        const tarefas = [carregarTurmasAdmin(), carregarDisciplinasAdmin()];
        if (usuarioEhAdmin) {
            tarefas.push(carregarContextoTurmasDisciplinas().then(carregarTurmasDisciplinasAdmin));
        } else {
            document.querySelectorAll("[data-admin-only='true']").forEach((elemento) => { elemento.hidden = true; });
        }
        await Promise.all(tarefas);
    } catch (err) {
        setMensagem("msgTurma", err.message || "Falha ao carregar turmas e disciplinas.", true);
    }
}

inicializarAdminTurmas();
