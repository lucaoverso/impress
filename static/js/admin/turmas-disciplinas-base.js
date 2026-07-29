async function carregarContextoTurmasDisciplinas() {
    const dados = await fetchJson("/admin/turmas-disciplinas/contexto", { headers });
    contextoTurmasDisciplinas = {
        professores: Array.isArray(dados.professores) ? dados.professores : [],
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };
}

function registrarTurmasDisciplinasExpandidas() {
    const container = el("listaTurmasDisciplinasAdmin");
    if (!container) {
        return;
    }
    turmasDisciplinasExpandidas.clear();
    Array.from(container.querySelectorAll("details[data-turma-id][open]")).forEach((item) => {
        const turmaId = String(item.dataset.turmaId || "").trim();
        if (turmaId) {
            turmasDisciplinasExpandidas.add(turmaId);
        }
    });
}

function disciplinaBasePorId(disciplinaId) {
    return (Array.isArray(contextoTurmasDisciplinas.disciplinas) ? contextoTurmasDisciplinas.disciplinas : [])
        .find((item) => Number(item.id) === Number(disciplinaId)) || null;
}

function resumoMarcacoesDisciplina(disciplina) {
    return [
        disciplina?.tem_apc ? "APC" : null,
        disciplina?.tem_prova_bimestral ? "Prova bimestral" : null
    ].filter(Boolean).join(" | ");
}

function construirSelectProfessorTurmaDisciplina(valorAtual = "", professorAtual = null) {
    const select = document.createElement("select");
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.innerText = "Sem professor";
    select.appendChild(vazio);

    const professores = Array.isArray(contextoTurmasDisciplinas.professores)
        ? [...contextoTurmasDisciplinas.professores]
        : [];
    const possuiAtual = professores.some((item) => Number(item.id) === Number(valorAtual));
    if (!possuiAtual && Number(valorAtual) > 0 && professorAtual) {
        professores.push({
            id: Number(valorAtual),
            nome: professorAtual.professor_nome || "Professor vinculado",
            label: professorAtual.professor_nome || "Professor vinculado"
        });
    }

    professores
        .sort((a, b) => String(a.nome || a.label || "").localeCompare(String(b.nome || b.label || ""), "pt-BR"))
        .forEach((professor) => {
            const option = document.createElement("option");
            option.value = String(professor.id);
            option.innerText = professor.label || professor.nome || "";
            select.appendChild(option);
        });

    select.value = valorAtual ? String(valorAtual) : "";
    return select;
}

function construirSelectDisciplinasTurma(itensTurma = []) {
    const select = document.createElement("select");
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.innerText = "Selecione uma disciplina";
    select.appendChild(vazio);

    const disciplinaIdsTurma = new Set((itensTurma || []).map((item) => Number(item.disciplina_id)));
    const disciplinas = (Array.isArray(contextoTurmasDisciplinas.disciplinas) ? contextoTurmasDisciplinas.disciplinas : [])
        .filter((disciplina) => !disciplinaIdsTurma.has(Number(disciplina.id)))
        .sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"));

    disciplinas.forEach((disciplina) => {
        const option = document.createElement("option");
        option.value = String(disciplina.id);
        const marcacoes = resumoMarcacoesDisciplina(disciplina);
        option.innerText = marcacoes
            ? `${disciplina.nome} (${disciplina.aulas_semanais ?? 0}h base • ${marcacoes})`
            : `${disciplina.nome} (${disciplina.aulas_semanais ?? 0}h base)`;
        select.appendChild(option);
    });
    return select;
}

async function salvarTurmaDisciplinaInline(item, cargaInput, professorSelect) {
    try {
        const resposta = await fetchJson(`/admin/turmas-disciplinas/${item.id}`, {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                carga_horaria: Number(cargaInput.value || 0),
                professor_id: professorSelect.value ? Number(professorSelect.value) : null
            })
        });
        const professorTexto = resposta.professor_nome
            ? ` com ${resposta.professor_nome}`
            : " sem professor vinculado";
        setMensagem("msgTurmaDisciplina", `${resposta.disciplina_nome} atualizada em ${resposta.turma_nome}${professorTexto}.`);
        await Promise.all([
            carregarTurmasDisciplinasAdmin(),
            carregarDisciplinasAdmin()
        ]);
    } catch (err) {
        setMensagem("msgTurmaDisciplina", err.message, true);
    }
}

async function removerTurmaDisciplinaInline(item) {
    const confirmado = window.confirm(
        `Remover ${item.disciplina_nome} da turma ${item.turma_nome}?`
    );
    if (!confirmado) {
        return;
    }

    try {
        await fetchJson(`/admin/turmas-disciplinas/${item.id}`, {
            method: "DELETE",
            headers
        });
        setMensagem("msgTurmaDisciplina", `Disciplina ${item.disciplina_nome} removida da turma ${item.turma_nome}.`);
        await Promise.all([
            carregarTurmasDisciplinasAdmin(),
            carregarDisciplinasAdmin()
        ]);
    } catch (err) {
        setMensagem("msgTurmaDisciplina", err.message, true);
    }
}
