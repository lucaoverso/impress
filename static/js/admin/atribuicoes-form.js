async function carregarContextoAtribuicoesDocentes() {
    const dados = await fetchJson("/admin/atribuicoes-docentes/contexto", { headers });
    contextoAtribuicoesDocentes = {
        professores: Array.isArray(dados.professores) ? dados.professores : [],
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    preencherSelectComItens(
        "atribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Selecione o professor",
        { labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "atribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Selecione a disciplina"
    );

    preencherSelectComItens(
        "filtroAtribuicaoProfessor",
        contextoAtribuicoesDocentes.professores,
        "Todos os professores",
        { permitirVazio: true, labelFn: (item) => item.label || item.nome || "" }
    );
    preencherSelectComItens(
        "filtroAtribuicaoTurma",
        contextoAtribuicoesDocentes.turmas,
        "Todas as turmas",
        { permitirVazio: true }
    );
    preencherSelectComItens(
        "filtroAtribuicaoDisciplina",
        contextoAtribuicoesDocentes.disciplinas,
        "Todas as disciplinas",
        { permitirVazio: true }
    );

    await carregarTurmasAtribuidasProfessorDisciplina();
}

function obterProfessorIdAtribuicaoFormulario() {
    return Number(el("atribuicaoProfessor")?.value || 0);
}

function obterDisciplinaIdAtribuicaoFormulario() {
    return Number(el("atribuicaoDisciplina")?.value || 0);
}

function obterTurmaIdsSelecionadasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return [];
    }
    return Array.from(container.querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => Number(input.value))
        .filter((valor) => Number.isFinite(valor) && valor > 0);
}

function atualizarResumoTurmasAtribuicao() {
    const resumo = el("atribuicaoTurmasResumo");
    if (!resumo) {
        return;
    }

    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    if (professorId <= 0 || disciplinaId <= 0) {
        resumo.innerText = "Selecione professor e disciplina para carregar as turmas.";
        return;
    }

    const selecionadas = obterTurmaIdsSelecionadasAtribuicao();
    if (selecionadas.length === 0) {
        resumo.innerText = "Nenhuma turma marcada. Salvar agora remove as atribuicoes desta disciplina para o professor.";
        return;
    }

    resumo.innerText = `${selecionadas.length} turma(s) marcada(s) para esta disciplina.`;
}

function renderTurmasAtribuicaoCheckboxes(turmaIdsSelecionadas = []) {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!Array.isArray(contextoAtribuicoesDocentes.turmas) || contextoAtribuicoesDocentes.turmas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma ativa cadastrada.";
        container.appendChild(vazio);
        atualizarResumoTurmasAtribuicao();
        return;
    }

    const selecionadas = new Set((turmaIdsSelecionadas || []).map((item) => String(item)));
    contextoAtribuicoesDocentes.turmas.forEach((turma, index) => {
        const label = document.createElement("label");
        label.className = "admin-checkbox-item admin-checkbox-item-stack";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = `atribuicao_turma_${index}_${turma.id}`;
        input.value = String(turma.id);
        input.checked = selecionadas.has(String(turma.id));
        input.addEventListener("change", atualizarResumoTurmasAtribuicao);

        const texto = document.createElement("span");
        texto.innerText = turma.nome;

        const detalhe = document.createElement("small");
        detalhe.className = "admin-checkbox-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)}`;

        const conteudo = document.createElement("div");
        conteudo.className = "admin-checkbox-content";
        conteudo.appendChild(texto);
        conteudo.appendChild(detalhe);

        label.appendChild(input);
        label.appendChild(conteudo);
        container.appendChild(label);
    });

    atualizarResumoTurmasAtribuicao();
}

async function carregarTurmasAtribuidasProfessorDisciplina() {
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();

    if (professorId <= 0 || disciplinaId <= 0) {
        renderTurmasAtribuicaoCheckboxes([]);
        return;
    }

    const lista = await fetchJson(
        `/admin/atribuicoes-docentes?professor_id=${professorId}&disciplina_id=${disciplinaId}`,
        { headers }
    );
    renderTurmasAtribuicaoCheckboxes(
        (Array.isArray(lista) ? lista : []).map((item) => Number(item.turma_id))
    );
}

function selecionarTodasTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = true;
    });
    atualizarResumoTurmasAtribuicao();
}

function limparSelecaoTurmasAtribuicao() {
    const container = el("atribuicaoTurmasLista");
    if (!container) {
        return;
    }
    Array.from(container.querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = false;
    });
    atualizarResumoTurmasAtribuicao();
}

function queryAtribuicoesDocentes() {
    const params = new URLSearchParams();
    const professorId = el("filtroAtribuicaoProfessor")?.value || "";
    const turmaId = el("filtroAtribuicaoTurma")?.value || "";
    const disciplinaId = el("filtroAtribuicaoDisciplina")?.value || "";
    if (professorId) params.set("professor_id", professorId);
    if (turmaId) params.set("turma_id", turmaId);
    if (disciplinaId) params.set("disciplina_id", disciplinaId);
    return params.toString() ? `?${params.toString()}` : "";
}


function limparFiltrosAtribuicoesDocentes() {
    if (el("filtroAtribuicaoProfessor")) el("filtroAtribuicaoProfessor").value = "";
    if (el("filtroAtribuicaoTurma")) el("filtroAtribuicaoTurma").value = "";
    if (el("filtroAtribuicaoDisciplina")) el("filtroAtribuicaoDisciplina").value = "";
    carregarAtribuicoesDocentes().catch((err) => {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    });
}
