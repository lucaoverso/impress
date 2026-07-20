function criarTabelaTurmaDisciplina(itensTurma = []) {
    const wrapper = document.createElement("div");
    wrapper.className = "admin-table-wrap";

    const tabela = document.createElement("table");
    tabela.className = "admin-table";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Disciplina", "Carga horária", "Professor vinculado", "Ações"].forEach((titulo) => {
        const th = document.createElement("th");
        th.innerText = titulo;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    itensTurma.forEach((item) => {
        const tr = document.createElement("tr");

        const tdDisciplina = document.createElement("td");
        const titulo = document.createElement("strong");
        titulo.innerText = item.disciplina_nome;
        const detalhe = document.createElement("div");
        detalhe.className = "admin-table-meta";
        const marcacoes = [];
        if (item.tem_apc) marcacoes.push("APC");
        if (item.tem_prova_bimestral) marcacoes.push("Prova bimestral");
        detalhe.innerText = `Base: ${item.carga_horaria_padrao ?? 0}h${marcacoes.length ? ` | ${marcacoes.join(" | ")}` : ""} | ${
            item.disciplina_ativa ? "Disciplina ativa" : "Disciplina inativa"
        }`;
        tdDisciplina.appendChild(titulo);
        tdDisciplina.appendChild(detalhe);

        const tdCarga = document.createElement("td");
        const inputCarga = document.createElement("input");
        inputCarga.type = "number";
        inputCarga.min = "0";
        inputCarga.value = String(item.carga_horaria ?? 0);
        inputCarga.title = "Carga horária da disciplina na turma";
        tdCarga.appendChild(inputCarga);

        const tdProfessor = document.createElement("td");
        const selectProfessor = construirSelectProfessorTurmaDisciplina(
            item.professor_id ? String(item.professor_id) : "",
            item
        );
        tdProfessor.appendChild(selectProfessor);
        if (item.professor_id && !item.professor_ativo) {
            const alerta = document.createElement("div");
            alerta.className = "admin-table-meta";
            alerta.innerText = "Professor inativo";
            tdProfessor.appendChild(alerta);
        }

        const tdAcoes = document.createElement("td");
        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "admin-inline";

        const btnSalvar = document.createElement("button");
        btnSalvar.type = "button";
        btnSalvar.innerText = "Salvar";
        btnSalvar.addEventListener("click", () => {
            salvarTurmaDisciplinaInline(item, inputCarga, selectProfessor);
        });

        const btnRemover = document.createElement("button");
        btnRemover.type = "button";
        btnRemover.innerText = "Remover";
        btnRemover.addEventListener("click", () => {
            removerTurmaDisciplinaInline(item);
        });

        linhaAcoes.appendChild(btnSalvar);
        linhaAcoes.appendChild(btnRemover);
        tdAcoes.appendChild(linhaAcoes);

        tr.appendChild(tdDisciplina);
        tr.appendChild(tdCarga);
        tr.appendChild(tdProfessor);
        tr.appendChild(tdAcoes);
        tbody.appendChild(tr);
    });
    tabela.appendChild(tbody);
    wrapper.appendChild(tabela);
    return wrapper;
}

function criarFormularioAdicionarDisciplinaTurma(turma, itensTurma = []) {
    const form = document.createElement("form");
    form.className = "admin-subform";

    const titulo = document.createElement("h3");
    titulo.innerText = "Adicionar disciplina nesta turma";

    const ajuda = document.createElement("p");
    ajuda.className = "booking-detail";
    ajuda.innerText = "Escolha uma disciplina do catálogo ou digite um novo nome para já cadastrar e vincular à turma.";

    const selectDisciplina = construirSelectDisciplinasTurma(itensTurma);
    const inputNovaDisciplina = document.createElement("input");
    inputNovaDisciplina.type = "text";
    inputNovaDisciplina.placeholder = "Nova disciplina (opcional)";

    const inputCarga = document.createElement("input");
    inputCarga.type = "number";
    inputCarga.min = "0";
    inputCarga.placeholder = "Carga horária da turma";
    inputCarga.value = "0";

    const selectProfessor = construirSelectProfessorTurmaDisciplina();

    selectDisciplina.addEventListener("change", () => {
        const disciplina = disciplinaBasePorId(selectDisciplina.value);
        if (disciplina && Number(inputCarga.value || 0) === 0) {
            inputCarga.value = String(disciplina.aulas_semanais ?? 0);
        }
    });

    form.appendChild(titulo);
    form.appendChild(ajuda);
    form.appendChild(selectDisciplina);
    form.appendChild(inputNovaDisciplina);
    form.appendChild(inputCarga);
    form.appendChild(selectProfessor);

    const linhaBotoes = document.createElement("div");
    linhaBotoes.className = "admin-inline";

    const btnAdicionar = document.createElement("button");
    btnAdicionar.type = "submit";
    btnAdicionar.className = "btn-destaque";
    btnAdicionar.innerText = "Adicionar disciplina";
    linhaBotoes.appendChild(btnAdicionar);
    form.appendChild(linhaBotoes);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            const disciplinaId = Number(selectDisciplina.value || 0);
            const payload = {
                turma_id: Number(turma.id),
                disciplina_id: disciplinaId > 0 ? disciplinaId : null,
                disciplina_nome: disciplinaId > 0 ? "" : inputNovaDisciplina.value.trim(),
                carga_horaria: Number(inputCarga.value || 0),
                professor_id: selectProfessor.value ? Number(selectProfessor.value) : null
            };
            const resposta = await fetchJson("/admin/turmas-disciplinas", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgTurmaDisciplina", `${resposta.disciplina_nome} adicionada à turma ${resposta.turma_nome}.`);
            form.reset();
            inputCarga.value = "0";
            await Promise.all([
                carregarTurmasDisciplinasAdmin(),
                carregarDisciplinasAdmin()
            ]);
        } catch (err) {
            setMensagem("msgTurmaDisciplina", err.message, true);
        }
    });

    return form;
}

function criarPainelTurmaDisciplina(turma, itensTurma = []) {
    const details = document.createElement("details");
    details.className = "admin-accordion-item";
    details.dataset.turmaId = String(turma.id);
    details.open = turmasDisciplinasExpandidas.has(String(turma.id));
    details.addEventListener("toggle", () => {
        if (details.open) {
            turmasDisciplinasExpandidas.add(String(turma.id));
        } else {
            turmasDisciplinasExpandidas.delete(String(turma.id));
        }
    });

    const summary = document.createElement("summary");
    summary.className = "admin-accordion-summary";

    const resumoPrincipal = document.createElement("div");
    resumoPrincipal.className = "admin-accordion-title";

    const titulo = document.createElement("strong");
    titulo.innerText = turma.nome;
    const detalhe = document.createElement("span");
    detalhe.innerText = `${nomeTurno(turma.turno)} | ${turma.quantidade_estudantes ?? 0} estudantes | ${
        turma.ativo ? "Ativa" : "Inativa"
    }`;
    resumoPrincipal.appendChild(titulo);
    resumoPrincipal.appendChild(detalhe);

    const badge = document.createElement("span");
    badge.className = "admin-accordion-badge";
    badge.innerText = `${itensTurma.length} disciplina(s)`;

    summary.appendChild(resumoPrincipal);
    summary.appendChild(badge);
    details.appendChild(summary);

    const corpo = document.createElement("div");
    corpo.className = "admin-accordion-body";

    if (itensTurma.length > 0) {
        corpo.appendChild(criarTabelaTurmaDisciplina(itensTurma));
    } else {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina vinculada a esta turma.";
        corpo.appendChild(vazio);
    }

    corpo.appendChild(criarFormularioAdicionarDisciplinaTurma(turma, itensTurma));
    details.appendChild(corpo);
    return details;
}

async function carregarTurmasDisciplinasAdmin() {
    const container = el("listaTurmasDisciplinasAdmin");
    if (!container) {
        return;
    }

    registrarTurmasDisciplinasExpandidas();
    const lista = await fetchJson("/admin/turmas-disciplinas?incluir_inativos=true", { headers });
    const turmas = Array.isArray(contextoTurmasDisciplinas.turmas) ? contextoTurmasDisciplinas.turmas : [];

    container.innerHTML = "";
    if (turmas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada para organizar disciplinas.";
        container.appendChild(vazio);
        return;
    }

    const itensPorTurma = new Map();
    (Array.isArray(lista) ? lista : []).forEach((item) => {
        const turmaId = Number(item.turma_id);
        if (!itensPorTurma.has(turmaId)) {
            itensPorTurma.set(turmaId, []);
        }
        itensPorTurma.get(turmaId).push(item);
    });

    turmas
        .slice()
        .sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "pt-BR"))
        .forEach((turma) => {
            container.appendChild(
                criarPainelTurmaDisciplina(turma, itensPorTurma.get(Number(turma.id)) || [])
            );
        });
}
